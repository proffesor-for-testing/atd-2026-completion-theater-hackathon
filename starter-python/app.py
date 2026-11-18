"""Session Seat Desk: local JSON API + basic UI backed by SQLite.

Run --reset explicitly before serving. Only the marked fixture store is reset.
Ordinary start never resets or reseeds.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(BASE / '.state'))).resolve()
DB_PATH = DATA / 'seats.db'
MARKER = 'session-seat-desk-disposable-fixture-v1'
MAX_BODY = 64 * 1024


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class LoopbackHTTPServer(ThreadingHTTPServer):
    """Local transport does not need HTTPServer's reverse-DNS lookup."""
    daemon_threads = True

    def server_bind(self):
        TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


def connect():
    # Autocommit mode: transactions are opened explicitly with BEGIN IMMEDIATE.
    connection = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA busy_timeout = 30000')
    return connection


def reset_fixture():
    marker = DATA / '.fixture-owner'
    if DB_PATH.exists() and (not marker.exists() or marker.read_text() != MARKER):
        raise RuntimeError('Refusing to reset an unmarked database. Choose a new DATA_DIR.')
    DATA.mkdir(parents=True, exist_ok=True)
    marker.write_text(MARKER)
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.executescript('''
            DROP TABLE IF EXISTS reservations;
            DROP TABLE IF EXISTS sessions;
            CREATE TABLE sessions (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, capacity INTEGER NOT NULL);
            CREATE TABLE reservations (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL REFERENCES sessions(id),
              attendee_alias TEXT NOT NULL,
              request_key TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL CHECK (status IN ('active','cancelled')),
              created_seq INTEGER NOT NULL);
        ''')
        seed = json.loads((BASE / 'sessions.json').read_text())
        connection.executemany('INSERT INTO sessions VALUES (:id,:title,:capacity)', seed)
    print('Reset fixture:', DB_PATH)


# ---------------------------------------------------------------- data access

def reservation_json(row):
    return {
        'id': row['id'],
        'sessionId': row['session_id'],
        'attendeeAlias': row['attendee_alias'],
        'requestKey': row['request_key'],
        'status': row['status'],
    }


def list_sessions(connection):
    rows = connection.execute('''
        SELECT s.id, s.title, s.capacity,
               (SELECT COUNT(*) FROM reservations r
                 WHERE r.session_id = s.id AND r.status = 'active') AS active
          FROM sessions s ORDER BY s.id''').fetchall()
    return [{
        'id': r['id'], 'title': r['title'], 'capacity': r['capacity'],
        'activeCount': r['active'], 'remainingSeats': r['capacity'] - r['active'],
    } for r in rows]


def get_reservation(connection, reservation_id):
    row = connection.execute('SELECT * FROM reservations WHERE id = ?',
                             (reservation_id,)).fetchone()
    if row is None:
        raise ApiError(404, 'RESERVATION_NOT_FOUND', 'Unknown reservation id.')
    return reservation_json(row)


def validate_create(body):
    if not isinstance(body, dict):
        raise ApiError(400, 'INVALID_BODY', 'Request body must be a JSON object.')
    session_id = body.get('sessionId')
    alias = body.get('attendeeAlias')
    key = body.get('requestKey')
    if not isinstance(session_id, str) or not session_id:
        raise ApiError(400, 'INVALID_SESSION_ID', 'sessionId is required and must be a string.')
    if not isinstance(alias, str) or not alias.strip():
        raise ApiError(400, 'INVALID_ALIAS', 'attendeeAlias is required and must not be blank.')
    if not isinstance(key, str) or not key:
        raise ApiError(400, 'INVALID_REQUEST_KEY', 'requestKey is required and must be a non-empty string.')
    return session_id, alias.strip(), key


def create_reservation(connection, body):
    """Returns (http_status, reservation). All checks and the insert run in one
    write transaction, so concurrent requests are serialized by SQLite."""
    session_id, alias, key = validate_create(body)
    connection.execute('BEGIN IMMEDIATE')
    try:
        existing = connection.execute('SELECT * FROM reservations WHERE request_key = ?',
                                      (key,)).fetchone()
        if existing is not None:
            if existing['session_id'] == session_id and existing['attendee_alias'] == alias:
                connection.execute('COMMIT')
                return 200, reservation_json(existing)
            raise ApiError(409, 'REQUEST_KEY_CONFLICT',
                           'requestKey was already used for a different session or alias.')
        session = connection.execute('SELECT capacity FROM sessions WHERE id = ?',
                                     (session_id,)).fetchone()
        if session is None:
            raise ApiError(404, 'SESSION_NOT_FOUND', 'Unknown sessionId.')
        active = connection.execute(
            "SELECT COUNT(*) FROM reservations WHERE session_id = ? AND status = 'active'",
            (session_id,)).fetchone()[0]
        if active >= session['capacity']:
            raise ApiError(409, 'CAPACITY_FULL', 'No remaining seats for this session.')
        seq = connection.execute('SELECT COALESCE(MAX(created_seq), 0) + 1 FROM reservations').fetchone()[0]
        new_id = 'res-' + uuid.uuid4().hex
        connection.execute(
            "INSERT INTO reservations VALUES (?, ?, ?, ?, 'active', ?)",
            (new_id, session_id, alias, key, seq))
        connection.execute('COMMIT')
    except BaseException:
        if connection.in_transaction:
            connection.execute('ROLLBACK')
        raise
    return 201, get_reservation(connection, new_id)


def cancel_reservation(connection, reservation_id):
    connection.execute('BEGIN IMMEDIATE')
    try:
        row = connection.execute('SELECT id FROM reservations WHERE id = ?',
                                 (reservation_id,)).fetchone()
        if row is None:
            raise ApiError(404, 'RESERVATION_NOT_FOUND', 'Unknown reservation id.')
        connection.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?",
                           (reservation_id,))
        connection.execute('COMMIT')
    except BaseException:
        if connection.in_transaction:
            connection.execute('ROLLBACK')
        raise
    return get_reservation(connection, reservation_id)


def list_reservations(connection):
    rows = connection.execute('SELECT * FROM reservations ORDER BY created_seq').fetchall()
    return [reservation_json(r) for r in rows]


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = 'SessionSeatDesk/1.0'

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

    def send_error_json(self, status, code, message):
        self.send_json(status, {'error': {'code': code, 'message': message}})

    def read_json(self, allow_empty=False):
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            raise ApiError(400, 'INVALID_LENGTH', 'Invalid Content-Length header.')
        if length < 0 or length > MAX_BODY:
            raise ApiError(413, 'BODY_TOO_LARGE', 'Request body is too large.')
        raw = self.rfile.read(length) if length else b''
        if not raw.strip():
            if allow_empty:
                return {}
            raise ApiError(400, 'MALFORMED_JSON', 'Request body must be valid JSON.')
        try:
            return json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            raise ApiError(400, 'MALFORMED_JSON', 'Request body must be valid JSON.')

    def route_path(self):
        return self.path.split('?', 1)[0].rstrip('/') or '/'

    def handle_api(self, func):
        try:
            with closing(connect()) as connection:
                func(connection)
        except ApiError as error:
            self.send_error_json(error.status, error.code, error.message)
        except Exception as error:  # keep the process available
            sys.stderr.write('Internal error: %r\n' % (error,))
            self.send_error_json(500, 'INTERNAL_ERROR', 'Unexpected server error.')

    def do_GET(self):
        path = self.route_path()
        if path == '/':
            payload = (BASE / 'static' / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(payload)
        elif path == '/health':
            self.send_json(200, {'status': 'ok', 'stateFile': str(DB_PATH)})
        elif path == '/sessions':
            self.handle_api(lambda c: self.send_json(200, {'sessions': list_sessions(c)}))
        elif path == '/reservations':
            self.handle_api(lambda c: self.send_json(200, {'reservations': list_reservations(c)}))
        elif path.startswith('/reservations/') and path.count('/') == 2:
            rid = path.split('/')[2]
            self.handle_api(lambda c: self.send_json(200, get_reservation(c, rid)))
        else:
            self.send_error_json(404, 'NOT_FOUND', 'Unknown path.')

    def do_POST(self):
        path = self.route_path()
        parts = path.split('/')
        if path == '/reservations':
            def create(connection):
                status, record = create_reservation(connection, self.read_json())
                self.send_json(status, record)
            self.handle_api(create)
        elif len(parts) == 4 and parts[1] == 'reservations' and parts[3] == 'cancel':
            def cancel(connection):
                body = self.read_json(allow_empty=True)
                if not isinstance(body, dict):
                    raise ApiError(400, 'INVALID_BODY', 'Request body must be a JSON object.')
                self.send_json(200, cancel_reservation(connection, parts[2]))
            self.handle_api(cancel)
        else:
            self.send_error_json(404, 'NOT_FOUND', 'Unknown path.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', help='Reset only the marked fixture DATA_DIR')
    args = parser.parse_args()
    if args.reset:
        reset_fixture()
        return
    if not DB_PATH.exists():
        parser.error('Run with --reset first, using the same DATA_DIR.')
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.execute('PRAGMA journal_mode = WAL')
    server = LoopbackHTTPServer(('127.0.0.1', int(os.environ.get('PORT', '8765'))), Handler)
    print('Session Seat Desk on http://127.0.0.1:%s  state: %s (pid %s)'
          % (server.server_port, DB_PATH, os.getpid()), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
