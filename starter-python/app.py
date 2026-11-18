"""Optional transport/storage scaffold, deliberately NOT a working solution.

Implement the PRD endpoints and browser behavior during the hackathon.
Run --reset explicitly before serving. Only this marked fixture store is reset.
"""
import argparse
from contextlib import closing
import html
import json
import os
from pathlib import Path
import sqlite3
import uuid
from urllib.parse import parse_qs, urlencode, urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(BASE / '.state'))).resolve()
MARKER = 'session-seat-desk-disposable-fixture-v1'


class LoopbackHTTPServer(ThreadingHTTPServer):
    """Local transport does not need HTTPServer's reverse-DNS lookup."""
    def server_bind(self):
        TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


def reset_fixture():
    marker = DATA / '.fixture-owner'
    db = DATA / 'seats.db'
    if db.exists() and (not marker.exists() or marker.read_text() != MARKER):
        raise RuntimeError('Refusing to reset an unmarked database. Choose a new DATA_DIR.')
    DATA.mkdir(parents=True, exist_ok=True)
    marker.write_text(MARKER)
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, capacity INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS reservations (
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
              attendee_alias TEXT NOT NULL, request_key TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL CHECK (status IN ('active','cancelled')));
            DELETE FROM reservations;
            DELETE FROM sessions;
        ''')
        seed = json.loads((BASE / 'sessions.json').read_text())
        connection.executemany('INSERT INTO sessions VALUES (:id,:title,:capacity)', seed)
    print('Reset fixture:', db)


class ApiError(Exception):
    """Raised anywhere in a request; Handler turns it into a 4xx JSON error (AC-08)."""
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


MAX_ALIAS_LENGTH = 30  # A-05: counted after trimming


def validate_create(body):
    """Edge validation before any DB work. Returns (sessionId, trimmed alias, requestKey)."""
    session_id, alias, key = (body.get(k) for k in ('sessionId', 'attendeeAlias', 'requestKey'))
    if not isinstance(session_id, str) or not session_id:
        raise ApiError(400, 'INVALID_INPUT', 'sessionId must be a non-empty string')
    if not isinstance(alias, str) or not alias.strip():
        raise ApiError(400, 'INVALID_INPUT', 'attendeeAlias must not be blank')
    if len(alias.strip()) > MAX_ALIAS_LENGTH:
        raise ApiError(400, 'INVALID_INPUT', 'attendeeAlias must be at most %d characters' % MAX_ALIAS_LENGTH)
    if not isinstance(key, str) or not key:
        raise ApiError(400, 'INVALID_INPUT', 'requestKey must be a non-empty string')
    return session_id, alias.strip(), key


def connect():
    """One connection per request; explicit transactions (BEGIN IMMEDIATE) for writes."""
    connection = sqlite3.connect(DATA / 'seats.db', timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection


def list_sessions():
    """Single source of truth for counts, shared by GET /sessions and the UI (AC-02)."""
    with closing(connect()) as connection:
        rows = connection.execute('''
            SELECT s.id, s.title, s.capacity,
                   (SELECT COUNT(*) FROM reservations r
                     WHERE r.session_id = s.id AND r.status = 'active') AS active_count
            FROM sessions s ORDER BY s.id''').fetchall()
    return [{'id': r['id'], 'title': r['title'], 'capacity': r['capacity'],
             'activeCount': r['active_count'], 'remainingSeats': r['capacity'] - r['active_count']}
            for r in rows]


def _reservation(row):
    return {'id': row['id'], 'sessionId': row['session_id'], 'attendeeAlias': row['attendee_alias'],
            'requestKey': row['request_key'], 'status': row['status']}


def get_reservation(reservation_id):
    with closing(connect()) as connection:
        row = connection.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
    return _reservation(row) if row else None


def cancel_reservation(reservation_id):
    """active -> cancelled once; repeats return the stored cancelled row unchanged (AC-06)."""
    with closing(connect()) as connection:
        connection.execute('BEGIN IMMEDIATE')
        try:
            connection.execute(
                "UPDATE reservations SET status = 'cancelled' WHERE id = ? AND status = 'active'",
                (reservation_id,))
            row = connection.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
            if not row:
                raise ApiError(404, 'NOT_FOUND', 'Unknown reservation %s' % reservation_id)
            connection.execute('COMMIT')
        except BaseException:
            connection.execute('ROLLBACK')
            raise
    return _reservation(row)


def create_reservation(session_id, alias, request_key):
    """Returns (record, created). Key lookup, checks, write and readback share one transaction.

    A known request key never creates a row: identical (session, trimmed alias) replays the stored
    record in its current status (AC-05a); anything else is a 409 conflict (AC-05b). Keys are global.
    """
    reservation_id = uuid.uuid4().hex
    with closing(connect()) as connection:
        connection.execute('BEGIN IMMEDIATE')
        try:
            existing = connection.execute(
                'SELECT * FROM reservations WHERE request_key = ?', (request_key,)).fetchone()
            if existing:
                if (existing['session_id'], existing['attendee_alias']) != (session_id, alias):
                    raise ApiError(409, 'KEY_CONFLICT',
                                   'requestKey %s is already used for a different session or alias' % request_key)
                connection.execute('COMMIT')
                return _reservation(existing), False
            session = connection.execute('SELECT capacity FROM sessions WHERE id = ?', (session_id,)).fetchone()
            if not session:
                raise ApiError(404, 'UNKNOWN_SESSION', 'Unknown session %s' % session_id)
            # BEGIN IMMEDIATE holds the write lock, so this count cannot go stale before INSERT (AC-04).
            active = connection.execute(
                "SELECT COUNT(*) FROM reservations WHERE session_id = ? AND status = 'active'",
                (session_id,)).fetchone()[0]
            if active >= session['capacity']:
                raise ApiError(409, 'CAPACITY_FULL', 'No remaining seats in %s' % session_id)
            connection.execute(
                "INSERT INTO reservations VALUES (?, ?, ?, ?, 'active')",
                (reservation_id, session_id, alias, request_key))
            row = connection.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
            connection.execute('COMMIT')
        except BaseException:
            connection.execute('ROLLBACK')
            raise
    return _reservation(row), True


def list_reservations():
    with closing(connect()) as connection:
        rows = connection.execute('SELECT * FROM reservations ORDER BY session_id, attendee_alias').fetchall()
    return [_reservation(r) for r in rows]


# Palette from the organizer's materials (scripts/render_materials.py, event deck). Inspired by
# Agile Testing Days 2026; no logos or external assets, so the page works fully offline.
STYLE = '''
:root{--atd-navy:#080E62;--atd-pink:#C91C53;--ink:#1A2943;--slate:#5A6B85;--surface:#F2F4F8;
  --rule:#D6DBE4;--sky:#B9C6E4;--pink-light:#FF8FAB;--card:#FFFFFF;
  --ok-ink:#1E6B3A;--ok-bg:#E8F5EC;--err-ink:#A3123F;--err-bg:#FCE8EE;--muted-bg:#E9EDF3;
  --radius:.6rem;--shadow:0 1px 2px rgba(8,14,98,.06),0 4px 16px rgba(8,14,98,.07)}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--surface);color:var(--ink);
  font:1rem/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
.masthead{background:var(--atd-navy);color:#fff;border-bottom:4px solid var(--atd-pink)}
.masthead .inner,main{max-width:60rem;margin:0 auto;padding:0 1rem}
.masthead .inner{padding-top:1.4rem;padding-bottom:1.3rem;display:flex;align-items:center;gap:.9rem}
.mark{flex:none;width:2.6rem;height:2.6rem}
h1{margin:0;font-size:clamp(1.5rem,4vw,2.1rem);line-height:1.15;letter-spacing:-.01em}
.subtitle{margin:.2rem 0 0;color:var(--sky);font-size:.95rem}
main{padding-top:1.5rem;padding-bottom:3rem}
h2{font-size:1.2rem;margin:0 0 .8rem;color:var(--atd-navy);display:flex;align-items:center;gap:.5rem}
h2::before{content:"";width:.35rem;height:1.1rem;border-radius:.2rem;background:var(--atd-pink)}
.card{background:var(--card);border:1px solid var(--rule);border-radius:var(--radius);
  box-shadow:var(--shadow);padding:1.2rem;margin:0 0 1.5rem}
.table-wrap{overflow-x:auto;border:1px solid var(--rule);border-radius:var(--radius)}
table{border-collapse:collapse;width:100%;background:var(--card)}
caption{caption-side:top;text-align:left;color:var(--slate);font-size:.9rem;padding:.55rem .8rem;
  background:var(--card);border-bottom:1px solid var(--rule)}
th,td{padding:.6rem .8rem;text-align:left;border-bottom:1px solid var(--rule);vertical-align:middle}
th{background:var(--atd-navy);color:#fff;font-weight:600;font-size:.9rem;white-space:nowrap}
tr:last-child td{border-bottom:0}
tr:nth-child(odd) td{background:var(--surface)}
#sessions td:nth-child(n+3){font-variant-numeric:tabular-nums}
#sessions td:first-child,#reservations td:nth-child(2){white-space:nowrap}
#sessions td:last-child{font-weight:700;font-size:1.15rem;color:var(--atd-navy)}
#sessions tr.full td:last-child{color:var(--atd-pink)}
#sessions tr.full td:first-child{box-shadow:inset 4px 0 0 var(--atd-pink)}
#reservations td:first-child,#reservations td:nth-child(4){font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
  font-size:.82rem;color:var(--slate);word-break:break-all;min-width:9rem}
.badge{display:inline-block;padding:.1rem .65rem;border-radius:999px;font-size:.85rem;font-weight:600}
.badge-active{background:var(--ok-bg);color:var(--ok-ink)}
.badge-cancelled{background:var(--muted-bg);color:var(--slate)}
form.reserve{display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-end}
form.reserve>div{flex:1 1 14rem;min-width:0}
label{display:block;font-weight:600;margin-bottom:.3rem;color:var(--atd-navy)}
input,select{width:100%;max-width:100%;min-width:0;text-overflow:ellipsis;font:inherit;color:var(--ink);background:#fff;padding:.55rem .7rem;
  border:1px solid var(--slate);border-radius:.4rem}
button{font:inherit;font-weight:600;cursor:pointer;border-radius:.4rem;padding:.55rem 1.3rem;
  transition:background-color .15s,color .15s,border-color .15s}
form.reserve button{background:var(--atd-navy);color:#fff;border:2px solid var(--atd-navy);flex:none}
form.reserve button:hover{background:var(--atd-pink);border-color:var(--atd-pink)}
td form{margin:0}
td button{background:#fff;color:var(--atd-pink);border:1.5px solid var(--atd-pink);padding:.3rem .9rem;font-size:.9rem}
td button:hover{background:var(--atd-pink);color:#fff}
:focus-visible{outline:3px solid var(--atd-pink);outline-offset:2px}
#message{margin:0 0 1.5rem;padding:.8rem 1rem;border-radius:var(--radius);font-weight:600;
  background:var(--ok-bg);color:var(--ok-ink);border:1px solid var(--ok-ink);border-left-width:6px}
#message[role=alert],#message.message-cancelled{background:var(--err-bg);color:var(--err-ink);border-color:var(--err-ink)}
#message:empty{display:none}
.empty{color:var(--slate);margin:.8rem 0 0}
.muted{color:var(--slate)}
footer{color:var(--slate);font-size:.85rem;text-align:center;padding:0 1rem 2rem}
@media (max-width:30rem){.card{padding:1rem}th,td{padding:.5rem .55rem}form.reserve button{width:100%}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
'''

# Inline SVG mark (aria-hidden): seat rows in the event palette, no external asset.
MARK = ('<svg class="mark" viewBox="0 0 40 40" aria-hidden="true" focusable="false">'
        '<rect width="40" height="40" rx="9" fill="#C91C53"/>'
        '<g fill="#fff"><rect x="8" y="10" width="7" height="7" rx="2"/><rect x="17" y="10" width="7" height="7" rx="2"/>'
        '<rect x="26" y="10" width="7" height="7" rx="2" opacity=".45"/><rect x="8" y="22" width="7" height="7" rx="2"/>'
        '<rect x="17" y="22" width="7" height="7" rx="2" opacity=".45"/><rect x="26" y="22" width="7" height="7" rx="2" opacity=".45"/>'
        '</g></svg>')

PAGE = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Session Seat Desk</title>
<style>{style}</style>
<header class="masthead"><div class="inner">{mark}<div><h1>Session Seat Desk</h1>
<p class="subtitle">Completion Theater Hackathon &middot; Agile Testing Days 2026</p></div></div></header>
<main>
<p id="message" role="{message_role}"{message_class}>{message}</p>
<section class="card" aria-labelledby="h-sessions"><h2 id="h-sessions">Workshops</h2>
<div class="table-wrap"><table id="sessions"><caption>Workshops and remaining seats (live from storage)</caption>
<tr><th scope="col">Session</th><th scope="col">Title</th><th scope="col">Capacity</th>
<th scope="col">Active</th><th scope="col">Remaining</th></tr>
{session_rows}
</table></div></section>
<section class="card" aria-labelledby="h-reserve"><h2 id="h-reserve">Reserve a seat</h2>
<form class="reserve" method="post" action="/ui/reserve">
<div><label for="session">Session</label><select id="session" name="sessionId">{session_options}</select></div>
<div><label for="alias">Attendee alias</label><input id="alias" name="attendeeAlias" required maxlength="30" autocomplete="off"></div>
<input type="hidden" name="requestKey" value="{request_key}">
<button type="submit">Reserve</button>
</form></section>
<section class="card" aria-labelledby="h-reservations"><h2 id="h-reservations">Reservations</h2>
<div class="table-wrap"><table id="reservations"><caption>All reservations (live from storage)</caption>
<tr><th scope="col">ID</th><th scope="col">Session</th><th scope="col">Alias</th>
<th scope="col">Request key</th><th scope="col">Status</th><th scope="col">Action</th></tr>
{reservation_rows}
</table></div>{empty_note}</section>
</main>
<footer>Fictional aliases only &middot; state stored locally in SQLite</footer>
</html>
'''


def _cancel_cell(r):
    if r['status'] != 'active':
        return '&mdash;'
    return ('<form method="post" action="/ui/cancel"><input type="hidden" name="reservationId" value="{id}">'
            '<button type="submit" aria-label="Cancel reservation for {alias} in {session}">Cancel</button>'
            '</form>').format(id=html.escape(r['id']), alias=html.escape(r['attendeeAlias']),
                              session=html.escape(r['sessionId']))


def render_page(message='', is_error=False, cancelled=False):
    """Everything shown comes from storage at render time; success text only via confirmed_message()."""
    e = lambda value: html.escape(str(value))  # noqa: E731
    sessions = list_sessions()
    session_rows = '\n'.join('<tr%s>%s</tr>' % (
        ' class="full"' if s['remainingSeats'] == 0 else '',
        ''.join('<td>%s</td>' % e(s[k]) for k in ('id', 'title', 'capacity', 'activeCount', 'remainingSeats')))
        for s in sessions)
    session_options = ''.join('<option value="{0}">{0} {1} ({2} left)</option>'.format(
        e(s['id']), e(s['title']), e(s['remainingSeats'])) for s in sessions)
    reservations = list_reservations()
    reservation_rows = '\n'.join(
        '<tr>%s<td><span class="badge badge-%s">%s</span></td><td>%s</td></tr>' % (
            ''.join('<td>%s</td>' % e(r[k]) for k in ('id', 'sessionId', 'attendeeAlias', 'requestKey')),
            e(r['status']), e(r['status']), _cancel_cell(r))
        for r in reservations)
    empty_note = '' if reservations else '<p class="empty">No reservations yet.</p>'
    return PAGE.format(style=STYLE, mark=MARK, message=e(message),
                       message_role='alert' if is_error else 'status',
                       message_class=' class="message-cancelled"' if cancelled and not is_error else '',
                       session_rows=session_rows, session_options=session_options,
                       request_key=uuid.uuid4().hex, reservation_rows=reservation_rows,
                       empty_note=empty_note).encode('utf-8')


def confirmed_message(reservation_id):
    """(text, stored status) built from the stored row, never from the request (no success theater)."""
    r = get_reservation(reservation_id) if reservation_id else None
    if not r:
        return '', None
    return 'Reservation %s: %s in %s is %s.' % (r['id'], r['attendeeAlias'], r['sessionId'], r['status']), r['status']


class Handler(BaseHTTPRequestHandler):
    def json_response(self, status, value):
        payload = json.dumps(value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def handle_safely(self, route):
        """Every request gets a JSON answer; no exception may drop the connection or the process."""
        try:
            route()
        except ApiError as err:
            self.json_response(err.status, {'error': {'code': err.code, 'message': err.message}})
        except Exception as err:  # unexpected: answer 500, log, keep serving
            self.log_error('Unhandled %r', err)
            self.json_response(500, {'error': {'code': 'INTERNAL', 'message': 'Unexpected server error'}})

    def do_GET(self):
        self.handle_safely(self.route_get)

    def do_POST(self):
        self.handle_safely(self.route_post)

    def html_response(self, status, payload):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def redirect_home(self, reservation_id):
        self.send_response(303)
        self.send_header('Location', '/?' + urlencode({'r': reservation_id}))
        self.send_header('Content-Length', '0')
        self.end_headers()

    def read_form(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0)).decode('utf-8', 'replace')
        return {k: v[0] for k, v in parse_qs(raw, keep_blank_values=True).items()}

    def route_get(self):
        url = urlsplit(self.path)
        if url.path == '/health':
            self.json_response(200, {'status': 'ok'})
        elif url.path == '/sessions':
            self.json_response(200, {'sessions': list_sessions()})
        elif url.path == '/':
            reservation_id = parse_qs(url.query).get('r', [''])[0]
            text, status = confirmed_message(reservation_id)
            self.html_response(200, render_page(text, cancelled=(status == 'cancelled')))
        elif url.path.startswith('/reservations/'):
            reservation = get_reservation(url.path[len('/reservations/'):])
            if reservation:
                self.json_response(200, reservation)
            else:
                self.json_response(404, {'error': {'code': 'NOT_FOUND', 'message': 'Unknown reservation'}})
        else:
            self.json_response(404, {'error': {'code': 'NOT_FOUND', 'message': 'Unknown path'}})

    def read_json_object(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        try:
            body = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            raise ApiError(400, 'INVALID_JSON', 'Request body must be valid JSON') from None
        if not isinstance(body, dict):
            raise ApiError(400, 'INVALID_JSON', 'Request body must be a JSON object')
        return body

    def route_post(self):
        parts = self.path.strip('/').split('/')
        if parts == ['reservations']:
            record, created = create_reservation(*validate_create(self.read_json_object()))
            self.json_response(201 if created else 200, record)
        elif len(parts) == 3 and parts[0] == 'reservations' and parts[2] == 'cancel':
            self.read_json_object()  # contract input is {}; malformed bodies reject before any write
            self.json_response(200, cancel_reservation(parts[1]))
        elif parts[0] == 'ui' and len(parts) == 2 and parts[1] in ('reserve', 'cancel'):
            self.route_ui_form(parts[1])
        else:
            raise ApiError(404, 'NOT_FOUND', 'Unknown path')

    def route_ui_form(self, action):
        """Browser forms: same domain functions as the API; success -> 303 to a stored-state page,
        rejection -> the API's 4xx status with the error in a role=alert region."""
        form = self.read_form()
        try:
            if action == 'reserve':
                record, _ = create_reservation(*validate_create(form))
            else:
                record = cancel_reservation(form.get('reservationId', ''))
        except ApiError as err:
            self.html_response(err.status, render_page(err.message, is_error=True))
            return
        self.redirect_home(record['id'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', help='Reset only the marked fixture DATA_DIR')
    args = parser.parse_args()
    if args.reset:
        reset_fixture()
        return
    if not (DATA / 'seats.db').exists():
        parser.error('Run with --reset first, using the same DATA_DIR.')
    server = LoopbackHTTPServer((os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '8765'))), Handler)
    print('Session Seat Desk on http://127.0.0.1:%s (state: %s)' % (server.server_port, DATA / 'seats.db'), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
