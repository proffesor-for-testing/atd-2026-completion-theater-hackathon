"""Hardening tests from the internal review + chaos audit (beyond AC-08's five cases).

Each case must reject with a 4xx JSON error (never 5xx/HTML), change no state,
and leave the server available.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

APP_DIR = Path(__file__).resolve().parent


class HardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0)); cls.port = s.getsockname()[1]
        env = {**os.environ, 'DATA_DIR': cls.tmp.name + '/state', 'PORT': str(cls.port)}
        subprocess.run([sys.executable, 'app.py', '--reset'], cwd=APP_DIR, env=env, check=True, capture_output=True)
        cls.proc = subprocess.Popen([sys.executable, 'app.py'], cwd=APP_DIR, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{cls.port}/sessions', timeout=1); break
            except OSError:
                time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate(); cls.proc.wait(timeout=5); cls.tmp.cleanup()

    def raw(self, method, path, body=b''):
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=body or None, method=method,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.headers.get('Content-Type', ''), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get('Content-Type', ''), e.read()

    def sessions(self):
        return json.loads(self.raw('GET', '/sessions')[2])

    def assert_rejected(self, method, path, body=b''):
        before = self.sessions()
        status, ctype, payload = self.raw(method, path, body)
        self.assertTrue(400 <= status < 500, (status, payload[:200]))
        if method != 'HEAD':
            self.assertIn('application/json', ctype)
            self.assertTrue(json.loads(payload)['error'])
        self.assertEqual(self.sessions(), before)

    def reserve_body(self, alias='Ada', key='H1', session='CT-102'):
        return json.dumps({'sessionId': session, 'attendeeAlias': alias, 'requestKey': key}).encode()

    def test_invisible_only_aliases_rejected(self):
        for i, alias in enumerate(['​', '﻿', '\t​\n﻿', '⁠ ']):
            with self.subTest(alias=repr(alias)):
                self.assert_rejected('POST', '/reservations', self.reserve_body(alias, f'INV{i}'))

    def test_control_character_in_alias_rejected(self):
        self.assert_rejected('POST', '/reservations', self.reserve_body('Ad\na', 'CC1'))

    def test_whitespace_only_request_key_rejected(self):
        self.assert_rejected('POST', '/reservations', self.reserve_body('Ada', '   '))

    def test_lone_surrogate_rejected_not_500(self):
        body = b'{"sessionId":"CT-102","attendeeAlias":"\\ud800","requestKey":"S1"}'
        self.assert_rejected('POST', '/reservations', body)

    def test_deeply_nested_json_rejected_not_500(self):
        self.assert_rejected('POST', '/reservations', b'[' * 30000)

    def test_non_object_bodies_rejected(self):
        for body in (b'null', b'"x"', b'42', b'[]'):
            with self.subTest(body=body):
                self.assert_rejected('POST', '/reservations', body)

    def test_unsupported_methods_are_json_4xx(self):
        for method in ('PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'):
            with self.subTest(method=method):
                self.assert_rejected(method, '/sessions')

    def test_bad_request_line_returns_valid_json(self):
        with socket.create_connection(('127.0.0.1', self.port), timeout=5) as s:
            s.sendall(b'PA"TCH /sessions HTTP/1.1\r\nHost: x\r\n\r\n')
            data = b''
            while chunk := s.recv(4096):
                data += chunk
        head, _, body = data.partition(b'\r\n\r\n')
        status = int(head.split(b'\r\n')[0].split()[1])
        self.assertTrue(400 <= status < 500, head)
        self.assertTrue(json.loads(body)['error'])

    def test_unknown_path_is_json_404(self):
        self.assert_rejected('GET', '/nope')


if __name__ == '__main__':
    unittest.main(verbosity=2)
