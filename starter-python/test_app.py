"""Behavioral tests for Session Seat Desk. Each test starts the real app process
against a fresh temporary DATA_DIR and talks to it over HTTP; the store is also
inspected directly with sqlite3. Any failure makes the process exit non-zero."""
from contextlib import closing
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

APP = Path(__file__).resolve().parent / 'app.py'


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class AppCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = self._tmp.name
        self.port = free_port()
        self.env = dict(os.environ, PORT=str(self.port), DATA_DIR=self.data_dir)
        self.proc = None
        self.reset()
        self.start()

    @staticmethod
    def app_command(*args):
        """argv for the app; under coverage_report.py (COVERAGE_DIR set) it runs via covtrace.py."""
        if os.environ.get('COVERAGE_DIR'):
            return [sys.executable, str(APP.with_name('covtrace.py')), str(APP), *args]
        return [sys.executable, str(APP), *args]

    def reset(self):
        subprocess.run(self.app_command('--reset'), env=self.env,
                       check=True, capture_output=True, timeout=30)

    def start(self):
        self.proc = subprocess.Popen(self.app_command(), env=self.env,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.stop)
        deadline = time.time() + 10
        while time.time() < deadline:
            if self.proc.poll() is not None:
                self.fail('app exited at startup: ' + self.proc.stderr.read().decode())
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.05)
        self.fail('app did not start listening')

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        for pipe in (self.proc.stdout, self.proc.stderr):
            pipe.close()

    def request(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path),
                                     data=data, method=method,
                                     headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def reserve(self, session='CT-101', alias='Ada', key='K1'):
        return self.request('POST', '/reservations',
                            {'sessionId': session, 'attendeeAlias': alias, 'requestKey': key})

    def sessions(self):
        status, body = self.request('GET', '/sessions')
        self.assertEqual(status, 200)
        return {s['id']: s for s in body['sessions']}

    def db_counts(self):
        with closing(sqlite3.connect(os.path.join(self.data_dir, 'seats.db'))) as db:
            total = db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]
            active = db.execute("SELECT COUNT(*) FROM reservations WHERE status='active'").fetchone()[0]
        return total, active

    def assert_error(self, result):
        status, body = result
        self.assertTrue(400 <= status < 500, 'expected 4xx, got %s %s' % (status, body))
        err = body.get('error')
        self.assertTrue(err, 'missing error in %r' % body)
        if isinstance(err, dict):
            self.assertTrue(err.get('message'))


class SessionReadback(AppCase):  # AC-02
    def test_fresh_reset_state(self):
        s = self.sessions()
        self.assertEqual(set(s), {'CT-101', 'CT-102'})
        self.assertEqual((s['CT-101']['title'], s['CT-101']['capacity'],
                          s['CT-101']['activeCount'], s['CT-101']['remainingSeats']),
                         ('Catching Ghost Databases', 2, 0, 2))
        self.assertEqual((s['CT-102']['title'], s['CT-102']['capacity'],
                          s['CT-102']['activeCount'], s['CT-102']['remainingSeats']),
                         ('Tests That Can Fail', 3, 0, 3))
        for rec in s.values():
            for field in ('capacity', 'activeCount', 'remainingSeats'):
                self.assertIs(type(rec[field]), int)

    def test_ui_served(self):
        with urllib.request.urlopen('http://127.0.0.1:%d/' % self.port, timeout=10) as resp:
            html = resp.read().decode()
        self.assertIn('/sessions', html)
        self.assertNotIn('Scaffold only', html)


class Reservation(AppCase):  # AC-03
    def test_reserve_and_read_back(self):
        status, rec = self.reserve()
        self.assertEqual(status, 201)
        self.assertTrue(rec['id'])
        self.assertEqual((rec['sessionId'], rec['attendeeAlias'], rec['requestKey'], rec['status']),
                         ('CT-101', 'Ada', 'K1', 'active'))
        status, again = self.request('GET', '/reservations/' + rec['id'])
        self.assertEqual((status, again), (200, rec))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 1)
        self.assertEqual(self.sessions()['CT-102']['remainingSeats'], 3)
        self.assertEqual(self.db_counts(), (1, 1))

    def test_unknown_reservation(self):
        self.assert_error(self.request('GET', '/reservations/nope'))


class Capacity(AppCase):  # AC-04
    def test_third_request_rejected(self):
        self.assertEqual(self.reserve(key='K1', alias='Ada')[0], 201)
        self.assertEqual(self.reserve(key='K2', alias='Grace')[0], 201)
        self.assert_error(self.reserve(key='K3', alias='Linus'))
        self.assertEqual(self.db_counts(), (2, 2))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 0)

    def test_concurrent_race_for_last_seat(self):
        self.assertEqual(self.reserve(key='seed', alias='Ada')[0], 201)
        for batch in range(10):
            if batch:  # new fresh one-seat state per batch
                self.stop()
                self.reset()
                self.start()
                self.assertEqual(self.reserve(key='seed', alias='Ada')[0], 201)
            results = []
            lock = threading.Lock()
            barrier = threading.Barrier(10)

            def attempt(n):
                barrier.wait()
                out = self.reserve(key='race-%d-%d' % (batch, n), alias='Racer%d' % n)
                with lock:
                    results.append(out)

            threads = [threading.Thread(target=attempt, args=(n,)) for n in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            ok = [r for r in results if 200 <= r[0] < 300]
            self.assertEqual(len(ok), 1, 'batch %d: %r' % (batch, results))
            for status, body in results:
                if not 200 <= status < 300:
                    self.assertTrue(400 <= status < 500 and body.get('error'), (status, body))
            self.assertEqual(self.sessions()['CT-101']['activeCount'], 2)
            self.assertEqual(self.db_counts(), (2, 2))


class Idempotency(AppCase):  # AC-05
    def test_replay_returns_original(self):
        _, first = self.reserve(alias='Ada', key='K1')
        status, replay = self.reserve(alias='  Ada  ', key='K1')
        self.assertIn(status, (200, 201))
        self.assertEqual(replay, first)
        self.assertEqual(self.sessions()['CT-101']['activeCount'], 1)
        self.assertEqual(self.db_counts(), (1, 1))

    def test_replay_on_full_session_still_returns_original(self):
        _, first = self.reserve(alias='Ada', key='K1')
        self.reserve(alias='Grace', key='K2')
        status, replay = self.reserve(alias='Ada', key='K1')
        self.assertIn(status, (200, 201))
        self.assertEqual(replay['id'], first['id'])

    def test_key_conflicts(self):
        self.reserve(alias='Ada', key='K1')
        self.assert_error(self.reserve(alias='Grace', key='K1'))
        self.assert_error(self.reserve(session='CT-102', alias='Ada', key='K1'))
        self.assert_error(self.reserve(alias='ada', key='K1'))  # case-sensitive
        self.assertEqual(self.db_counts(), (1, 1))
        self.assertEqual(self.sessions()['CT-102']['activeCount'], 0)


class Cancellation(AppCase):  # AC-06
    def test_cancel_release_and_replay(self):
        _, rec = self.reserve()
        status, cancelled = self.request('POST', '/reservations/%s/cancel' % rec['id'], {})
        self.assertEqual(status, 200)
        self.assertEqual((cancelled['id'], cancelled['status']), (rec['id'], 'cancelled'))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 2)
        status, again = self.request('POST', '/reservations/%s/cancel' % rec['id'], {})
        self.assertEqual((status, again['status']), (200, 'cancelled'))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 2)
        status, replay = self.reserve()
        self.assertIn(status, (200, 201))
        self.assertEqual((replay['id'], replay['status']), (rec['id'], 'cancelled'))
        self.assertEqual(self.sessions()['CT-101']['activeCount'], 0)
        self.assertEqual(self.request('GET', '/reservations/' + rec['id'])[1]['status'], 'cancelled')
        status, fresh = self.reserve(key='K2')
        self.assertEqual(status, 201)
        self.assertNotEqual(fresh['id'], rec['id'])


class Durability(AppCase):  # AC-07
    def test_restart_preserves_state(self):
        _, active = self.reserve(alias='Ada', key='K1')
        _, other = self.reserve(alias='Grace', key='K2')
        self.request('POST', '/reservations/%s/cancel' % other['id'], {})
        before = self.sessions()
        self.stop()
        self.start()  # no reset
        self.assertEqual(self.sessions(), before)
        self.assertEqual(self.request('GET', '/reservations/' + active['id'])[1]['status'], 'active')
        self.assertEqual(self.request('GET', '/reservations/' + other['id'])[1]['status'], 'cancelled')
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 1)


class InvalidInput(AppCase):  # AC-08
    def test_rejections_change_nothing_and_server_survives(self):
        cases = [
            self.request('POST', '/reservations', {'sessionId': 'NOPE', 'attendeeAlias': 'Ada', 'requestKey': 'K'}),
            self.request('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': '', 'requestKey': 'K'}),
            self.request('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': '   ', 'requestKey': 'K'}),
            self.request('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': 'Ada'}),
            self.request('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': ''}),
            self.request('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 7}),
            self.request('POST', '/reservations', {'sessionId': 'CT-101', 'attendeeAlias': 5, 'requestKey': 'K'}),
            self.request('POST', '/reservations', raw=b'{not json'),
            self.request('POST', '/reservations', raw=b'[1,2]'),
            self.request('POST', '/reservations', raw=b'\xff\xfe'),
            self.request('POST', '/reservations/unknown/cancel', {}),
            self.request('POST', '/reservations/unknown/cancel', raw=b'{bad'),
            self.request('GET', '/nowhere'),
        ]
        for result in cases:
            self.assert_error(result)
        self.assertEqual(self.db_counts(), (0, 0))
        s = self.sessions()
        self.assertEqual((s['CT-101']['remainingSeats'], s['CT-102']['remainingSeats']), (2, 3))
        self.assertIsNone(self.proc.poll())
        self.assertEqual(self.reserve()[0], 201)


class HttpEdgeCases(AppCase):
    def test_health_is_liveness_only(self):
        self.assertEqual(self.request('GET', '/health'), (200, {'status': 'ok'}))

    def test_wrong_method_is_405_and_changes_nothing(self):
        for method, path in (('PUT', '/reservations'), ('DELETE', '/reservations/x'),
                             ('PATCH', '/sessions'), ('GET', '/reservations/x/cancel'),
                             ('POST', '/sessions')):
            status, body = self.request(method, path, {} if method != 'GET' else None)
            self.assertEqual(status, 405, (method, path))
            self.assert_error((status, body))
        self.assertEqual(self.db_counts(), (0, 0))

    def test_missing_session_id_rejected(self):
        self.assert_error(self.request('POST', '/reservations', {'attendeeAlias': 'Ada', 'requestKey': 'K'}))
        self.assertEqual(self.db_counts(), (0, 0))

    def test_empty_create_body_rejected_but_empty_cancel_body_allowed(self):
        self.assert_error(self.request('POST', '/reservations', raw=b''))
        _, rec = self.reserve()
        status, cancelled = self.request('POST', '/reservations/%s/cancel' % rec['id'], raw=b'')
        self.assertEqual((status, cancelled['status']), (200, 'cancelled'))

    def test_oversized_body_rejected(self):
        status, body = self.request('POST', '/reservations', raw=b'{"x":"' + b'a' * 70000 + b'"}')
        self.assertEqual(status, 413)
        self.assert_error((status, body))
        self.assertEqual(self.db_counts(), (0, 0))

    def test_bad_content_length_rejected_and_server_survives(self):
        with socket.create_connection(('127.0.0.1', self.port), timeout=10) as conn:
            conn.sendall(b'POST /reservations HTTP/1.1\r\nHost: x\r\nContent-Length: abc\r\n\r\n')
            reply = conn.recv(4096)
        self.assertTrue(reply.startswith(b'HTTP/1.0 400') or reply.startswith(b'HTTP/1.1 400'), reply[:40])
        self.assertEqual(self.reserve()[0], 201)

    def test_locked_store_gives_503_not_success_and_recovers(self):
        blocker = sqlite3.connect(os.path.join(self.data_dir, 'seats.db'), isolation_level=None)
        blocker.execute('BEGIN EXCLUSIVE')
        try:
            status, body = self.reserve()
        finally:
            blocker.execute('ROLLBACK')
            blocker.close()
        self.assertEqual(status, 503)
        self.assertTrue(body['error']['message'])
        self.assertEqual(self.db_counts(), (0, 0))
        self.assertEqual(self.reserve()[0], 201)


class ResetSafety(unittest.TestCase):
    def test_reset_refuses_unmarked_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            sqlite3.connect(os.path.join(tmp, 'seats.db')).close()  # a db we do not own
            result = subprocess.run(AppCase.app_command('--reset'), capture_output=True, timeout=30,
                                    env=dict(os.environ, DATA_DIR=tmp))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'unmarked', result.stderr)


class StartupSafety(unittest.TestCase):
    def test_refuses_to_serve_without_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(AppCase.app_command(), capture_output=True, timeout=30,
                                    env=dict(os.environ, DATA_DIR=tmp, PORT=str(free_port())))
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
