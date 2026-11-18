"""Session Seat Desk: local JSON API + UI backed by SQLite (stdlib only).

Run --reset explicitly before serving. Only this marked fixture store is reset.
State lives in DATA_DIR/seats.db (default: .state/ next to this file).
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import uuid
from urllib.parse import urlparse
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


MAX_BODY = 65536


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def connect():
    """New connection per request: the server is multi-threaded. Autocommit with
    explicit BEGIN IMMEDIATE so each write takes SQLite's write lock before it reads."""
    connection = sqlite3.connect(DATA / 'seats.db', timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection


def reservation_record(row):
    return {'id': row['id'], 'sessionId': row['session_id'],
            'attendeeAlias': row['attendee_alias'], 'requestKey': row['request_key'],
            'status': row['status']}


def list_sessions():
    with closing(connect()) as db:
        rows = db.execute('''
            SELECT s.id, s.title, s.capacity,
                   (SELECT COUNT(*) FROM reservations r
                     WHERE r.session_id = s.id AND r.status = 'active') AS active
              FROM sessions s ORDER BY s.id''').fetchall()
    return {'sessions': [{'id': r['id'], 'title': r['title'], 'capacity': r['capacity'],
                          'activeCount': r['active'],
                          'remainingSeats': max(r['capacity'] - r['active'], 0)} for r in rows]}


def get_reservation(reservation_id):
    with closing(connect()) as db:
        row = db.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
    if row is None:
        raise ApiError(404, 'NOT_FOUND', 'Unknown reservation')
    return reservation_record(row)


def create_reservation(payload):
    session_id = payload.get('sessionId')
    alias = payload.get('attendeeAlias')
    key = payload.get('requestKey')
    if not isinstance(session_id, str) or not session_id:
        raise ApiError(400, 'INVALID_SESSION', 'sessionId must be a non-empty string')
    if not isinstance(alias, str) or not alias.strip():
        raise ApiError(400, 'INVALID_ALIAS', 'attendeeAlias must be a non-blank string')
    if not isinstance(key, str) or not key.strip():
        raise ApiError(400, 'INVALID_REQUEST_KEY', 'requestKey must be a non-empty string')
    for name, value in (('sessionId', session_id), ('attendeeAlias', alias), ('requestKey', key)):
        try:
            value.encode('utf-8')  # a lone surrogate parses as JSON but cannot be stored
        except UnicodeEncodeError:
            raise ApiError(400, 'INVALID_TEXT', '%s must be valid Unicode text' % name)
    alias = alias.strip()
    with closing(connect()) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            session = db.execute('SELECT capacity FROM sessions WHERE id = ?', (session_id,)).fetchone()
            if session is None:
                raise ApiError(404, 'UNKNOWN_SESSION', 'Unknown session: %s' % session_id)
            existing = db.execute('SELECT * FROM reservations WHERE request_key = ?', (key,)).fetchone()
            if existing is not None:
                if existing['session_id'] != session_id or existing['attendee_alias'] != alias:
                    raise ApiError(409, 'KEY_CONFLICT',
                                   'requestKey was already used for a different session or alias')
                db.execute('COMMIT')
                return 200, reservation_record(existing)  # replay: no state change
            active = db.execute("SELECT COUNT(*) FROM reservations WHERE session_id = ? AND status = 'active'",
                                (session_id,)).fetchone()[0]
            if active >= session['capacity']:
                raise ApiError(409, 'CAPACITY_FULL', 'No remaining seats')
            record = {'id': uuid.uuid4().hex, 'sessionId': session_id, 'attendeeAlias': alias,
                      'requestKey': key, 'status': 'active'}
            db.execute('INSERT INTO reservations (id, session_id, attendee_alias, request_key, status) '
                       'VALUES (?,?,?,?,?)', (record['id'], session_id, alias, key, 'active'))
            db.execute('COMMIT')
            return 201, record
        except BaseException:
            if db.in_transaction:
                db.execute('ROLLBACK')
            raise


def cancel_reservation(reservation_id):
    with closing(connect()) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            row = db.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
            if row is None:
                raise ApiError(404, 'NOT_FOUND', 'Unknown reservation')
            db.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ? AND status = 'active'",
                       (reservation_id,))
            row = db.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
            db.execute('COMMIT')
            return reservation_record(row)
        except BaseException:
            if db.in_transaction:
                db.execute('ROLLBACK')
            raise


class Handler(BaseHTTPRequestHandler):
    def json_response(self, status, value):
        payload = json.dumps(value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def error_response(self, status, code, message):
        self.json_response(status, {'error': {'code': code, 'message': message}})

    def read_body(self, allow_empty=False):
        if self.headers.get('Transfer-Encoding'):  # only Content-Length framing is read: never guess a body
            raise ApiError(411, 'LENGTH_REQUIRED', 'Send a Content-Length body; chunked encoding is not supported')
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            raise ApiError(400, 'INVALID_JSON', 'Bad Content-Length')
        if length < 0 or length > MAX_BODY:
            raise ApiError(413 if length > MAX_BODY else 400, 'INVALID_BODY', 'Body size not accepted')
        raw = self.rfile.read(length) if length else b''
        if not raw.strip():
            if allow_empty:
                return {}
            raise ApiError(400, 'INVALID_JSON', 'A JSON object body is required')
        try:
            payload = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, ValueError, RecursionError):  # RecursionError: deeply nested input
            raise ApiError(400, 'INVALID_JSON', 'Body is not valid JSON')
        if not isinstance(payload, dict):
            raise ApiError(400, 'INVALID_JSON', 'Body must be a JSON object')
        return payload

    def route(self, method):
        parts = [p for p in urlparse(self.path).path.split('/') if p]
        if method == 'GET' and parts == []:
            payload = (BASE / 'static' / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if parts == ['health']:
            allowed, action = 'GET', lambda: (200, {'status': 'ok'})
        elif parts == ['sessions']:
            allowed, action = 'GET', lambda: (200, list_sessions())
        elif parts == ['reservations']:
            allowed, action = 'POST', lambda: create_reservation(self.read_body())
        elif len(parts) == 2 and parts[0] == 'reservations':
            allowed, action = 'GET', lambda: (200, get_reservation(parts[1]))
        elif len(parts) == 3 and parts[0] == 'reservations' and parts[2] == 'cancel':
            allowed = 'POST'
            action = lambda: (self.read_body(allow_empty=True), (200, cancel_reservation(parts[1])))[1]
        else:
            raise ApiError(404, 'NOT_FOUND', 'No such route')
        if method != allowed:
            raise ApiError(405, 'METHOD_NOT_ALLOWED', 'Use %s for this path' % allowed)
        self.json_response(*action())

    def dispatch(self, method):
        try:
            self.route(method)
        except ApiError as err:
            self.error_response(err.status, err.code, err.message)
        except sqlite3.OperationalError as err:
            self.error_response(503, 'STORE_BUSY', 'State store unavailable: %s' % err)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as err:  # keep the process alive; never report an error as 200
            self.error_response(500, 'INTERNAL_ERROR', type(err).__name__)

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', help='Reset only the marked fixture DATA_DIR')
    args = parser.parse_args()
    if args.reset:
        reset_fixture()
        return
    if not (DATA / 'seats.db').exists():
        parser.error('Run with --reset first, using the same DATA_DIR.')
    marker = DATA / '.fixture-owner'
    if not marker.exists() or marker.read_text() != MARKER:
        parser.error('Refusing to serve %s: it is not a fixture created by this app (missing or wrong '
                     '.fixture-owner marker). Choose a new DATA_DIR and run --reset.' % (DATA / 'seats.db'))
    server = LoopbackHTTPServer(('127.0.0.1', int(os.environ.get('PORT', '8765'))), Handler)
    print('Session Seat Desk on http://127.0.0.1:%s (state: %s)' % (server.server_port, DATA / 'seats.db'), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
