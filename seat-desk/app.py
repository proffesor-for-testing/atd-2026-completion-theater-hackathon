"""Session Seat Desk: team-a submission, built from the organizer starter scaffold.

Run --reset explicitly before serving. Only this marked fixture store is reset.
Ordinary start never resets state.
"""
import argparse
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import sqlite3
import threading
import uuid
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
    """A rejection that maps to a 4xx JSON error response."""
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


# Serializes every write in this process. BEGIN IMMEDIATE additionally takes
# SQLite's write lock, so check-then-insert cannot interleave even across processes.
WRITE_LOCK = threading.Lock()


def connect():
    """Open a fresh connection per request; callers must close it.

    isolation_level=None leaves transaction control to explicit BEGIN/COMMIT.
    """
    connection = sqlite3.connect(DATA / 'seats.db', timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def write_transaction():
    with WRITE_LOCK, closing(connect()) as connection:
        connection.execute('BEGIN IMMEDIATE')
        try:
            yield connection
        except BaseException:
            connection.execute('ROLLBACK')
            raise
        connection.execute('COMMIT')


def reservation_json(row):
    return {'id': row['id'], 'sessionId': row['session_id'], 'attendeeAlias': row['attendee_alias'],
            'requestKey': row['request_key'], 'status': row['status']}


def get_reservation(connection, reservation_id):
    row = connection.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
    if row is None:
        raise ApiError(404, 'UNKNOWN_RESERVATION', 'No reservation with id %r.' % reservation_id)
    return reservation_json(row)


def list_reservations(connection):
    rows = connection.execute('SELECT * FROM reservations ORDER BY rowid')
    return [reservation_json(row) for row in rows]


def create_reservation(body):
    """Validate, then replay/conflict/capacity-check/insert inside one write transaction.

    Returns (http_status, reservation): 201 for a new reservation, 200 for a replay.
    """
    if not isinstance(body, dict):
        raise ApiError(400, 'INVALID_BODY', 'Request body must be a JSON object.')
    request_key = body.get('requestKey')
    if not isinstance(request_key, str) or request_key == '':
        raise ApiError(400, 'MISSING_REQUEST_KEY', 'requestKey must be a non-empty string.')
    alias = body.get('attendeeAlias')
    if not isinstance(alias, str) or alias.strip() == '':
        raise ApiError(400, 'INVALID_ALIAS', 'attendeeAlias must be a non-blank string.')
    alias = alias.strip()
    session_id = body.get('sessionId')
    if not isinstance(session_id, str) or session_id == '':
        raise ApiError(400, 'MISSING_SESSION', 'sessionId must be a non-empty string.')

    with write_transaction() as connection:
        session = connection.execute('SELECT capacity FROM sessions WHERE id = ?', (session_id,)).fetchone()
        if session is None:
            raise ApiError(404, 'UNKNOWN_SESSION', 'No session with id %r.' % session_id)
        existing = connection.execute('SELECT * FROM reservations WHERE request_key = ?',
                                      (request_key,)).fetchone()
        if existing is not None:
            if existing['session_id'] == session_id and existing['attendee_alias'] == alias:
                return 200, reservation_json(existing)
            raise ApiError(409, 'KEY_CONFLICT',
                           'requestKey %r was already used for a different session or alias.' % request_key)
        active = connection.execute(
            "SELECT COUNT(*) FROM reservations WHERE session_id = ? AND status = 'active'",
            (session_id,)).fetchone()[0]
        if active >= session['capacity']:
            raise ApiError(409, 'CAPACITY_FULL', 'Session %s has no remaining seats.' % session_id)
        reservation_id = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO reservations (id, session_id, attendee_alias, request_key, status) "
            "VALUES (?, ?, ?, ?, 'active')", (reservation_id, session_id, alias, request_key))
        row = connection.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
        return 201, reservation_json(row)


def cancel_reservation(reservation_id):
    """Active -> cancelled releases one seat; repeating it is a no-op that reports cancelled."""
    with write_transaction() as connection:
        get_reservation(connection, reservation_id)  # 404 if unknown
        connection.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ? AND status = 'active'",
                           (reservation_id,))
        return get_reservation(connection, reservation_id)


SESSIONS_SQL = '''
    SELECT s.id, s.title, s.capacity,
           (SELECT COUNT(*) FROM reservations r
             WHERE r.session_id = s.id AND r.status = 'active') AS activeCount
      FROM sessions s ORDER BY s.id'''


def list_sessions(connection):
    sessions = []
    for row in connection.execute(SESSIONS_SQL):
        sessions.append({'id': row['id'], 'title': row['title'], 'capacity': row['capacity'],
                         'activeCount': row['activeCount'],
                         'remainingSeats': row['capacity'] - row['activeCount']})
    return sessions


class Handler(BaseHTTPRequestHandler):
    def json_response(self, status, value):
        payload = json.dumps(value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def error_response(self, error):
        self.json_response(error.status, {'error': {'code': error.code, 'message': error.message}})

    def read_json_body(self):
        try:
            length = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            raise ApiError(400, 'MALFORMED_JSON', 'Invalid Content-Length header.')
        raw = self.rfile.read(length) if length > 0 else b''
        try:
            return json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, 'MALFORMED_JSON', 'Request body is not valid JSON.')

    def handle_safely(self, route):
        """Every failure becomes a JSON response; the server keeps serving."""
        try:
            route()
        except ApiError as error:
            self.error_response(error)
        except Exception as error:  # Unexpected: log it, report 500, stay available.
            self.log_error('Unhandled %s: %s', type(error).__name__, error)
            self.json_response(500, {'error': {'code': 'INTERNAL', 'message': 'Unexpected server error.'}})

    def do_GET(self):
        self.handle_safely(self.route_get)

    def do_POST(self):
        self.handle_safely(self.route_post)

    def route_post(self):
        path = self.path.split('?', 1)[0]
        if path == '/reservations':
            status, reservation = create_reservation(self.read_json_body())
            self.json_response(status, reservation)
        elif path.startswith('/reservations/') and path.endswith('/cancel') and path.count('/') == 3:
            reservation_id = path[len('/reservations/'):-len('/cancel')]
            if self.headers.get('Content-Length', '0') not in ('', '0'):
                self.read_json_body()  # Body should be {}; malformed JSON rejects before any change.
            self.json_response(200, cancel_reservation(reservation_id))
        else:
            raise ApiError(404, 'NOT_FOUND', 'No such endpoint: POST %s' % path)

    def route_get(self):
        path = self.path.split('?', 1)[0]
        if path == '/sessions':
            with closing(connect()) as connection:
                self.json_response(200, {'sessions': list_sessions(connection)})
        elif path == '/reservations':
            with closing(connect()) as connection:
                self.json_response(200, {'reservations': list_reservations(connection)})
        elif path.startswith('/reservations/') and path.count('/') == 2:
            with closing(connect()) as connection:
                self.json_response(200, get_reservation(connection, path[len('/reservations/'):]))
        elif path == '/health':
            self.json_response(200, {'status': 'ok'})
        elif path == '/':
            payload = (BASE / 'static' / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            raise ApiError(404, 'NOT_FOUND', 'No such endpoint: GET %s' % path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', help='Reset only the marked fixture DATA_DIR')
    args = parser.parse_args()
    if args.reset:
        reset_fixture()
        return
    if not (DATA / 'seats.db').exists():
        parser.error('Run with --reset first, using the same DATA_DIR.')
    server = LoopbackHTTPServer(('127.0.0.1', int(os.environ.get('PORT', '8765'))), Handler)
    print('Session Seat Desk on http://127.0.0.1:%s  state: %s' % (server.server_port, DATA / 'seats.db'), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
