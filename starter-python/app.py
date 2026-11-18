"""Optional transport/storage scaffold, deliberately NOT a working solution.

Implement the PRD endpoints and browser behavior during the hackathon.
Run --reset explicitly before serving. Only this marked fixture store is reset.
"""
import argparse
import json
import os
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer

import reservations
import storage
import ui
import uuid

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(BASE / '.state'))).resolve()
MARKER = 'session-seat-desk-disposable-fixture-v1'


STATE_FILE = 'state.json'
RESERVATION_LOCK = threading.Lock()  # serialises capacity check and save


def active_count(state, session_id):
    """Pure: active reservations for one session."""
    return sum(1 for r in state['reservations']
               if r['sessionId'] == session_id and r['status'] == 'active')


def session_views(state):
    """Pure: stored state -> session records in API shape."""
    views = []
    for session in state['sessions']:
        active = active_count(state, session['id'])
        views.append({'id': session['id'], 'title': session['title'],
                      'capacity': session['capacity'], 'activeCount': active,
                      'remainingSeats': session['capacity'] - active})
    return views


def read_sessions():
    """Session records in API shape, read from the fixture state file."""
    return session_views(storage.load_state(DATA / STATE_FILE))


class LoopbackHTTPServer(ThreadingHTTPServer):
    """Local transport does not need HTTPServer's reverse-DNS lookup."""
    request_queue_size = 64  # default backlog of 5 resets simultaneous connections
    def server_bind(self):
        TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


def reset_fixture(data_dir: Path = DATA) -> Path:
    """Reset only the marked fixture store in data_dir. Returns the state file path."""
    data_dir = Path(data_dir)
    marker = data_dir / '.fixture-owner'
    state_file = data_dir / STATE_FILE
    if state_file.exists() and (not marker.exists() or marker.read_text() != MARKER):
        raise RuntimeError('Refusing to reset an unmarked state file. Choose a new DATA_DIR.')
    data_dir.mkdir(parents=True, exist_ok=True)
    marker.write_text(MARKER)
    seed = json.loads((BASE / 'sessions.json').read_text())
    storage.save_state(state_file, {'sessions': seed, 'reservations': []})
    return state_file


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
        elif self.path == '/sessions':
            try:
                self.json_response(200, {'sessions': read_sessions()})
            except ValueError:
                self.json_response(500, {'error': {'code': 'STATE_CORRUPT',
                    'message': 'State file %s is corrupt; refusing to load it' % (DATA / STATE_FILE)}})
        elif self.path.startswith('/reservations/'):
            reservation_id = self.path[len('/reservations/'):]
            record = reservations.find_reservation(
                storage.load_state(DATA / STATE_FILE), reservation_id)
            if record is None:
                self.json_response(404, {'error': {'code': 'NOT_FOUND',
                    'message': 'No reservation with ID %s' % reservation_id}})
            else:
                self.json_response(200, record)
        elif self.path == '/':
            payload = ui.render_page(read_sessions()).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.json_response(501, {'error': {'code': 'NOT_IMPLEMENTED',
                'message': 'Implement the PRD read endpoints in your team copy.'}})

    def do_POST(self):
        if self.path.startswith('/reservations/') and self.path.endswith('/cancel'):
            reservation_id = self.path[len('/reservations/'):-len('/cancel')].rstrip('/')
            state_file = DATA / STATE_FILE
            with RESERVATION_LOCK:
                state = storage.load_state(state_file)
                record = reservations.find_reservation(state, reservation_id)
                if record is None:
                    self.json_response(404, {'error': {'code': 'NOT_FOUND',
                        'message': 'No reservation with ID %s' % reservation_id}})
                    return
                updated = reservations.cancel_reservation(state, reservation_id)
                storage.save_state(state_file, updated)
            self.json_response(200, reservations.find_reservation(updated, reservation_id))
        elif self.path == '/reservations':
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            record = reservations.new_reservation(uuid.uuid4().hex, body['sessionId'],
                                                  body['attendeeAlias'], body['requestKey'])
            state_file = DATA / STATE_FILE
            with RESERVATION_LOCK:
                state = storage.load_state(state_file)
                replay = reservations.find_replay(state, record)
                if replay is not None:
                    self.json_response(200, replay)
                    return
                if reservations.find_key_conflict(state, record) is not None:
                    self.json_response(409, {'error': {'code': 'KEY_CONFLICT',
                        'message': 'Request key %s was already used for another reservation'
                                   % record['requestKey']}})
                    return
                try:
                    updated = reservations.add_active_reservation(state, record)
                except reservations.CapacityFull as error:
                    self.json_response(409, {'error': {'code': 'CAPACITY_FULL',
                        'message': str(error)}})
                    return
                storage.save_state(state_file, updated)
            self.json_response(201, record)
        else:
            self.json_response(501, {'error': {'code': 'NOT_IMPLEMENTED',
                'message': 'Implement reservation and cancellation in your team copy.'}})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', help='Reset only the marked fixture DATA_DIR')
    args = parser.parse_args()
    if args.reset:
        print('Reset fixture:', reset_fixture(DATA))
        return
    if not (DATA / STATE_FILE).exists():
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
