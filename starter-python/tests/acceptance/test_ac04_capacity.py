import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from tests.support import RunningApp, alert_text

BATCHES, ATTEMPTS = 10, 10


def reserve(alias, key, session='CT-101'):
    return {'sessionId': session, 'attendeeAlias': alias, 'requestKey': key}


def ct101(app):
    _, body = app.request('GET', '/sessions')
    s = body['sessions'][0]
    assert s['id'] == 'CT-101'
    return s['activeCount'], s['remainingSeats']


class AC04Capacity(unittest.TestCase):
    def fill_ct101(self, app):
        for alias, key in (('Ada', 'K1'), ('Grace', 'K2')):
            status, body = app.request('POST', '/reservations', reserve(alias, key))
            self.assertEqual(status, 201, body)

    def test_ac04_third_distinct_request_is_rejected_with_capacity_error_and_no_row(self):
        # Given CT-101 (capacity 2) has two active reservations
        with RunningApp() as app:
            self.fill_ct101(app)
            sessions_before = app.request('GET', '/sessions')
            # When a third, distinct request arrives
            status, body = app.request('POST', '/reservations', reserve('Linus', 'K3'))
            # Then it is a 409 with a clear capacity error, and nothing was created
            self.assertEqual(status, 409, body)
            self.assertEqual(body['error']['code'], 'CAPACITY_FULL')
            self.assertTrue(body['error']['message'])
            self.assertEqual(app.request('GET', '/sessions'), sessions_before)
            self.assertEqual(ct101(app), (2, 0))
            self.assertEqual(app.stored_reservation_count(), 2)
            # And CT-102 is unaffected by CT-101 being full
            self.assertEqual(app.request('POST', '/reservations', reserve('Linus', 'K4', 'CT-102'))[0], 201)

    def test_ac04_ui_shows_capacity_error_when_full(self):
        # Given CT-101 is full
        with RunningApp() as app:
            self.fill_ct101(app)
            # When the helper tries to reserve CT-101 in the UI
            status, html = app.post_form('/ui/reserve',
                                         {'sessionId': 'CT-101', 'attendeeAlias': 'Linus', 'requestKey': 'U3'})
            # Then the page answers 409 with a visible capacity error and no row was created
            self.assertEqual(status, 409)
            self.assertIn('No remaining seats', alert_text(html))
            self.assertEqual(app.stored_reservation_count(), 2)

    def test_ac04_replay_of_existing_key_still_returns_original_when_full(self):
        # Given CT-101 is full
        with RunningApp() as app:
            self.fill_ct101(app)
            _, original = app.request('POST', '/reservations', reserve('Ada', 'K1'))
            # When Ada's original request is replayed
            status, replay = app.request('POST', '/reservations', reserve('Ada', 'K1'))
            # Then it is a replay (same record), not a capacity error
            self.assertEqual((status, replay), (200, original))

    def test_ac04_simultaneous_attempts_for_last_seat_produce_exactly_one_success(self):
        for batch in range(BATCHES):
            with self.subTest(batch=batch), RunningApp() as app:
                # Given a fresh state where CT-101 has exactly one seat left
                self.assertEqual(app.request('POST', '/reservations', reserve('Ada', 'K0'))[0], 201)
                barrier = threading.Barrier(ATTEMPTS)

                def attempt(i):
                    barrier.wait()
                    return app.request('POST', '/reservations', reserve('Racer%d' % i, 'B%d-R%d' % (batch, i)))

                # When ten distinct requests arrive at the same moment
                with ThreadPoolExecutor(ATTEMPTS) as pool:
                    results = list(pool.map(attempt, range(ATTEMPTS)))
                # Then exactly one succeeds, the rest reject, and storage holds exactly 2 active
                statuses = sorted(status for status, _ in results)
                self.assertEqual(statuses.count(201), 1, statuses)
                self.assertTrue(all(400 <= s < 500 for s in statuses if s != 201), statuses)
                self.assertEqual(ct101(app), (2, 0))
                self.assertEqual(app.stored_reservation_count(), 2)


if __name__ == '__main__':
    unittest.main()
