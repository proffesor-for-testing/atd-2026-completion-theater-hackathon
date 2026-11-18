"""Black-box behavioral tests for Session Seat Desk.

Every test launches the real app.py as a separate process with its own fresh
DATA_DIR and port, talks to it over HTTP only, and (where the PRD asks for it)
reads the SQLite store directly as an independent oracle.

Run from this directory:  python -m unittest -v test_app
A failing test makes the process exit non-zero.
"""
from contextlib import closing
import json
import random
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
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class AppProcess:
    """One running app.py process bound to a given state directory."""

    def __init__(self, state_dir, port=None):
        self.state_dir, self.port = state_dir, port or free_port()
        self.env = {'DATA_DIR': str(state_dir), 'PORT': str(self.port),
                    'SYSTEMROOT': _env('SYSTEMROOT'), 'PATH': _env('PATH')}
        self.process = None

    def reset(self):
        result = subprocess.run([sys.executable, 'app.py', '--reset'], cwd=APP_DIR, env=self.env,
                                capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            raise AssertionError('reset failed: %s %s' % (result.stdout, result.stderr))

    def start(self):
        self.process = subprocess.Popen([sys.executable, 'app.py'], cwd=APP_DIR, env=self.env,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError('app exited early with %s' % self.process.returncode)
            try:
                if self.request('GET', '/health')[0] == 200:
                    return self
            except OSError:
                time.sleep(0.05)
        raise AssertionError('app did not become ready')

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)

    def request(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), data=data, method=method,
                                     headers={'Content-Type': 'application/json'})
        try:
            response = OPENER.open(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read().decode() or 'null')

    # Convenience wrappers
    def reserve(self, session_id, alias, key):
        return self.request('POST', '/reservations',
                            {'sessionId': session_id, 'attendeeAlias': alias, 'requestKey': key})

    def cancel(self, reservation_id):
        return self.request('POST', '/reservations/%s/cancel' % reservation_id, {})

    def sessions(self):
        status, body = self.request('GET', '/sessions')
        assert status == 200, (status, body)
        return {s['id']: s for s in body['sessions']}

    def store_rows(self):
        """Independent oracle: read the actual SQLite file, not the API."""
        with closing(sqlite3.connect(self.state_dir / 'seats.db')) as connection:
            return connection.execute(
                'SELECT id, session_id, attendee_alias, request_key, status FROM reservations ORDER BY rowid'
            ).fetchall()


def _env(name):
    import os
    return os.environ.get(name, '')


class AppTestCase(unittest.TestCase):
    """Fresh reset + running process per test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.app = AppProcess(Path(self.tmp.name) / 'state')
        self.app.reset()
        self.app.start()
        self.addCleanup(self.app.stop)

    def assertCounts(self, session_id, active, remaining):
        s = self.app.sessions()[session_id]
        self.assertEqual((s['activeCount'], s['remainingSeats']), (active, remaining), s)

    def assertRejected(self, response, expected_status):
        status, body = response
        self.assertEqual(status, expected_status, body)
        self.assertTrue(body and body.get('error'), 'rejection must carry a non-empty error: %r' % body)


class SessionsTests(AppTestCase):
    def test_ac02_fresh_reset_seeds_exact_sessions(self):
        self.assertEqual(self.app.request('GET', '/sessions'), (200, {'sessions': [
            {'id': 'CT-101', 'title': 'Catching Ghost Databases', 'capacity': 2, 'activeCount': 0,
             'remainingSeats': 2},
            {'id': 'CT-102', 'title': 'Tests That Can Fail', 'capacity': 3, 'activeCount': 0,
             'remainingSeats': 3}]}))

    def test_ui_page_is_served_with_labelled_controls(self):
        req = urllib.request.Request('http://127.0.0.1:%d/' % self.app.port)
        with OPENER.open(req, timeout=10) as response:
            html = response.read().decode()
        for control in ('session-select', 'alias-input', 'key-input'):
            self.assertIn('<label for="%s">' % control, html)


class ReservationTests(AppTestCase):
    def test_ac03_reserve_then_independent_readback(self):
        status, created = self.app.reserve('CT-101', 'Ada', 'K1')
        self.assertEqual(status, 201, created)
        self.assertEqual(created['status'], 'active')
        self.assertTrue(created['id'])
        self.assertEqual(self.app.request('GET', '/reservations/' + created['id']), (200, created))
        self.assertCounts('CT-101', 1, 1)
        self.assertEqual(self.app.store_rows(), [(created['id'], 'CT-101', 'Ada', 'K1', 'active')])

    def test_unknown_reservation_readback_is_404(self):
        self.assertRejected(self.app.request('GET', '/reservations/does-not-exist'), 404)

    def test_ac04_sequential_capacity_rejects_third_booking(self):
        self.assertEqual(self.app.reserve('CT-101', 'Ada', 'K1')[0], 201)
        self.assertEqual(self.app.reserve('CT-101', 'Grace', 'K2')[0], 201)
        status, body = self.app.reserve('CT-101', 'Linus', 'K3')
        self.assertEqual(status, 409, body)
        self.assertEqual(body['error']['code'], 'CAPACITY_FULL')
        self.assertCounts('CT-101', 2, 0)
        self.assertEqual(len(self.app.store_rows()), 2)

    def test_ac04_concurrent_attempts_for_last_seat_produce_exactly_one_winner(self):
        self.assertEqual(self.app.reserve('CT-101', 'Ada', 'K0')[0], 201)
        attempts = 10
        barrier = threading.Barrier(attempts)
        results = [None] * attempts

        def attempt(i):
            barrier.wait()
            results[i] = self.app.reserve('CT-101', 'Racer%d' % i, 'race-%d' % i)

        threads = [threading.Thread(target=attempt, args=(i,)) for i in range(attempts)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        statuses = sorted(r[0] for r in results)
        self.assertEqual(statuses, [201] + [409] * (attempts - 1), results)
        self.assertCounts('CT-101', 2, 0)
        self.assertEqual(len(self.app.store_rows()), 2, 'rejected attempts must not insert rows')

    def test_ac05_replay_returns_original_and_conflicts_change_nothing(self):
        status, original = self.app.reserve('CT-101', 'Ada', 'K1')
        self.assertEqual(status, 201)
        for alias in ('Ada', '  Ada  '):
            status, replay = self.app.reserve('CT-101', alias, 'K1')
            self.assertEqual((status, replay), (200, original))
        self.assertCounts('CT-101', 1, 1)
        rows_before = self.app.store_rows()
        for session_id, alias in (('CT-101', 'Grace'), ('CT-102', 'Ada'), ('CT-101', 'ada')):
            status, body = self.app.reserve(session_id, alias, 'K1')
            self.assertEqual(status, 409, (session_id, alias, body))
            self.assertEqual(body['error']['code'], 'KEY_CONFLICT')
        self.assertCounts('CT-101', 1, 1)
        self.assertCounts('CT-102', 0, 3)
        self.assertEqual(self.app.store_rows(), rows_before)

    def test_ac05_replay_wins_over_full_capacity(self):
        _, ada = self.app.reserve('CT-101', 'Ada', 'K1')
        self.app.reserve('CT-101', 'Grace', 'K2')
        self.assertEqual(self.app.reserve('CT-101', 'Ada', 'K1'), (200, ada))


class CancellationTests(AppTestCase):
    def test_ac06_cancel_releases_one_seat_and_repeat_is_stable(self):
        _, created = self.app.reserve('CT-101', 'Ada', 'K1')
        self.assertCounts('CT-101', 1, 1)
        status, cancelled = self.app.cancel(created['id'])
        self.assertEqual(status, 200)
        self.assertEqual(cancelled, dict(created, status='cancelled'))
        self.assertCounts('CT-101', 0, 2)
        self.assertEqual(self.app.cancel(created['id']), (200, cancelled))
        self.assertCounts('CT-101', 0, 2)

    def test_ac06_replay_after_cancel_returns_cancelled_record_without_reactivating(self):
        _, created = self.app.reserve('CT-101', 'Ada', 'K1')
        self.app.cancel(created['id'])
        status, replay = self.app.reserve('CT-101', 'Ada', 'K1')
        self.assertEqual(status, 200)
        self.assertEqual(replay, dict(created, status='cancelled'))
        self.assertCounts('CT-101', 0, 2)
        self.assertEqual(self.app.store_rows(), [(created['id'], 'CT-101', 'Ada', 'K1', 'cancelled')])
        self.assertEqual(self.app.reserve('CT-101', 'Ada', 'K2')[0], 201, 'a new key books again')


class DurabilityTests(AppTestCase):
    def test_ac07_active_and_cancelled_state_survive_real_process_restart(self):
        _, first = self.app.reserve('CT-101', 'Ada', 'K1')
        _, second = self.app.reserve('CT-101', 'Grace', 'K2')
        self.app.cancel(first['id'])
        before_sessions = self.app.sessions()
        old_pid = self.app.process.pid

        self.app.stop()
        self.assertIsNotNone(self.app.process.returncode, 'old process must be gone')
        restarted = AppProcess(self.app.state_dir, port=free_port()).start()  # no reset
        self.addCleanup(restarted.stop)
        self.assertNotEqual(restarted.process.pid, old_pid)

        self.assertEqual(restarted.sessions(), before_sessions)
        self.assertCounts_on(restarted, 'CT-101', 1, 1)
        self.assertEqual(restarted.request('GET', '/reservations/' + first['id']),
                         (200, dict(first, status='cancelled')))
        self.assertEqual(restarted.request('GET', '/reservations/' + second['id']), (200, second))

    def assertCounts_on(self, app, session_id, active, remaining):
        s = app.sessions()[session_id]
        self.assertEqual((s['activeCount'], s['remainingSeats']), (active, remaining))


class InvalidInputTests(AppTestCase):
    def test_ac08_all_five_invalid_cases_reject_without_state_change(self):
        self.app.reserve('CT-101', 'Ada', 'K1')  # some existing state to protect
        sessions_before, rows_before = self.app.sessions(), self.app.store_rows()
        cases = {
            'unknown session': (self.app.reserve('CT-999', 'Ada', 'X1'), 404),
            'blank alias': (self.app.reserve('CT-101', '   ', 'X2'), 400),
            'missing request key': (self.app.request('POST', '/reservations',
                                                     {'sessionId': 'CT-101', 'attendeeAlias': 'Ada'}), 400),
            'malformed JSON': (self.app.request('POST', '/reservations', raw=b'{"sessionId": "CT-1'), 400),
            'cancel unknown reservation': (self.app.cancel('no-such-reservation'), 404),
        }
        for name, (response, expected) in cases.items():
            with self.subTest(name):
                self.assertRejected(response, expected)
        self.assertEqual(self.app.sessions(), sessions_before)
        self.assertEqual(self.app.store_rows(), rows_before)
        self.assertEqual(self.app.request('GET', '/sessions')[0], 200, 'process must stay available')

    def test_other_malformed_shapes_are_rejected(self):
        for name, body in (('empty request key', {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': ''}),
                           ('non-string key', {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 7}),
                           ('array body', ['CT-101'])):
            with self.subTest(name):
                self.assertRejected(self.app.request('POST', '/reservations', body), 400)
        self.assertEqual(self.app.store_rows(), [])


class ModelBasedTests(AppTestCase):
    """Extra technique (D2): seeded random operation sequences checked against a reference model.

    Question: does any interleaving of reserve / replay / conflict / cancel break the invariants
    (count == model, active <= capacity, store agrees with API)? Seeds are fixed so failures reproduce.
    """
    CAPACITY = {'CT-101': 2, 'CT-102': 3}

    def test_random_sequences_match_reference_model(self):
        for seed in range(3):
            with self.subTest(seed=seed):
                if seed:
                    self.app.stop()
                    self.app = AppProcess(Path(self.tmp.name) / ('state-%d' % seed))
                    self.app.reset()
                    self.app.start()
                    self.addCleanup(self.app.stop)
                self._run_sequence(random.Random(seed), steps=40)

    def _run_sequence(self, rng, steps):
        model = {}  # key -> {'id', 'session', 'alias', 'status'}
        aliases = ['Ada', 'Grace', 'Linus', 'Edsger']
        for step in range(steps):
            op = rng.choice(['reserve', 'reserve', 'replay', 'conflict', 'cancel'])
            context = 'step %d %s' % (step, op)
            if op == 'reserve' or not model:
                session = rng.choice(list(self.CAPACITY))
                key, alias = 'k%d' % step, rng.choice(aliases)
                active = sum(1 for r in model.values() if r['session'] == session and r['status'] == 'active')
                status, body = self.app.reserve(session, alias, key)
                if active < self.CAPACITY[session]:
                    self.assertEqual(status, 201, (context, body))
                    model[key] = {'id': body['id'], 'session': session, 'alias': alias, 'status': 'active'}
                else:
                    self.assertEqual(status, 409, (context, body))
            elif op == 'replay':
                key, r = rng.choice(list(model.items()))
                status, body = self.app.reserve(r['session'], ' %s ' % r['alias'], key)
                self.assertEqual((status, body['id'], body['status']), (200, r['id'], r['status']), context)
            elif op == 'conflict':
                key, r = rng.choice(list(model.items()))
                other = 'CT-102' if r['session'] == 'CT-101' else 'CT-101'
                self.assertEqual(self.app.reserve(other, r['alias'], key)[0], 409, context)
            else:
                key, r = rng.choice(list(model.items()))
                status, body = self.app.cancel(r['id'])
                self.assertEqual((status, body['status']), (200, 'cancelled'), context)
                r['status'] = 'cancelled'
            self._check_invariants(model, context)

    def _check_invariants(self, model, context):
        sessions = self.app.sessions()
        for session, capacity in self.CAPACITY.items():
            expected = sum(1 for r in model.values() if r['session'] == session and r['status'] == 'active')
            s = sessions[session]
            self.assertEqual(s['activeCount'], expected, context)
            self.assertEqual(s['remainingSeats'], capacity - expected, context)
            self.assertLessEqual(s['activeCount'], capacity, context)
        stored = {row[3]: row[4] for row in self.app.store_rows()}
        self.assertEqual(stored, {k: r['status'] for k, r in model.items()}, context)


if __name__ == '__main__':
    unittest.main(verbosity=2)
