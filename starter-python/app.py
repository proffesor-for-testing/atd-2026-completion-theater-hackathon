"""Session Seat Desk: local JSON API + HTML UI backed by SQLite.

Run --reset explicitly before the first serve. Only this marked fixture store is reset.
Ordinary start never resets. State lives in DATA_DIR/seats.db (default ./.state).
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import unicodedata
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer
from urllib.parse import urlsplit, unquote

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(BASE / '.state'))).resolve()


def db_path():
    # Resolved on each use so DATA can be overridden (e.g. by tests) after import.
    return DATA / 'seats.db'

MARKER = 'session-seat-desk-disposable-fixture-v1'
MAX_BODY = 64 * 1024
MAX_FIELD = 200
LOCK_WAIT = 10   # seconds a writer waits for the in-process lock before 503
DB_BUSY_WAIT = 5  # seconds sqlite waits for another process's lock

# Serialises write transactions inside this process; BEGIN IMMEDIATE also
# guards against a second process writing the same store.
WRITE_LOCK = threading.Lock()


class LoopbackHTTPServer(ThreadingHTTPServer):
    """Local transport does not need HTTPServer's reverse-DNS lookup."""
    daemon_threads = True

    def server_bind(self):
        TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


def reset_fixture():
    marker = DATA / '.fixture-owner'
    db = db_path()
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
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def connect():
    connection = sqlite3.connect(db_path(), timeout=DB_BUSY_WAIT, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection


def reservation_json(row):
    return {'id': row['id'], 'sessionId': row['session_id'],
            'attendeeAlias': row['attendee_alias'], 'requestKey': row['request_key'],
            'status': row['status']}


def list_sessions(connection):
    rows = connection.execute('''
        SELECT s.id, s.title, s.capacity,
               (SELECT COUNT(*) FROM reservations r
                 WHERE r.session_id = s.id AND r.status = 'active') AS active
          FROM sessions s ORDER BY s.id''').fetchall()
    return [{'id': r['id'], 'title': r['title'], 'capacity': r['capacity'],
             'activeCount': r['active'],
             # Raw difference on purpose: an oversell must show up as negative, not be hidden.
             'remainingSeats': r['capacity'] - r['active']} for r in rows]


def get_reservation(connection, reservation_id):
    row = connection.execute('SELECT * FROM reservations WHERE id = ?',
                             (reservation_id,)).fetchone()
    if row is None:
        raise ApiError(404, 'RESERVATION_NOT_FOUND',
                       'No reservation with id %r.' % reservation_id[:MAX_FIELD])
    return row


INVISIBLE = {'Cc', 'Cf', 'Zs', 'Zl', 'Zp'}


def is_blank(text):
    """True when nothing visible remains: whitespace, controls, zero-width/BOM chars."""
    return all(ch.isspace() or unicodedata.category(ch) in INVISIBLE for ch in text)


def check_text(name, value):
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        raise ApiError(400, 'INVALID_TEXT', '%s contains invalid Unicode (lone surrogate).' % name)
    if '\x00' in value:
        raise ApiError(400, 'INVALID_TEXT', '%s must not contain NUL characters.' % name)


def validate_create(body):
    if not isinstance(body, dict):
        raise ApiError(400, 'INVALID_BODY', 'Request body must be a JSON object.')
    session_id = body.get('sessionId')
    alias = body.get('attendeeAlias')
    key = body.get('requestKey')
    if not isinstance(session_id, str) or not session_id.strip():
        raise ApiError(400, 'MISSING_SESSION_ID', 'sessionId is required and must be a non-empty string.')
    if not isinstance(alias, str):
        raise ApiError(400, 'INVALID_ALIAS', 'attendeeAlias is required and must be a string.')
    check_text('attendeeAlias', alias)
    alias = alias.strip()
    if not alias or is_blank(alias):
        raise ApiError(400, 'BLANK_ALIAS', 'attendeeAlias must not be blank or whitespace-only.')
    if key is None:
        raise ApiError(400, 'MISSING_REQUEST_KEY', 'requestKey is required.')
    if not isinstance(key, str) or not key.strip():
        raise ApiError(400, 'INVALID_REQUEST_KEY',
                       'requestKey must be a non-empty, non-whitespace string.')
    check_text('sessionId', session_id)
    check_text('requestKey', key)
    if len(alias) > MAX_FIELD or len(key) > MAX_FIELD or len(session_id) > MAX_FIELD:
        raise ApiError(400, 'FIELD_TOO_LONG', 'Fields must be at most %d characters.' % MAX_FIELD)
    return session_id, alias, key


class write_lock:
    """WRITE_LOCK with a bounded wait so queued writers fail fast with 503."""
    def __enter__(self):
        if not WRITE_LOCK.acquire(timeout=LOCK_WAIT):
            raise ApiError(503, 'STORE_BUSY', 'Store is busy; retry shortly.')

    def __exit__(self, *exc):
        WRITE_LOCK.release()


def create_reservation(body):
    """Returns (http_status, reservation_dict). Atomic and idempotent per requestKey."""
    session_id, alias, key = validate_create(body)
    with write_lock(), closing(connect()) as connection:
        connection.execute('BEGIN IMMEDIATE')
        try:
            existing = connection.execute('SELECT * FROM reservations WHERE request_key = ?',
                                          (key,)).fetchone()
            if existing is not None:
                connection.execute('ROLLBACK')
                if existing['session_id'] == session_id and existing['attendee_alias'] == alias:
                    return 200, reservation_json(existing)
                raise ApiError(409, 'REQUEST_KEY_CONFLICT',
                               'requestKey was already used for a different session or alias.')
            session = connection.execute('SELECT capacity FROM sessions WHERE id = ?',
                                         (session_id,)).fetchone()
            if session is None:
                raise ApiError(404, 'UNKNOWN_SESSION', 'Unknown session %r.' % session_id)
            active = connection.execute(
                "SELECT COUNT(*) FROM reservations WHERE session_id = ? AND status = 'active'",
                (session_id,)).fetchone()[0]
            if active >= session['capacity']:
                raise ApiError(409, 'CAPACITY_FULL', 'No remaining seats in %s.' % session_id)
            reservation_id = uuid.uuid4().hex
            connection.execute(
                "INSERT INTO reservations (id, session_id, attendee_alias, request_key, status)"
                " VALUES (?, ?, ?, ?, 'active')", (reservation_id, session_id, alias, key))
            connection.execute('COMMIT')
        except BaseException:
            if connection.in_transaction:
                connection.execute('ROLLBACK')
            raise
        return 201, reservation_json(get_reservation(connection, reservation_id))


def cancel_reservation(reservation_id):
    with write_lock(), closing(connect()) as connection:
        connection.execute('BEGIN IMMEDIATE')
        try:
            get_reservation(connection, reservation_id)
            connection.execute("UPDATE reservations SET status = 'cancelled'"
                               " WHERE id = ? AND status = 'active'", (reservation_id,))
            connection.execute('COMMIT')
        except BaseException:
            if connection.in_transaction:
                connection.execute('ROLLBACK')
            raise
        return reservation_json(get_reservation(connection, reservation_id))


RESERVATION_PATH = re.compile(r'^/reservations/([^/]+)$')
CANCEL_PATH = re.compile(r'^/reservations/([^/]+)/cancel$')


class Handler(BaseHTTPRequestHandler):
    server_version = 'SessionSeatDesk/1.0'
    timeout = 30  # drop clients that stall mid-request instead of pinning a thread

    def json_response(self, status, value):
        payload = json.dumps(value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def error_response(self, error):
        self.json_response(error.status, {'error': {'code': error.code, 'message': error.message}})

    def read_json(self, allow_empty=False):
        if self.headers.get('Transfer-Encoding'):
            raise ApiError(411, 'LENGTH_REQUIRED', 'Chunked bodies are not supported; send Content-Length.')
        lengths = self.headers.get_all('Content-Length') or []
        if len(lengths) > 1:
            raise ApiError(400, 'INVALID_LENGTH', 'Send exactly one Content-Length header.')
        length_header = lengths[0].strip() if lengths else '0'
        if not (length_header.isascii() and length_header.isdigit()):
            raise ApiError(400, 'INVALID_LENGTH', 'Content-Length must be a non-negative integer.')
        length = int(length_header)
        if length > MAX_BODY:
            raise ApiError(413, 'BODY_TOO_LARGE', 'Request body is too large.')
        raw = self.rfile.read(length) if length else b''
        if not raw.strip():
            if allow_empty:
                return {}
            raise ApiError(400, 'MALFORMED_JSON', 'Request body must be a JSON object.')
        try:
            return json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, 'MALFORMED_JSON', 'Request body is not valid JSON.')
        except (ValueError, RecursionError):  # e.g. huge ints, absurd nesting
            raise ApiError(400, 'MALFORMED_JSON', 'Request body JSON is too deeply nested or out of range.')

    def path_only(self):
        # Route on the raw path; only the captured ID is percent-decoded, so an
        # encoded slash (%2F) can never create a different route.
        return urlsplit(self.path).path

    def dispatch(self, method):
        try:
            self.route(method, self.path_only())
        except ApiError as error:
            self.error_response(error)
        except sqlite3.OperationalError as exc:
            self.log_error('database error: %s', exc)
            if 'locked' in str(exc) or 'busy' in str(exc):
                self.error_response(ApiError(503, 'STORE_BUSY', 'Store is busy; retry shortly.'))
            else:
                self.error_response(ApiError(500, 'STORE_ERROR',
                    'Store is missing tables or unreadable; run --reset with a fresh DATA_DIR.'))
        except sqlite3.DatabaseError as exc:
            self.log_error('database error: %s', exc)
            self.error_response(ApiError(500, 'STORE_ERROR',
                'Store file is corrupt; run --reset with a fresh DATA_DIR.'))
        except Exception as exc:  # keep the process available
            self.log_error('unexpected error: %r', exc)
            self.error_response(ApiError(500, 'INTERNAL_ERROR', 'Unexpected server error.'))

    def route(self, method, path):
        if method == 'GET':
            if path in ('/', '/index.html'):
                return self.send_page()
            if path == '/health':
                return self.json_response(200, {'status': 'ok'})
            if path == '/sessions':
                with closing(connect()) as connection:
                    return self.json_response(200, {'sessions': list_sessions(connection)})
            if path == '/reservations':
                with closing(connect()) as connection:
                    rows = connection.execute(
                        'SELECT * FROM reservations ORDER BY rowid').fetchall()
                    return self.json_response(200, {'reservations': [reservation_json(r) for r in rows]})
            match = RESERVATION_PATH.match(path)
            if match:
                with closing(connect()) as connection:
                    return self.json_response(200, reservation_json(
                        get_reservation(connection, unquote(match.group(1)))))
        elif method == 'POST':
            if path == '/reservations':
                status, record = create_reservation(self.read_json())
                return self.json_response(status, record)
            match = CANCEL_PATH.match(path)
            if match:
                body = self.read_json(allow_empty=True)
                if not isinstance(body, dict):
                    raise ApiError(400, 'INVALID_BODY', 'Cancel body must be a JSON object.')
                return self.json_response(200, cancel_reservation(unquote(match.group(1))))
        raise ApiError(404, 'NOT_FOUND', 'No route for %s %s.' % (method, path[:MAX_FIELD]))

    def send_page(self):
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
        # No body allowed on HEAD: report method-not-allowed via status/headers only.
        self.send_response(405)
        self.send_header('Allow', 'GET, POST')
        self.send_header('Content-Length', '0')
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', help='Reset only the marked fixture DATA_DIR')
    args = parser.parse_args()
    if args.reset:
        try:
            reset_fixture()
        except (RuntimeError, sqlite3.DatabaseError) as exc:
            parser.exit(1, 'Reset refused: %s\n' % exc)
        return
    if not db_path().exists():
        parser.error('Run with --reset first, using the same DATA_DIR.')
    server = LoopbackHTTPServer(('127.0.0.1', int(os.environ.get('PORT', '8765'))), Handler)
    print('Session Seat Desk on http://127.0.0.1:%s (state: %s)' % (server.server_port, db_path()),
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
