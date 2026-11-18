"""Session Seat Desk: local JSON API + basic UI over a durable SQLite fixture.

Commands (run from this directory, Python 3.11+, standard library only):
  python3 app.py --reset   explicitly seed a fresh fixture in DATA_DIR
  python3 app.py           serve on 127.0.0.1:$PORT (default 8765); never resets
  python3 app.py --check   read the store directly and verify invariants + audit chain

State: $DATA_DIR/seats.db (default ./.state/seats.db). See README.md.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import threading
import unicodedata
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer
from urllib.parse import parse_qs, urlsplit

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(BASE / '.state'))).resolve()
DB = DATA / 'seats.db'
MARKER = 'session-seat-desk-disposable-fixture-v1'
MAX_BODY = 64 * 1024
MAX_ALIAS = 200
MAX_KEY = 200
GENESIS = '0' * 64

# One process-wide writer lock serialises every check-then-write. BEGIN IMMEDIATE
# additionally takes SQLite's write lock, so a second process cannot interleave.
WRITE_LOCK = threading.Lock()

SCHEMA = '''
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, capacity INTEGER NOT NULL CHECK (capacity >= 0));
CREATE TABLE IF NOT EXISTS reservations (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  attendee_alias TEXT NOT NULL,
  request_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('active','cancelled')),
  created_at TEXT NOT NULL,
  cancelled_at TEXT);
CREATE TABLE IF NOT EXISTS audit_log (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('reserve','cancel')),
  reservation_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  attendee_alias TEXT NOT NULL,
  request_key TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL);
'''


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def connect():
    if not DB.exists():
        raise ApiError(503, 'STORE_MISSING', f'State store not found at {DB}. Run --reset for a fresh fixture.')
    connection = sqlite3.connect(DB, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA busy_timeout = 10000')
    return connection


def reset_fixture():
    marker = DATA / '.fixture-owner'
    if DB.exists() and (not marker.exists() or marker.read_text() != MARKER):
        raise RuntimeError('Refusing to reset an unmarked database. Choose a new DATA_DIR.')
    DATA.mkdir(parents=True, exist_ok=True)
    marker.write_text(MARKER)
    seed = json.loads((BASE / 'sessions.json').read_text())
    with closing(sqlite3.connect(DB, timeout=10, isolation_level=None)) as connection:
        connection.executescript(SCHEMA)
        connection.execute('BEGIN IMMEDIATE')
        connection.execute('DELETE FROM audit_log')
        connection.execute('DELETE FROM reservations')
        connection.execute('DELETE FROM sessions')
        connection.executemany('INSERT INTO sessions VALUES (:id,:title,:capacity)', seed)
        connection.execute('COMMIT')
    print('Reset fixture:', DB)


# ---------- domain ----------

def reservation_json(row):
    return {
        'id': row['id'], 'sessionId': row['session_id'],
        'attendeeAlias': row['attendee_alias'], 'requestKey': row['request_key'],
        'status': row['status'], 'createdAt': row['created_at'],
        'cancelledAt': row['cancelled_at'],
    }


def list_sessions(connection):
    rows = connection.execute('''
        SELECT s.id, s.title, s.capacity,
               (SELECT COUNT(*) FROM reservations r
                 WHERE r.session_id = s.id AND r.status = 'active') AS active
        FROM sessions s ORDER BY s.id''').fetchall()
    return [{'id': r['id'], 'title': r['title'], 'capacity': int(r['capacity']),
             'activeCount': int(r['active']),
             'remainingSeats': max(0, int(r['capacity']) - int(r['active']))} for r in rows]


def audit_digest(prev, at, action, reservation_id, session_id, alias, key):
    material = json.dumps([prev, at, action, reservation_id, session_id, alias, key], ensure_ascii=False)
    return hashlib.sha256(material.encode('utf-8')).hexdigest()


def append_audit(connection, action, row):
    last = connection.execute('SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1').fetchone()
    prev = last['hash'] if last else GENESIS
    at = now()
    digest = audit_digest(prev, at, action, row['id'], row['session_id'], row['attendee_alias'], row['request_key'])
    connection.execute('INSERT INTO audit_log (at, action, reservation_id, session_id, attendee_alias, request_key, '
                       'prev_hash, hash) VALUES (?,?,?,?,?,?,?,?)',
                       (at, action, row['id'], row['session_id'], row['attendee_alias'], row['request_key'], prev, digest))


def validate_reservation_request(body):
    if not isinstance(body, dict):
        raise ApiError(400, 'INVALID_BODY', 'Request body must be a JSON object.')
    session_id = body.get('sessionId')
    alias = body.get('attendeeAlias')
    key = body.get('requestKey')
    if not isinstance(session_id, str) or not session_id.strip():
        raise ApiError(400, 'INVALID_SESSION_ID', 'sessionId must be a non-empty string.')
    if not isinstance(alias, str) or not alias.strip():
        raise ApiError(400, 'INVALID_ALIAS', 'attendeeAlias must be a non-blank string.')
    if not isinstance(key, str) or key == '':
        raise ApiError(400, 'INVALID_REQUEST_KEY', 'requestKey must be a non-empty string.')
    for name, value in (('sessionId', session_id), ('attendeeAlias', alias), ('requestKey', key)):
        try:
            value.encode('utf-8')
        except UnicodeEncodeError:
            raise ApiError(400, 'INVALID_TEXT', f'{name} contains invalid Unicode.')
    alias = alias.strip()
    if not any(unicodedata.category(ch)[0] not in 'CZ' for ch in alias):
        raise ApiError(400, 'INVALID_ALIAS', 'attendeeAlias must contain visible characters.')
    if len(alias) > MAX_ALIAS:
        raise ApiError(400, 'INVALID_ALIAS', f'attendeeAlias must be at most {MAX_ALIAS} characters.')
    if len(key) > MAX_KEY:
        raise ApiError(400, 'INVALID_REQUEST_KEY', f'requestKey must be at most {MAX_KEY} characters.')
    return session_id, alias, key


def reserve(body):
    """Returns (http_status, reservation). Order: validate, session, key replay, capacity, insert."""
    session_id, alias, key = validate_reservation_request(body)
    with WRITE_LOCK, closing(connect()) as connection:
        connection.execute('BEGIN IMMEDIATE')
        try:
            session = connection.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
            if session is None:
                raise ApiError(404, 'UNKNOWN_SESSION', f'Unknown session: {session_id}')
            existing = connection.execute('SELECT * FROM reservations WHERE request_key = ?', (key,)).fetchone()
            if existing is not None:
                if existing['session_id'] == session_id and existing['attendee_alias'] == alias:
                    connection.execute('ROLLBACK')
                    return 200, reservation_json(existing)   # replay: original record, current status
                raise ApiError(409, 'REQUEST_KEY_CONFLICT',
                               'This requestKey was already used for a different session or alias.')
            active = connection.execute("SELECT COUNT(*) FROM reservations WHERE session_id = ? AND status = 'active'",
                                        (session_id,)).fetchone()[0]
            if active >= session['capacity']:
                raise ApiError(409, 'CAPACITY_FULL', f'No remaining seats in {session_id}.')
            reservation_id = str(uuid.uuid4())
            connection.execute('INSERT INTO reservations (id, session_id, attendee_alias, request_key, status, created_at) '
                               "VALUES (?,?,?,?,'active',?)", (reservation_id, session_id, alias, key, now()))
            row = connection.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
            append_audit(connection, 'reserve', row)
            connection.execute('COMMIT')
            return 201, reservation_json(row)
        except BaseException:
            if connection.in_transaction:
                connection.execute('ROLLBACK')
            raise


def cancel(reservation_id):
    with WRITE_LOCK, closing(connect()) as connection:
        connection.execute('BEGIN IMMEDIATE')
        try:
            row = connection.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
            if row is None:
                raise ApiError(404, 'UNKNOWN_RESERVATION', f'Unknown reservation: {reservation_id}')
            if row['status'] == 'active':
                connection.execute("UPDATE reservations SET status = 'cancelled', cancelled_at = ? WHERE id = ?",
                                   (now(), reservation_id))
                row = connection.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
                append_audit(connection, 'cancel', row)
            connection.execute('COMMIT')
            return 200, reservation_json(row)
        except BaseException:
            if connection.in_transaction:
                connection.execute('ROLLBACK')
            raise


def get_reservation(reservation_id):
    with closing(connect()) as connection:
        row = connection.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
    if row is None:
        raise ApiError(404, 'UNKNOWN_RESERVATION', f'Unknown reservation: {reservation_id}')
    return reservation_json(row)


def find_reservations(alias=None):
    with closing(connect()) as connection:
        if alias is not None and alias.strip():
            rows = connection.execute('SELECT * FROM reservations WHERE attendee_alias = ? ORDER BY created_at',
                                      (alias.strip(),)).fetchall()
        else:
            rows = connection.execute('SELECT * FROM reservations ORDER BY created_at').fetchall()
    return [reservation_json(r) for r in rows]


# ---------- independent store check (python3 app.py --check) ----------

def check_store():
    """Reads seats.db directly (not via HTTP) and verifies the PRD invariants
    plus the hash-chained audit log. Returns (ok, report)."""
    problems = []
    with closing(connect()) as connection:
        sessions = {r['id']: r['capacity'] for r in connection.execute('SELECT * FROM sessions')}
        reservations = [dict(r) for r in connection.execute('SELECT * FROM reservations')]
        log = [dict(r) for r in connection.execute('SELECT * FROM audit_log ORDER BY seq')]
    if set(sessions) != {'CT-101', 'CT-102'}:
        problems.append(f'unexpected sessions {sorted(sessions)}')
    for sid, cap in sessions.items():
        active = sum(1 for r in reservations if r['session_id'] == sid and r['status'] == 'active')
        if active > cap:
            problems.append(f'{sid}: active {active} exceeds capacity {cap}')
    for r in reservations:
        if r['attendee_alias'] != r['attendee_alias'].strip() or not r['attendee_alias']:
            problems.append(f'{r["id"]}: alias not trimmed/blank')
    prev = GENESIS
    replay = {}
    for entry in log:
        expected = audit_digest(prev, entry['at'], entry['action'], entry['reservation_id'], entry['session_id'],
                                entry['attendee_alias'], entry['request_key'])
        if entry['prev_hash'] != prev or entry['hash'] != expected:
            problems.append(f'audit chain broken at seq {entry["seq"]}')
            break
        prev = entry['hash']
        replay[entry['reservation_id']] = (entry['session_id'], entry['attendee_alias'], entry['request_key'],
                                           'active' if entry['action'] == 'reserve' else 'cancelled')
    actual = {r['id']: (r['session_id'], r['attendee_alias'], r['request_key'], r['status']) for r in reservations}
    if not problems and replay != actual:
        problems.append('reservation table disagrees with audit log replay '
                        f'(log {len(replay)} rows, table {len(actual)} rows)')
    report = {'store': str(DB), 'sessions': len(sessions), 'reservations': len(reservations),
              'auditEntries': len(log), 'problems': problems, 'ok': not problems}
    return not problems, report


# ---------- HTTP ----------

# Exact whitelist: the UI's two bundled fonts (SIL Open Font License), never arbitrary files.
FONTS = {'/fonts/bricolage.woff2': 'bricolage-grotesque-latin.woff2', '/fonts/dm-sans.woff2': 'dm-sans-latin.woff2'}
ID_PATH = re.compile(r'^/reservations/([^/]+)$')
CANCEL_PATH = re.compile(r'^/reservations/([^/]+)/cancel$')


class LoopbackHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128

    def server_bind(self):
        TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


class Handler(BaseHTTPRequestHandler):
    server_version = 'SessionSeatDesk/1.0'
    timeout = 15  # seconds; drops slow or stalled clients instead of holding a thread forever

    def send_error(self, code, message=None, explain=None):
        # Protocol-level errors (bad request line, oversize headers) must also be JSON.
        self.close_connection = True
        if code == 501:  # unknown method token from the stdlib parser: a client error, not a server fault
            code = 405
        try:
            self.send_json(code, {'error': {'code': f'HTTP_{code}', 'message': message or 'Request rejected.'}})
        except OSError:
            pass

    def log_message(self, fmt, *args):
        sys.stderr.write('%s %s\n' % (self.log_date_time_string(), fmt % args))

    def send_json(self, status, value):
        payload = json.dumps(value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, error):
        self.send_json(error.status, {'error': {'code': error.code, 'message': error.message}})

    def read_json(self, required=True):
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            raise ApiError(400, 'INVALID_LENGTH', 'Invalid Content-Length header.')
        if length < 0:
            raise ApiError(400, 'INVALID_LENGTH', 'Invalid Content-Length header.')
        if length > MAX_BODY:
            raise ApiError(413, 'BODY_TOO_LARGE', 'Request body is too large.')
        raw = self.rfile.read(length) if length else b''
        if not raw.strip():
            if required:
                raise ApiError(400, 'MALFORMED_JSON', 'Request body must be a JSON object.')
            return {}
        try:
            return json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            raise ApiError(400, 'MALFORMED_JSON', 'Request body is not valid JSON.')

    def dispatch(self, method):
        try:
            try:
                url = urlsplit(self.path)
            except ValueError:
                raise ApiError(400, 'BAD_URL', 'Malformed request path.')
            path = url.path.rstrip('/') or '/'
            if method == 'GET':
                if path in ('/', '/index.html'):
                    return self.send_static()
                if path in FONTS:
                    return self.send_font(FONTS[path])
                if path == '/sessions':
                    with closing(connect()) as connection:
                        return self.send_json(200, {'sessions': list_sessions(connection)})
                if path == '/reservations':
                    alias = parse_qs(url.query).get('alias', [None])[0]
                    return self.send_json(200, {'reservations': find_reservations(alias)})
                if path == '/health':
                    with closing(connect()) as connection:
                        last = connection.execute('SELECT seq, hash FROM audit_log ORDER BY seq DESC LIMIT 1').fetchone()
                    return self.send_json(200, {'status': 'ok', 'store': str(DB), 'pid': os.getpid(),
                                                'auditEntries': last['seq'] if last else 0,
                                                'lastAuditHash': last['hash'] if last else GENESIS})
                match = ID_PATH.match(path)
                if match:
                    return self.send_json(200, get_reservation(match.group(1)))
            elif method == 'POST':
                if path == '/reservations':
                    status, record = reserve(self.read_json())
                    return self.send_json(status, record)
                match = CANCEL_PATH.match(path)
                if match:
                    body = self.read_json(required=False)
                    if not isinstance(body, dict):
                        raise ApiError(400, 'INVALID_BODY', 'Cancel body must be an empty JSON object.')
                    status, record = cancel(match.group(1))
                    return self.send_json(status, record)
            if method in ('GET', 'POST'):
                raise ApiError(404, 'NOT_FOUND', f'No route for {method} {url.path}')
            raise ApiError(405, 'METHOD_NOT_ALLOWED', f'{method} is not supported; use GET or POST.')
        except ApiError as error:
            self.send_error_json(error)
        except sqlite3.OperationalError as error:
            self.log_message('database busy: %s', error)
            self.send_error_json(ApiError(503, 'STORE_BUSY', 'Store is busy; retry with the same requestKey.'))
        except Exception as error:  # never leak a stack trace or an HTML page
            self.log_message('unexpected error: %r', error)
            self.send_error_json(ApiError(500, 'INTERNAL', 'Unexpected server error.'))

    def send_font(self, name):
        payload = (BASE / 'static' / 'fonts' / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'font/woff2')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'max-age=86400')
        self.end_headers()
        self.wfile.write(payload)

    def send_static(self):
        payload = (BASE / 'static' / 'index.html').read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.dispatch('GET')

    def do_POST(self):
        self.dispatch('POST')

    def do_PUT(self):
        self.dispatch('PUT')

    def do_DELETE(self):
        self.dispatch('DELETE')

    def do_PATCH(self):
        self.dispatch('PATCH')

    def do_OPTIONS(self):
        self.dispatch('OPTIONS')

    def do_HEAD(self):
        self.send_response(405)
        self.send_header('Content-Length', '0')
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--reset', action='store_true', help='Reset only the marked fixture DATA_DIR')
    parser.add_argument('--check', action='store_true', help='Verify stored invariants and the audit chain')
    args = parser.parse_args()
    if args.reset:
        reset_fixture()
        return 0
    if not DB.exists():
        parser.error(f'No fixture at {DB}. Run with --reset first, using the same DATA_DIR.')
    if args.check:
        ok, report = check_store()
        print(json.dumps(report, indent=2))
        return 0 if ok else 1
    try:
        port = int(os.environ.get('PORT', '8765'))
        server = LoopbackHTTPServer(('127.0.0.1', port), Handler)
    except (ValueError, OSError) as error:
        parser.error(f'Cannot listen on PORT={os.environ.get("PORT", "8765")}: {error}')
    print(f'Session Seat Desk on http://127.0.0.1:{server.server_port}  state={DB}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
