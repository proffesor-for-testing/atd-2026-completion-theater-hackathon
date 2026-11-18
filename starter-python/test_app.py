"""Unit tests of store.py — the PRD rules, with no server, browser or npm install.

    python3 -m unittest -v test_app        (Windows: py -3 -m unittest -v test_app)

Each test gets its own temporary fixture directory. Assertions read state back through
a fresh Store (a new connection), never trusting the value a write returned.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from store import Store, StoreError

SEED = Path(__file__).resolve().parent / 'sessions.json'


def req(key, alias='Ada', session='CT-101'):
    return {'sessionId': session, 'attendeeAlias': alias, 'requestKey': key}


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name) / 'fixture'
        self.store = Store(self.data_dir)
        self.store.reset(SEED)

    def tearDown(self):
        self._tmp.cleanup()

    def counts(self):
        """Readback through a brand-new Store, as a restarted process would see it."""
        return {s['id']: (s['activeCount'], s['remainingSeats']) for s in Store(self.data_dir).sessions()}

    def rejects(self, body, status, code):
        before = self.counts()
        with self.assertRaises(StoreError) as caught:
            self.store.reserve(body)
        self.assertEqual((caught.exception.status, caught.exception.code), (status, code))
        self.assertEqual(self.counts(), before, 'a rejection must not change counts')


class SeedAndRead(StoreTestCase):
    def test_fresh_reset_seeds_two_sessions_with_zero_active(self):
        sessions = Store(self.data_dir).sessions()
        self.assertEqual([(s['id'], s['capacity'], s['activeCount'], s['remainingSeats']) for s in sessions],
                         [('CT-101', 2, 0, 2), ('CT-102', 3, 0, 3)])

    def test_reset_refuses_a_database_it_did_not_create(self):
        foreign = Path(self._tmp.name) / 'foreign'
        foreign.mkdir()
        sqlite3.connect(foreign / 'seats.db').close()
        with self.assertRaises(RuntimeError):
            Store(foreign).reset(SEED)


class Reserve(StoreTestCase):
    def test_reservation_is_stored_and_read_back_by_id(self):
        created, record = self.store.reserve(req('K1'))
        self.assertTrue(created)
        stored = Store(self.data_dir).get(record['id'])
        self.assertEqual({k: stored[k] for k in ('sessionId', 'attendeeAlias', 'requestKey', 'status')},
                         {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1', 'status': 'active'})
        self.assertEqual(stored['id'], record['id'])
        self.assertEqual(self.counts()['CT-101'], (1, 1))

    def test_alias_is_trimmed_before_storing(self):
        _, record = self.store.reserve(req('K1', '  Ada  '))
        self.assertEqual(Store(self.data_dir).get(record['id'])['attendeeAlias'], 'Ada')


class Capacity(StoreTestCase):
    def test_third_reservation_in_a_two_seat_session_is_rejected(self):
        self.store.reserve(req('K1'))
        self.store.reserve(req('K2', 'Bob'))
        self.rejects(req('K3', 'Cy'), 409, 'CAPACITY_FULL')
        self.assertEqual(self.counts()['CT-101'], (2, 0))

    def test_concurrent_requests_for_the_last_seat_admit_exactly_one(self):
        self.store.reserve(req('seed'))
        barrier = threading.Barrier(10)

        def attempt(i):
            barrier.wait(timeout=5)
            try:
                return Store(self.data_dir).reserve(req('race-%d' % i, 'Alias-%d' % i))[0]
            except StoreError as err:
                return err.code

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(attempt, range(10)))
        self.assertEqual(results.count(True), 1, results)
        self.assertEqual(results.count('CAPACITY_FULL'), 9, results)
        self.assertEqual(self.counts()['CT-101'], (2, 0))


class Idempotency(StoreTestCase):
    def test_replay_with_trimmed_alias_returns_the_original_without_a_second_seat(self):
        _, first = self.store.reserve(req('K1'))
        created, replay = self.store.reserve(req('K1', ' Ada '))
        self.assertFalse(created)
        self.assertEqual(replay['id'], first['id'])
        self.assertEqual(self.counts()['CT-101'], (1, 1))

    def test_key_reused_for_another_alias_or_session_conflicts(self):
        self.store.reserve(req('K1'))
        self.rejects(req('K1', 'Bob'), 409, 'REQUEST_KEY_CONFLICT')
        self.rejects(req('K1', session='CT-102'), 409, 'REQUEST_KEY_CONFLICT')

    def test_alias_comparison_is_case_sensitive(self):
        self.store.reserve(req('K1'))
        self.rejects(req('K1', 'ada'), 409, 'REQUEST_KEY_CONFLICT')


class Cancellation(StoreTestCase):
    def test_cancel_releases_one_seat_and_repeating_changes_nothing(self):
        _, record = self.store.reserve(req('K1'))
        first = self.store.cancel(record['id'])
        self.assertEqual(first['status'], 'cancelled')
        self.assertEqual(self.counts()['CT-101'], (0, 2))
        again = self.store.cancel(record['id'])
        self.assertEqual(again, first, 'repeat cancel must return the same record unchanged')
        self.assertEqual(self.counts()['CT-101'], (0, 2))

    def test_replaying_a_cancelled_request_does_not_reactivate_it(self):
        _, record = self.store.reserve(req('K1'))
        self.store.cancel(record['id'])
        created, replay = self.store.reserve(req('K1'))
        self.assertFalse(created)
        self.assertEqual((replay['id'], replay['status']), (record['id'], 'cancelled'))
        self.assertEqual(self.counts()['CT-101'], (0, 2))

    def test_cancelling_an_unknown_reservation_is_rejected(self):
        with self.assertRaises(StoreError) as caught:
            self.store.cancel('not-a-real-id')
        self.assertEqual(caught.exception.status, 404)


class Durability(StoreTestCase):
    def test_active_and_cancelled_records_survive_a_new_store_on_the_same_directory(self):
        _, active = self.store.reserve(req('K1'))
        _, cancelled = self.store.reserve(req('K2', 'Bob'))
        self.store.cancel(cancelled['id'])
        reopened = Store(self.data_dir)
        self.assertEqual(reopened.get(active['id'])['status'], 'active')
        self.assertEqual(reopened.get(cancelled['id'])['status'], 'cancelled')
        self.assertEqual(self.counts()['CT-101'], (1, 1))


class InvalidInput(StoreTestCase):
    def test_each_invalid_request_is_rejected_without_a_state_change(self):
        cases = [
            (req('K1', session='UNKNOWN'), 404, 'SESSION_NOT_FOUND'),
            (req('K2', '   '), 400, 'ALIAS_REQUIRED'),
            ({'sessionId': 'CT-101', 'attendeeAlias': 'Ada'}, 400, 'REQUEST_KEY_REQUIRED'),
            (req(''), 400, 'REQUEST_KEY_REQUIRED'),
            ([1, 2], 400, 'INVALID_BODY'),
            (dict(req('K3'), status='active'), 400, 'UNKNOWN_FIELD'),
            (req('K4', 'x' * 65), 400, 'ALIAS_TOO_LONG'),
            (req('K5', 'Ada\x00'), 400, 'ALIAS_INVALID'),
            (req('K6', 42), 400, 'ALIAS_REQUIRED'),
        ]
        for body, status, code in cases:
            with self.subTest(code=code):
                self.rejects(body, status, code)
        self.assertEqual(Store(self.data_dir).list(), [], 'no hidden row may be inserted by a rejection')


if __name__ == '__main__':
    unittest.main(verbosity=2)
