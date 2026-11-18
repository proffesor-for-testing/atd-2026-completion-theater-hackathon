"""Behavioral tests for Session Seat Desk.

Each test starts the real app.py as a child process on a free loopback port
with its own temporary DATA_DIR, after an explicit --reset. Tests talk HTTP
only, plus independent SQLite readback where noted.
"""
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class AppProcess:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.port = free_port()
        self.proc = None

    def env(self):
        env = dict(os.environ)
        env['DATA_DIR'] = self.data_dir
        env['PORT'] = str(self.port)
        return env

    def reset(self):
        subprocess.run([sys.executable, 'app.py', '--reset'], cwd=HERE, env=self.env(),
                       check=True, capture_output=True)

    def start(self):
        # Server output goes to a file, not an unread pipe, so it can never block the server.
        self.log = open(os.path.join(self.data_dir, 'server.log'), 'ab')
        self.proc = subprocess.Popen([sys.executable, 'app.py'], cwd=HERE, env=self.env(),
                                     stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                urllib.request.urlopen(self.url('/health'), timeout=1).read()
                return
            except OSError:
                if self.proc.poll() is not None:
                    raise RuntimeError('app exited with %s, see %s' % (self.proc.returncode, self.log.name))
                time.sleep(0.05)
        raise RuntimeError('app did not start')

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        if self.proc:
            self.log.close()

    def url(self, path):
        return 'http://127.0.0.1:%d%s' % (self.port, path)

    def request(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        req = urllib.request.Request(self.url(path), data=data, method=method,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())


class SeatDeskTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = AppProcess(self.tmp.name)
        self.app.reset()
        self.app.start()

    def tearDown(self):
        self.app.stop()
        self.tmp.cleanup()

    def sessions(self):
        status, body = self.app.request('GET', '/sessions')
        self.assertEqual(status, 200)
        return {s['id']: s for s in body['sessions']}

    def reserve(self, session='CT-101', alias='Ada', key='K1'):
        return self.app.request('POST', '/reservations',
                                {'sessionId': session, 'attendeeAlias': alias, 'requestKey': key})

    def assertCounts(self, ct101, ct102=(0, 3)):
        s = self.sessions()
        self.assertEqual((s['CT-101']['activeCount'], s['CT-101']['remainingSeats']), ct101)
        self.assertEqual((s['CT-102']['activeCount'], s['CT-102']['remainingSeats']), ct102)

    def db_rows(self):
        with sqlite3.connect(os.path.join(self.tmp.name, 'seats.db')) as c:
            return c.execute('SELECT id, session_id, attendee_alias, request_key, status '
                             'FROM reservations ORDER BY created_seq').fetchall()

    def assertError(self, status, body, expected_status):
        self.assertEqual(status, expected_status, body)
        self.assertIn('error', body)
        self.assertTrue(body['error'])


class SessionsTests(SeatDeskTestCase):
    def test_ac02_seeded_sessions_on_fresh_reset(self):
        s = self.sessions()
        self.assertEqual(sorted(s), ['CT-101', 'CT-102'])
        self.assertEqual(s['CT-101'], {'id': 'CT-101', 'title': 'Catching Ghost Databases',
                                       'capacity': 2, 'activeCount': 0, 'remainingSeats': 2})
        self.assertEqual(s['CT-102'], {'id': 'CT-102', 'title': 'Tests That Can Fail',
                                       'capacity': 3, 'activeCount': 0, 'remainingSeats': 3})

    def test_ac01_ui_served(self):
        with urllib.request.urlopen(self.app.url('/'), timeout=5) as res:
            html = res.read().decode()
        self.assertEqual(res.status, 200)
        self.assertIn('<label for="alias">', html)
        self.assertIn('/sessions', html)


class ReservationTests(SeatDeskTestCase):
    def test_ac03_reserve_and_read_back(self):
        status, r = self.reserve()
        self.assertIn(status, (200, 201))
        self.assertEqual(r['status'], 'active')
        self.assertEqual((r['sessionId'], r['attendeeAlias'], r['requestKey']), ('CT-101', 'Ada', 'K1'))
        status, again = self.app.request('GET', '/reservations/' + r['id'])
        self.assertEqual(status, 200)
        self.assertEqual(again, r)
        self.assertCounts((1, 1))
        self.assertEqual(self.db_rows(), [(r['id'], 'CT-101', 'Ada', 'K1', 'active')])

    def test_unknown_reservation_is_404(self):
        status, body = self.app.request('GET', '/reservations/nope')
        self.assertError(status, body, 404)

    def test_ac04a_capacity_sequential(self):
        self.assertEqual(self.reserve(key='K1')[0], 201)
        self.assertEqual(self.reserve(alias='Bob', key='K2')[0], 201)
        status, body = self.reserve(alias='Cy', key='K3')
        self.assertError(status, body, 409)
        self.assertEqual(body['error']['code'], 'CAPACITY_FULL')
        self.assertCounts((2, 0))
        self.assertEqual(len(self.db_rows()), 2)

    def test_ac04b_capacity_concurrent(self):
        self.assertEqual(self.reserve(key='K0')[0], 201)
        results = []
        lock = threading.Lock()
        barrier = threading.Barrier(10)

        def attempt(i):
            barrier.wait()
            res = self.reserve(alias='Racer%d' % i, key='R%d' % i)
            with lock:
                results.append(res[0])

        threads = [threading.Thread(target=attempt, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(results), [201] + [409] * 9)
        self.assertCounts((2, 0))
        self.assertEqual(len(self.db_rows()), 2)

    def test_ac05_idempotent_replay_and_conflicts(self):
        _, first = self.reserve()
        status, replay = self.reserve(alias='  Ada  ')
        self.assertEqual(status, 200)
        self.assertEqual(replay['id'], first['id'])
        self.assertEqual(replay['status'], 'active')
        self.assertCounts((1, 1))
        status, body = self.reserve(alias='Bob')
        self.assertError(status, body, 409)
        status, body = self.reserve(session='CT-102')
        self.assertError(status, body, 409)
        status, body = self.reserve(alias='ada')  # case-sensitive
        self.assertError(status, body, 409)
        self.assertCounts((1, 1))
        self.assertEqual(len(self.db_rows()), 1)

    def test_ac06_cancel_repeat_and_replay(self):
        _, r = self.reserve()
        self.assertCounts((1, 1))
        status, c1 = self.app.request('POST', '/reservations/%s/cancel' % r['id'], {})
        self.assertEqual(status, 200)
        self.assertEqual((c1['id'], c1['status']), (r['id'], 'cancelled'))
        self.assertCounts((0, 2))
        status, c2 = self.app.request('POST', '/reservations/%s/cancel' % r['id'], {})
        self.assertEqual(status, 200)
        self.assertEqual(c2['status'], 'cancelled')
        self.assertCounts((0, 2))
        status, replay = self.reserve()
        self.assertEqual(status, 200)
        self.assertEqual((replay['id'], replay['status']), (r['id'], 'cancelled'))
        self.assertCounts((0, 2))
        self.assertEqual(len(self.db_rows()), 1)

    def test_ac07_state_survives_restart(self):
        _, k1 = self.reserve(key='K1')
        _, k2 = self.reserve(alias='Bob', key='K2')
        self.app.request('POST', '/reservations/%s/cancel' % k1['id'], {})
        before = self.sessions()
        old_pid = self.app.proc.pid
        self.app.stop()
        self.app.start()  # no reset
        self.assertNotEqual(self.app.proc.pid, old_pid)
        self.assertEqual(self.sessions(), before)
        self.assertCounts((1, 1))
        self.assertEqual(self.app.request('GET', '/reservations/' + k1['id'])[1]['status'], 'cancelled')
        self.assertEqual(self.app.request('GET', '/reservations/' + k2['id'])[1]['status'], 'active')

    def test_ac08_invalid_input_rejected_without_state_change(self):
        self.reserve()
        cases = [
            ('POST', '/reservations', {'sessionId': 'CT-999', 'attendeeAlias': 'Ada', 'requestKey': 'X1'}, None, 404),
            ('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': '   ', 'requestKey': 'X2'}, None, 400),
            ('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': 'Ada'}, None, 400),
            ('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': ''}, None, 400),
            ('POST', '/reservations', None, b'{"sessionId": "CT-101",', 400),
            ('POST', '/reservations/does-not-exist/cancel', {}, None, 404),
        ]
        for method, path, body, raw, expected in cases:
            with self.subTest(path=path, body=body, raw=raw):
                status, resp = self.app.request(method, path, body, raw)
                self.assertError(status, resp, expected)
                self.assertCounts((1, 1))
        self.assertEqual(len(self.db_rows()), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
