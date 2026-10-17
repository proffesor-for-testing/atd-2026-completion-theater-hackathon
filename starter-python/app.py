"""Optional transport/storage scaffold, deliberately NOT a working solution.

Implement the PRD endpoints and browser behavior during the hackathon.
Run --reset explicitly before serving. Only this marked fixture store is reset.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
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


class Handler(BaseHTTPRequestHandler):
    def json_response(self, status, value):
        payload = json.dumps(value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == '/health':
            self.json_response(200, {'status': 'scaffold', 'implemented': False})
        elif self.path == '/':
            payload = (BASE / 'static' / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.json_response(501, {'error': {'code': 'NOT_IMPLEMENTED',
                'message': 'Implement the PRD read endpoints in your team copy.'}})

    def do_POST(self):
        self.json_response(501, {'error': {'code': 'NOT_IMPLEMENTED',
            'message': 'Implement reservation and cancellation in your team copy.'}})


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
    print('Scaffold only. Open http://127.0.0.1:%s' % server.server_port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
