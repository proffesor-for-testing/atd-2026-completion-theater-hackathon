"""Independent store verification (`python3 app.py --check`).

Question this answers: does the data on disk agree with what the API reported,
and would we notice if it didn't? The checker reads seats.db directly, never via
HTTP, and replays the hash-chained audit log against the reservations table.
Each tamper test is a negative control for the checker itself.
"""
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

APP_DIR = Path(__file__).resolve().parent


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class StoreCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'state'
        self.port = free_port()
        self.env = {**os.environ, 'DATA_DIR': str(self.data), 'PORT': str(self.port)}
        subprocess.run([sys.executable, 'app.py', '--reset'], cwd=APP_DIR, env=self.env, check=True, capture_output=True)
        self.proc = subprocess.Popen([sys.executable, 'app.py'], cwd=APP_DIR, env=self.env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                if self.call('GET', '/sessions')[0] == 200:
                    break
            except OSError:
                time.sleep(0.05)
        # one active and one cancelled reservation
        self.active = self.call('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1'})[1]
        bob = self.call('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': 'Bob', 'requestKey': 'K2'})[1]
        self.cancelled = self.call('POST', f'/reservations/{bob["id"]}/cancel', {})[1]
        self.proc.terminate()
        self.proc.wait(timeout=5)

    def tearDown(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)
        self.tmp.cleanup()

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=data, method=method,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def check(self):
        r = subprocess.run([sys.executable, 'app.py', '--check'], cwd=APP_DIR, env=self.env, capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout)

    def sql(self, statement, *args):
        with sqlite3.connect(self.data / 'seats.db') as c:
            c.execute(statement, args)

    def test_clean_store_passes_and_matches_api(self):
        code, report = self.check()
        self.assertEqual(code, 0, report)
        self.assertEqual(report['reservations'], 2)
        self.assertEqual(report['auditEntries'], 3)  # reserve, reserve, cancel
        with sqlite3.connect(self.data / 'seats.db') as c:
            rows = dict(c.execute('SELECT id, status FROM reservations'))
        self.assertEqual(rows, {self.active['id']: 'active', self.cancelled['id']: 'cancelled'})

    def test_detects_silent_reactivation(self):
        self.sql("UPDATE reservations SET status='active' WHERE id=?", self.cancelled['id'])
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any('disagrees with audit log' in p for p in report['problems']), report)

    def test_detects_ghost_row_inserted_outside_api(self):
        self.sql("INSERT INTO reservations VALUES ('ghost','CT-102','Eve','K9','active','x',NULL)")
        code, report = self.check()
        self.assertEqual(code, 1, report)

    def test_detects_overbooking(self):
        self.sql("UPDATE reservations SET status='active'")
        self.sql("INSERT INTO reservations VALUES ('x3','CT-101','Cy','K3','active','x',NULL)")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any('exceeds capacity' in p for p in report['problems']), report)

    def test_detects_record_edited_in_place(self):
        self.sql("UPDATE reservations SET attendee_alias='Mallory' WHERE id=?", self.active['id'])
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any('disagrees with audit log' in p for p in report['problems']), report)

    def test_detects_edited_audit_history(self):
        self.sql("UPDATE audit_log SET action='reserve' WHERE action='cancel'")
        code, report = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any('audit chain broken' in p for p in report['problems']), report)


if __name__ == '__main__':
    unittest.main(verbosity=2)
