"""Session Seat Desk — local JSON API and UI. Python 3.11+ standard library only.

    python3 app.py --reset    # explicit, fixture-only reset (never automatic)
    python3 app.py            # serve on 127.0.0.1:$PORT (default 8765), state in $DATA_DIR

The PRD rules live in store.py. This module is transport: routing, body limits,
JSON errors and security headers.
"""
import argparse
import json
import os
import re
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import TCPServer
from urllib.parse import parse_qs, urlsplit

from store import Store, StoreError

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(BASE / '.state'))).resolve()
MAX_BODY = 16 * 1024
RESERVATION_PATH = re.compile(r'^/reservations/([A-Za-z0-9-]{1,64})$')
CANCEL_PATH = re.compile(r'^/reservations/([A-Za-z0-9-]{1,64})/cancel$')

# Static files are an allow-list: no part of a URL is ever joined onto a filesystem path.
STATIC = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/index.html': ('index.html', 'text/html; charset=utf-8'),
    '/static/styles.css': ('styles.css', 'text/css; charset=utf-8'),
    '/static/app.js': ('app.js', 'text/javascript; charset=utf-8'),
    '/favicon.svg': ('favicon.svg', 'image/svg+xml'),
}

PAGE_CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; font-src 'self'; base-uri 'none'; form-action 'self'; "
            "frame-ancestors 'none'")
API_CSP = "default-src 'none'; frame-ancestors 'none'"
COMMON_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Resource-Policy': 'same-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
}


LOG_LOCK = threading.Lock()
LOG_PATH = None  # set in main(): $DATA_DIR/server.log


def log_event(record):
    """One JSON line per event, to stdout and to $DATA_DIR/server.log.

    Aliases and request keys are deliberately NOT logged: the log records what happened
    to which reservation ID, not who it was for.
    """
    record = {'ts': datetime.now(timezone.utc).isoformat(timespec='milliseconds'), **record}
    line = json.dumps(record, separators=(',', ':'))
    with LOG_LOCK:
        print(line, flush=True)
        if LOG_PATH is not None:
            with open(LOG_PATH, 'a', encoding='utf-8') as handle:
                handle.write(line + '\n')


class LoopbackHTTPServer(ThreadingHTTPServer):
    """Local transport does not need HTTPServer's reverse-DNS lookup."""
    daemon_threads = True
    # The default backlog of 5 refuses connections when the AC-04 burst of ten arrives
    # at once (observed on Windows as ECONNREFUSED). 128 queues them instead.
    request_queue_size = 128

    def server_bind(self):
        TCPServer.server_bind(self)
        self.server_name = 'localhost'
        self.server_port = self.server_address[1]


class Handler(BaseHTTPRequestHandler):
    server_version = 'SeatDesk'
    sys_version = ''
    protocol_version = 'HTTP/1.1'
    timeout = 10  # seconds a client may stall a socket (slowloris)
    store = None  # set in main()

    # -- responses -------------------------------------------------------------

    def _security_headers(self, csp):
        for name, value in COMMON_HEADERS.items():
            self.send_header(name, value)
        self.send_header('Content-Security-Policy', csp)

    def json_response(self, status, value, extra=None):
        payload = json.dumps(value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self._security_headers(API_CSP)
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        if self.close_connection:
            self.send_header('Connection', 'close')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)

    def error_response(self, status, code, message, extra=None):
        self.json_response(status, {'error': {'code': code, 'message': message}}, extra)

    def send_error(self, code, message=None, explain=None):
        """Every error the base class raises (bad request line, 501, ...) is JSON too."""
        self.close_connection = True
        try:
            self.error_response(code, 'HTTP_%d' % code, message or self.responses.get(code, ('Error',))[0])
        except Exception:
            pass

    def version_string(self):
        return self.server_version

    # -- logging -----------------------------------------------------------------

    def parse_request(self):
        # Every request passes here first, including 405s and malformed ones, so the log
        # state is reset per request rather than inherited from the previous one on a
        # kept-alive connection (K1: a refused DELETE was logged as reservation.created).
        self._t0 = time.perf_counter()
        self._event = None
        return super().parse_request()

    def log_request(self, code='-', size='-'):
        started = getattr(self, '_t0', None)
        record = {
            'level': 'info' if int(code) < 500 else 'error',
            'method': self.command,
            'path': urlsplit(self.path).path if getattr(self, 'path', None) else None,
            'status': int(code),
            'ms': round((time.perf_counter() - started) * 1000, 1) if started else None,
        }
        record.update(getattr(self, '_event', None) or {})
        log_event(record)

    def log_message(self, format, *args):
        log_event({'level': 'warn', 'message': format % args})

    # -- request plumbing ------------------------------------------------------

    def _read_json(self):
        """Parse a bounded JSON body. Returns the value, or raises StoreError."""
        if 'chunked' in self.headers.get('Transfer-Encoding', '').lower():
            self.close_connection = True
            raise StoreError(411, 'LENGTH_REQUIRED', 'Send a Content-Length; chunked bodies are not accepted.')
        raw_length = self.headers.get('Content-Length')
        try:
            length = int(raw_length) if raw_length is not None else 0
        except ValueError:
            self.close_connection = True
            raise StoreError(400, 'BAD_LENGTH', 'Content-Length must be an integer.')
        if length < 0:
            self.close_connection = True
            raise StoreError(400, 'BAD_LENGTH', 'Content-Length must not be negative.')
        if length > MAX_BODY:
            self.close_connection = True  # the unread body must not be parsed as the next request
            raise StoreError(413, 'BODY_TOO_LARGE', 'Request body exceeds %d bytes.' % MAX_BODY)
        raw = self.rfile.read(length) if length else b''
        self._body_consumed = True
        content_type = self.headers.get('Content-Type', '').split(';')[0].strip().lower()
        if content_type != 'application/json':
            raise StoreError(415, 'UNSUPPORTED_MEDIA_TYPE', 'Content-Type must be application/json.')
        if not raw.strip():
            raise StoreError(400, 'MALFORMED_JSON', 'Request body must be a JSON object.')
        try:
            return json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            raise StoreError(400, 'MALFORMED_JSON', 'Request body is not valid JSON.')

    def _check_host(self):
        """DNS rebinding: a hostile site resolving its own name to 127.0.0.1 sends a matching
        Host and Origin, which an Origin==Host check accepts. Only our own names are served."""
        port = self.server.server_port
        allowed = {'127.0.0.1:%d' % port, 'localhost:%d' % port}
        if self.headers.get('Host', '').lower() not in allowed:
            self.close_connection = True
            raise StoreError(403, 'HOST_FORBIDDEN', 'Unrecognised Host header.')

    def _check_origin(self):
        """A browser on another origin may not drive writes (CSRF)."""
        origin = self.headers.get('Origin')
        if origin is None:
            return
        if origin != 'http://' + self.headers.get('Host', ''):
            raise StoreError(403, 'CROSS_ORIGIN_FORBIDDEN', 'Cross-origin requests are not accepted.')

    def _dispatch(self, handler):
        self._body_consumed = False
        self._t0 = time.perf_counter()
        self._event = None
        try:
            self._check_host()
            handler()
        except StoreError as err:
            self._event = {'event': 'rejected', 'code': err.code}
            if not self._body_consumed and self.headers.get('Content-Length', '0') not in ('', '0'):
                # Rejected before reading the body: on a kept-alive connection the unread
                # bytes would be parsed as the start of the next request (desync). Close it.
                self.close_connection = True
            self.json_response(err.status, err.body())
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception:
            # Full detail goes to the server log only; the client gets no stack trace.
            traceback.print_exc(file=sys.stderr)
            self._event = {'event': 'internal_error'}
            self.close_connection = True
            self.error_response(500, 'INTERNAL_ERROR', 'Internal error. The request was not completed.')

    # -- methods ---------------------------------------------------------------

    def do_GET(self):
        self._dispatch(self._get)

    def do_HEAD(self):
        self._dispatch(self._get)

    def do_POST(self):
        self._dispatch(self._post)

    def _not_allowed(self):
        path = urlsplit(self.path).path
        if path == '/reservations':
            allow = 'GET, HEAD, POST'
        elif CANCEL_PATH.match(path):
            allow = 'POST'
        else:
            allow = 'GET, HEAD'
        self.close_connection = True  # any body sent with the request is left unread
        self.error_response(405, 'METHOD_NOT_ALLOWED', 'Method %s is not allowed here.' % self.command,
                            {'Allow': allow})

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_TRACE = do_CONNECT = _not_allowed

    def _get(self):
        url = urlsplit(self.path)
        path = url.path
        if path in STATIC:
            return self._static(*STATIC[path])
        if path == '/health':
            return self.json_response(200, {'status': 'ok'})
        if path == '/sessions':
            return self.json_response(200, {'sessions': self.store.sessions()})
        if path == '/reservations':
            query = parse_qs(url.query)
            session_id = query.get('sessionId', [None])[0]
            status = query.get('status', [None])[0]
            return self.json_response(200, {'reservations': self.store.list(session_id, status)})
        match = RESERVATION_PATH.match(path)
        if match:
            return self.json_response(200, self.store.get(match.group(1)))
        if CANCEL_PATH.match(path):
            return self._not_allowed()
        self.error_response(404, 'NOT_FOUND', 'No such endpoint.')

    def _post(self):
        path = urlsplit(self.path).path
        if path == '/reservations':
            self._check_origin()
            body = self._read_json()
            created, record = self.store.reserve(body)
            self._event = {'event': 'reservation.created' if created else 'reservation.replayed',
                           'reservationId': record['id'], 'sessionId': record['sessionId'],
                           'reservationStatus': record['status']}
            return self.json_response(201 if created else 200, record,
                                      {'Location': '/reservations/' + record['id']} if created else None)
        match = CANCEL_PATH.match(path)
        if match:
            self._check_origin()
            body = self._read_json()
            if body != {}:
                raise StoreError(400, 'INVALID_BODY', 'Cancel takes an empty JSON object: {}.')
            record = self.store.cancel(match.group(1))
            self._event = {'event': 'reservation.cancelled', 'reservationId': record['id'],
                           'sessionId': record['sessionId'], 'cancelledAt': record['cancelledAt']}
            return self.json_response(200, record)
        if path in STATIC or path in ('/health', '/sessions') or RESERVATION_PATH.match(path):
            return self._not_allowed()
        self.close_connection = True
        self.error_response(404, 'NOT_FOUND', 'No such endpoint.')

    def _static(self, name, content_type):
        payload = (BASE / 'static' / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-cache')
        self._security_headers(PAGE_CSP)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--reset', action='store_true', help='Reset only the marked fixture DATA_DIR')
    args = parser.parse_args()
    store = Store(DATA)
    if args.reset:
        store.reset(BASE / 'sessions.json')
        print('Reset fixture:', store.db_path, flush=True)
        return
    if not store.is_initialised():
        parser.error('No initialised fixture at %s. Run with --reset first, using the same DATA_DIR.'
                     % store.db_path)
    Handler.store = store
    global LOG_PATH
    LOG_PATH = store.data_dir / 'server.log'
    server = LoopbackHTTPServer(('127.0.0.1', int(os.environ.get('PORT', '8765'))), Handler)
    print('Session Seat Desk on http://127.0.0.1:%s  state=%s  pid=%s'
          % (server.server_port, store.db_path, os.getpid()), flush=True)
    sessions = {s['id']: s['activeCount'] for s in store.sessions()}
    log_event({'level': 'info', 'event': 'server.start', 'pid': os.getpid(), 'port': server.server_port,
               'db': str(store.db_path), 'activeBySession': sessions})
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
