"""Behavioral tests for Session Seat Desk (PRD AC-02..AC-08 over real HTTP).

Each test class starts the real app.py as a subprocess against a fresh,
disposable DATA_DIR on an ephemeral loopback port. Run from this directory:

    python3 -m unittest -v test_app
"""
import concurrent.futures
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
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


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
        env = dict(os.environ, DATA_DIR=str(self.data_dir), PORT=str(self.port))
        return env

    def reset(self):
        subprocess.run([sys.executable, 'app.py', '--reset'], cwd=APP_DIR, env=self.env(),
                       check=True, capture_output=True, timeout=30)

    def start(self):
        self.proc = subprocess.Popen([sys.executable, 'app.py'], cwd=APP_DIR, env=self.env(),
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 15
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError('app exited early with %s' % self.proc.returncode)
            try:
                if self.request('GET', '/health')[0] == 200:
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError('app did not start')

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()

    def request(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), data=data,
                                     method=method, headers={'Content-Type': 'application/json'})
        try:
            with NO_PROXY.open(req, timeout=15) as resp:
                text = resp.read().decode()
                return resp.status, (json.loads(text) if 'json' in resp.headers.get('Content-Type', '') else text)
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode())


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = AppProcess(Path(self.tmp.name) / 'state')
        self.app.reset()
        self.app.start()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.app.stop)

    def sessions(self):
        status, body = self.app.request('GET', '/sessions')
        self.assertEqual(status, 200)
        return {s['id']: s for s in body['sessions']}

    def reserve(self, session='CT-101', alias='Ada', key='K1'):
        return self.app.request('POST', '/reservations',
                                {'sessionId': session, 'attendeeAlias': alias, 'requestKey': key})

    def assert_error(self, status, body, expected_status):
        self.assertEqual(status, expected_status, body)
        self.assertIn('error', body)
        self.assertTrue(body['error']['message'])

    def db_rows(self):
        with sqlite3.connect(self.app.data_dir / 'seats.db') as c:
            return c.execute('SELECT id, session_id, attendee_alias, request_key, status'
                             ' FROM reservations ORDER BY rowid').fetchall()


class SessionReadbackTests(AppTestCase):  # AC-01 (API part), AC-02
    def test_fresh_reset_returns_two_seeded_sessions_with_zero_counts(self):
        s = self.sessions()
        self.assertEqual(set(s), {'CT-101', 'CT-102'})
        self.assertEqual((s['CT-101']['capacity'], s['CT-101']['activeCount'], s['CT-101']['remainingSeats']), (2, 0, 2))
        self.assertEqual((s['CT-102']['capacity'], s['CT-102']['activeCount'], s['CT-102']['remainingSeats']), (3, 0, 3))
        self.assertEqual(s['CT-101']['title'], 'Catching Ghost Databases')
        self.assertEqual(s['CT-102']['title'], 'Tests That Can Fail')

    def test_ui_page_is_served_and_reads_the_api(self):
        status, html = self.app.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn("api('GET', '/sessions')", html)
        self.assertIn("api('GET', '/reservations')", html)
        self.assertIn("el('label', {for: 'alias'", html)  # alias input is rendered with a label
        self.assertIn('role="alert"', html)


class ReservationTests(AppTestCase):  # AC-03
    def test_reservation_is_created_read_back_and_consumes_one_seat(self):
        status, r = self.reserve()
        self.assertEqual(status, 201)
        self.assertEqual((r['sessionId'], r['attendeeAlias'], r['requestKey'], r['status']), ('CT-101', 'Ada', 'K1', 'active'))
        self.assertTrue(r['id'])
        status, again = self.app.request('GET', '/reservations/' + r['id'])
        self.assertEqual((status, again), (200, r))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 1)
        self.assertEqual(self.db_rows(), [(r['id'], 'CT-101', 'Ada', 'K1', 'active')])

    def test_unknown_reservation_id_is_404(self):
        status, body = self.app.request('GET', '/reservations/does-not-exist')
        self.assert_error(status, body, 404)


class CapacityTests(AppTestCase):  # AC-04
    def test_third_request_for_full_session_is_rejected_without_state_change(self):
        self.assertEqual(self.reserve(alias='Ada', key='K1')[0], 201)
        self.assertEqual(self.reserve(alias='Bob', key='K2')[0], 201)
        status, body = self.reserve(alias='Cy', key='K3')
        self.assert_error(status, body, 409)
        self.assertEqual(body['error']['code'], 'CAPACITY_FULL')
        self.assertEqual(self.sessions()['CT-101']['activeCount'], 2)
        self.assertEqual(len(self.db_rows()), 2)

    def test_concurrent_attempts_for_last_seat_produce_exactly_one_success(self):
        self.assertEqual(self.reserve(alias='Seed', key='seed')[0], 201)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda i: self.reserve(alias='A%d' % i, key='race-%d' % i), range(10)))
        statuses = sorted(s for s, _ in results)
        self.assertEqual(statuses.count(201), 1, results)
        self.assertEqual(statuses.count(409), 9, results)
        self.assertEqual(self.sessions()['CT-101']['activeCount'], 2)
        self.assertEqual(len(self.db_rows()), 2)


class IdempotencyTests(AppTestCase):  # AC-05
    def test_replay_with_same_key_returns_original_without_consuming_seat(self):
        _, first = self.reserve(alias='Ada', key='K1')
        status, replay = self.reserve(alias='  Ada  ', key='K1')
        self.assertEqual(status, 200)
        self.assertEqual(replay, first)
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 1)
        self.assertEqual(len(self.db_rows()), 1)

    def test_key_reuse_with_different_alias_session_or_case_conflicts(self):
        self.reserve(alias='Ada', key='K1')
        for session, alias in (('CT-102', 'Ada'), ('CT-101', 'Bob'), ('CT-101', 'ada')):
            status, body = self.reserve(session=session, alias=alias, key='K1')
            self.assert_error(status, body, 409)
            self.assertEqual(body['error']['code'], 'REQUEST_KEY_CONFLICT')
        s = self.sessions()
        self.assertEqual((s['CT-101']['activeCount'], s['CT-102']['activeCount']), (1, 0))
        self.assertEqual(len(self.db_rows()), 1)

    def test_replay_while_session_full_returns_original_not_capacity_error(self):
        _, first = self.reserve(alias='Ada', key='K1')
        self.assertEqual(self.reserve(alias='Bob', key='K2')[0], 201)
        status, replay = self.reserve(alias='Ada', key='K1')
        self.assertEqual((status, replay), (200, first))
        self.assertEqual(len(self.db_rows()), 2)

    def test_request_keys_are_case_sensitive(self):
        self.reserve(session='CT-102', alias='Ada', key='K1')
        status, other = self.reserve(session='CT-102', alias='Ada', key='k1')
        self.assertEqual(status, 201)
        self.assertEqual(self.sessions()['CT-102']['activeCount'], 2)


class CancellationTests(AppTestCase):  # AC-06
    def test_cancel_releases_one_seat_and_is_idempotent_and_replay_does_not_reactivate(self):
        _, r = self.reserve()
        status, c = self.app.request('POST', '/reservations/%s/cancel' % r['id'], {})
        self.assertEqual((status, c['status'], c['id']), (200, 'cancelled', r['id']))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 2)
        status, c2 = self.app.request('POST', '/reservations/%s/cancel' % r['id'], {})
        self.assertEqual((status, c2), (200, c))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 2)
        status, replay = self.reserve()
        self.assertEqual(status, 200)
        self.assertEqual((replay['id'], replay['status']), (r['id'], 'cancelled'))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 2)
        status, fresh = self.reserve(key='K2')
        self.assertEqual((status, fresh['status']), (201, 'active'))
        self.assertNotEqual(fresh['id'], r['id'])

    def test_cancel_unknown_reservation_is_404(self):
        status, body = self.app.request('POST', '/reservations/nope/cancel', {})
        self.assert_error(status, body, 404)

    def test_percent_encoded_slash_cannot_reach_cancel_route(self):
        _, r = self.reserve()
        status, body = self.app.request('POST', '/reservations/%s%%2Fcancel' % r['id'], {})
        self.assert_error(status, body, 404)
        self.assertEqual(self.app.request('GET', '/reservations/' + r['id'])[1]['status'], 'active')


class DurableStateTests(AppTestCase):  # AC-07
    def test_restart_without_reset_preserves_ids_statuses_and_counts(self):
        _, active = self.reserve(alias='Ada', key='K1')
        _, gone = self.reserve(session='CT-102', alias='Bob', key='K2')
        self.app.request('POST', '/reservations/%s/cancel' % gone['id'], {})
        before = self.sessions()
        self.app.stop()
        self.app.start()
        self.assertEqual(self.sessions(), before)
        self.assertEqual(self.app.request('GET', '/reservations/' + active['id'])[1]['status'], 'active')
        self.assertEqual(self.app.request('GET', '/reservations/' + gone['id'])[1]['status'], 'cancelled')
        self.assertEqual(before['CT-101']['remainingSeats'], 1)
        self.assertEqual(before['CT-102']['remainingSeats'], 3)


class InvalidInputTests(AppTestCase):  # AC-08
    CASES = {
        'unknown session': ({'sessionId': 'CT-999', 'attendeeAlias': 'Ada', 'requestKey': 'X1'}, 404),
        'blank alias': ({'sessionId': 'CT-101', 'attendeeAlias': '   ', 'requestKey': 'X2'}, 400),
        'missing alias': ({'sessionId': 'CT-101', 'requestKey': 'X3'}, 400),
        'missing key': ({'sessionId': 'CT-101', 'attendeeAlias': 'Ada'}, 400),
        'empty key': ({'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': ''}, 400),
        'numeric key': ({'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 7}, 400),
        'whitespace key': ({'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': '   '}, 400),
        'array body': ([], 400),
        'zero-width alias': ({'sessionId': 'CT-101', 'attendeeAlias': '\u200b', 'requestKey': 'X4'}, 400),
        'BOM alias': ({'sessionId': 'CT-101', 'attendeeAlias': '\ufeff ', 'requestKey': 'X5'}, 400),
        'NUL alias': ({'sessionId': 'CT-101', 'attendeeAlias': 'A\x00', 'requestKey': 'X6'}, 400),
    }

    def test_invalid_requests_reject_without_state_change_and_server_stays_up(self):
        baseline = self.sessions()
        for name, (body, expected) in self.CASES.items():
            with self.subTest(name):
                status, resp = self.app.request('POST', '/reservations', body)
                self.assert_error(status, resp, expected)
        hostile = (b'{not json', b'', b'\xff\xfe', b'[' * 20000 + b']' * 20000,
                   b'{"sessionId":' + b'1' * 5000 + b'}',
                   b'{"sessionId":"CT-101","attendeeAlias":"\\ud800","requestKey":"S1"}')
        for raw in hostile:
            with self.subTest(raw=raw):
                status, resp = self.app.request('POST', '/reservations', raw=raw)
                self.assert_error(status, resp, 400)
                self.assertEqual(self.app.request('GET', '/health')[0], 200)
        status, resp = self.app.request('POST', '/reservations/nope/cancel', raw=b'{bad')
        self.assert_error(status, resp, 400)
        self.assertEqual(self.sessions(), baseline)
        self.assertEqual(self.db_rows(), [])
        self.assertEqual(self.reserve()[0], 201)


class ResetSafetyTests(unittest.TestCase):
    def test_reset_refuses_unmarked_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            sqlite3.connect(Path(tmp) / 'seats.db').close()
            result = subprocess.run([sys.executable, 'app.py', '--reset'], cwd=APP_DIR,
                                    env=dict(os.environ, DATA_DIR=tmp), capture_output=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Refusing', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
