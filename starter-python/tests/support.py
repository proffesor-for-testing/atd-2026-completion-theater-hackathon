"""Black-box harness: runs the real app.py as a subprocess on a free port with a fresh DATA_DIR."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class _TableRows(HTMLParser):
    def __init__(self, table_id):
        super().__init__()
        self.table_id, self.depth, self.rows, self.cell = table_id, 0, [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'table' and dict(attrs).get('id') == self.table_id:
            self.depth = 1
        elif self.depth and tag == 'tr':
            self.rows.append([])
        elif self.depth and tag in ('td', 'th'):
            self.cell = ''

    def handle_endtag(self, tag):
        if self.depth and tag in ('td', 'th') and self.cell is not None:
            self.rows[-1].append(' '.join(self.cell.split()))
            self.cell = None
        elif tag == 'table':
            self.depth = 0

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data


def form_request_key(html):
    """The hidden requestKey the reserve form will submit (fresh per page load)."""
    import re
    match = re.search(r'name="requestKey" value="([^"]+)"', html)
    assert match, 'reserve form has no hidden requestKey'
    return match.group(1)


def alert_text(html):
    """Visible text of the role=alert / role=status message region, or ''."""
    import re
    match = re.search(r'<p id="message" role="(?:alert|status)"[^>]*>(.*?)</p>', html, re.S)
    return ' '.join(re.sub(r'<[^>]+>', ' ', match.group(1)).split()) if match else ''


def table_rows(html, table_id):
    """Visible cell text of each <tr> in <table id=table_id>, e.g. [['CT-101', 'Catching…', '2', '0', '2']]."""
    parser = _TableRows(table_id)
    parser.feed(html)
    return [row for row in parser.rows if row]


class RunningApp:
    """Use as a context manager. reset() once, then start()/stop() as often as needed (AC-07)."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.port = _free_port()
        self.env = {**os.environ, 'DATA_DIR': str(Path(self._tmp.name) / 'state'),
                    'PORT': str(self.port), 'HOST': '127.0.0.1'}
        self.proc = None

    def reset(self):
        subprocess.run([sys.executable, 'app.py', '--reset'], cwd=APP_DIR, env=self.env,
                       check=True, capture_output=True)

    def start(self):
        self.proc = subprocess.Popen([sys.executable, 'app.py'], cwd=APP_DIR, env=self.env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                socket.create_connection(('127.0.0.1', self.port), timeout=0.2).close()
                return
            except OSError:
                time.sleep(0.05)
        raise RuntimeError('app did not start on port %d' % self.port)

    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=10)
            self.proc = None

    def stored_reservation_count(self):
        """Independent store check: rows in SQLite, including cancelled ones the API counts can't show."""
        import sqlite3
        db = Path(self.env['DATA_DIR']) / 'seats.db'
        connection = sqlite3.connect('file:%s?mode=ro' % db.as_posix(), uri=True)
        try:
            return connection.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]
        finally:
            connection.close()

    def post_form(self, path, fields):
        """Submit an HTML form like a browser (urlencoded, follows the 303). Returns (status, html)."""
        from urllib.parse import urlencode
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path),
                                     data=urlencode(fields).encode(), method='POST',
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, res.read().decode('utf-8')
        except urllib.error.HTTPError as err:
            return err.code, err.read().decode('utf-8')

    def page(self):
        status, html = self.request('GET', '/')
        assert status == 200, status
        return html

    def request(self, method, path, body=None, raw=None):
        """Returns (status, parsed JSON or text). raw= sends bytes as-is (e.g. malformed JSON)."""
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), data=data,
                                     method=method, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                status, payload, ctype = res.status, res.read(), res.headers.get('Content-Type', '')
        except urllib.error.HTTPError as err:
            status, payload, ctype = err.code, err.read(), err.headers.get('Content-Type', '')
        text = payload.decode('utf-8')
        return status, (json.loads(text) if 'json' in ctype else text)

    def __enter__(self):
        self.reset()
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        self._tmp.cleanup()
