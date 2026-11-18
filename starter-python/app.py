"""Session Seat Desk: local, durable workshop reservations (Python 3.11+)."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer
from urllib.parse import unquote, urlsplit
from uuid import uuid4

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(BASE / '.state'))).resolve()
MARKER = 'session-seat-desk-disposable-fixture-v1'
MAX_BODY_BYTES = 1024 * 1024


def reject_json_constant(value):
    """JSON permits no NaN or infinity literals, including in ignored fields."""
    raise ValueError('Nonstandard JSON constant: ' + value)


class APIError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def connect():
    connection = sqlite3.connect(DATA / 'seats.db', timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def reset_fixture():
    marker = DATA / '.fixture-owner'
    db = DATA / 'seats.db'
    if marker.exists() and marker.read_text() != MARKER:
        raise RuntimeError('Refusing to reset another fixture. Choose a new DATA_DIR.')
    if db.exists() and not marker.exists():
        raise RuntimeError('Refusing to reset an unmarked database. Choose a new DATA_DIR.')
    DATA.mkdir(parents=True, exist_ok=True)
    marker.write_text(MARKER)
    with closing(connect()) as connection:
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, capacity INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS reservations (
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
              attendee_alias TEXT NOT NULL, request_key TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL CHECK (status IN ('active','cancelled')));
            BEGIN IMMEDIATE;
            DELETE FROM reservations;
            DELETE FROM sessions;
        ''')
        try:
            seed = json.loads((BASE / 'sessions.json').read_text())
            connection.executemany('INSERT INTO sessions VALUES (:id,:title,:capacity)', seed)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    print('Reset disposable fixture:', db, flush=True)


def reservation_json(row):
    return {'id': row['id'], 'sessionId': row['session_id'],
            'attendeeAlias': row['attendee_alias'], 'requestKey': row['request_key'],
            'status': row['status']}


def sessions():
    with closing(connect()) as connection:
        rows = connection.execute('''
            SELECT s.id, s.title, s.capacity, COUNT(r.id) AS active_count
            FROM sessions s LEFT JOIN reservations r
              ON r.session_id = s.id AND r.status = 'active'
            GROUP BY s.id, s.title, s.capacity ORDER BY s.id
        ''').fetchall()
    return {'sessions': [{'id': row['id'], 'title': row['title'],
                          'capacity': row['capacity'], 'activeCount': row['active_count'],
                          'remainingSeats': row['capacity'] - row['active_count']}
                         for row in rows]}


def read_reservation(reservation_id):
    with closing(connect()) as connection:
        row = connection.execute('SELECT * FROM reservations WHERE id = ?',
                                 (reservation_id,)).fetchone()
    if row is None:
        raise APIError(404, 'RESERVATION_NOT_FOUND', 'No reservation has that ID.')
    return reservation_json(row)


def reserve(payload):
    session_id = payload.get('sessionId')
    alias = payload.get('attendeeAlias')
    key = payload.get('requestKey')
    if not isinstance(session_id, str) or not session_id:
        raise APIError(400, 'INVALID_SESSION', 'sessionId must be a non-empty string.')
    if not isinstance(alias, str) or not alias.strip():
        raise APIError(400, 'INVALID_ALIAS', 'attendeeAlias must contain a fictional alias.')
    if not isinstance(key, str) or not key:
        raise APIError(400, 'INVALID_KEY', 'requestKey must be a non-empty string.')
    alias = alias.strip()
    with closing(connect()) as connection:
        # Lock covers key lookup, capacity and insertion, including across processes.
        connection.execute('BEGIN IMMEDIATE')
        try:
            previous = connection.execute('SELECT * FROM reservations WHERE request_key = ?',
                                          (key,)).fetchone()
            if previous is not None:
                if previous['session_id'] != session_id or previous['attendee_alias'] != alias:
                    raise APIError(409, 'REQUEST_KEY_CONFLICT',
                                   'That request key belongs to a different session or alias.')
                result = reservation_json(previous)
                connection.commit()
                return 200, result
            session = connection.execute('SELECT capacity FROM sessions WHERE id = ?',
                                         (session_id,)).fetchone()
            if session is None:
                raise APIError(404, 'SESSION_NOT_FOUND', 'No session has that ID.')
            active = connection.execute(
                "SELECT COUNT(*) FROM reservations WHERE session_id = ? AND status = 'active'",
                (session_id,)).fetchone()[0]
            if active >= session['capacity']:
                raise APIError(409, 'CAPACITY_FULL', 'No remaining seats in this session.')
            reservation_id = uuid4().hex
            connection.execute('INSERT INTO reservations VALUES (?, ?, ?, ?, ?)',
                               (reservation_id, session_id, alias, key, 'active'))
            result = reservation_json(connection.execute(
                'SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone())
            connection.commit()
            return 201, result
        except Exception:
            connection.rollback()
            raise


def cancel(reservation_id):
    with closing(connect()) as connection:
        connection.execute('BEGIN IMMEDIATE')
        try:
            row = connection.execute('SELECT * FROM reservations WHERE id = ?',
                                     (reservation_id,)).fetchone()
            if row is None:
                raise APIError(404, 'RESERVATION_NOT_FOUND', 'No reservation has that ID.')
            connection.execute("UPDATE reservations SET status = 'cancelled' "
                               "WHERE id = ? AND status = 'active'", (reservation_id,))
            result = reservation_json(connection.execute('SELECT * FROM reservations WHERE id = ?',
                                                        (reservation_id,)).fetchone())
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise


class LoopbackHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self):
        TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def json_response(self, status, value):
        payload = json.dumps(value, ensure_ascii=True).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise APIError(400, 'INVALID_JSON', 'Content-Length must be an integer.')
        if length > MAX_BODY_BYTES:
            raise APIError(413, 'BODY_TOO_LARGE', 'JSON request is too large.')
        if length <= 0:
            raise APIError(400, 'INVALID_JSON', 'Send a JSON object in the request body.')
        try:
            payload = json.loads(self.rfile.read(length).decode('utf-8'),
                                 parse_constant=reject_json_constant)
        except (UnicodeDecodeError, ValueError, TimeoutError):
            raise APIError(400, 'INVALID_JSON', 'The request body must be valid UTF-8 JSON.')
        if not isinstance(payload, dict):
            raise APIError(400, 'INVALID_JSON', 'The request body must be a JSON object.')
        return payload

    def dispatch(self, method):
        path = urlsplit(self.path).path
        if method == 'GET' and path == '/':
            payload = (BASE / 'static' / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(payload)
        elif method == 'GET' and path == '/health':
            self.json_response(200, {'status': 'ok'})
        elif method == 'GET' and path == '/sessions':
            self.json_response(200, sessions())
        elif method == 'POST' and path == '/reservations':
            status, result = reserve(self.read_json())
            self.json_response(status, result)
        elif method == 'GET' and (match := re.fullmatch(r'/reservations/([^/]+)', path)):
            self.json_response(200, read_reservation(unquote(match[1])))
        elif method == 'POST' and (match := re.fullmatch(r'/reservations/([^/]+)/cancel', path)):
            self.read_json()
            self.json_response(200, cancel(unquote(match[1])))
        else:
            raise APIError(404, 'NOT_FOUND', 'No endpoint exists at that path.')

    def handle_request(self, method):
        try:
            self.dispatch(method)
        except APIError as error:
            self.json_response(error.status, {'error': {'code': error.code, 'message': error.message}})
        except sqlite3.Error:
            self.log_error('Database request failed')
            self.json_response(503, {'error': {'code': 'STORE_UNAVAILABLE',
                                            'message': 'The store is unavailable. Retry the same request key.'}})
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self.handle_request('GET')

    def do_POST(self):
        self.handle_request('POST')


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
    print('Session Seat Desk: http://127.0.0.1:%s' % server.server_port, flush=True)
    print('State:', DATA / 'seats.db', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
