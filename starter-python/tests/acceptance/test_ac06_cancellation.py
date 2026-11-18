import unittest

from tests.support import RunningApp, alert_text, table_rows

ADA_K1 = {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1'}
GRACE_K2 = {'sessionId': 'CT-101', 'attendeeAlias': 'Grace', 'requestKey': 'K2'}


def ct101(app):
    _, body = app.request('GET', '/sessions')
    s = body['sessions'][0]
    assert s['id'] == 'CT-101'
    return s['activeCount'], s['remainingSeats']


class AC06Cancellation(unittest.TestCase):
    def reserve(self, app, body):
        status, record = app.request('POST', '/reservations', body)
        self.assertEqual(status, 201, record)
        return record

    def cancel(self, app, record):
        status, cancelled = app.request('POST', '/reservations/%s/cancel' % record['id'], {})
        self.assertEqual(status, 200, cancelled)
        return cancelled

    def test_ac06_cancel_active_returns_cancelled_record_and_releases_exactly_one_seat(self):
        # Given CT-101 is full (Ada and Grace active)
        with RunningApp() as app:
            ada = self.reserve(app, ADA_K1)
            self.reserve(app, GRACE_K2)
            self.assertEqual(ct101(app), (2, 0))
            # When Ada's reservation is cancelled
            status, cancelled = app.request('POST', '/reservations/%s/cancel' % ada['id'], {})
            # Then the response is the stored cancelled record and exactly one seat is free, in API and UI
            self.assertEqual(status, 200)
            self.assertEqual(cancelled, {**ada, 'status': 'cancelled'})
            self.assertEqual(app.request('GET', '/reservations/' + ada['id']), (200, cancelled))
            self.assertEqual(ct101(app), (1, 1))
            _, html = app.request('GET', '/')
            self.assertEqual(table_rows(html, 'sessions')[1][3:], ['1', '1'])

    def test_ac06_repeat_cancel_reports_cancelled_and_leaves_counts_unchanged(self):
        # Given Ada's reservation was cancelled
        with RunningApp() as app:
            ada = self.reserve(app, ADA_K1)
            cancelled = self.cancel(app, ada)
            # When it is cancelled again
            status, again = app.request('POST', '/reservations/%s/cancel' % ada['id'], {})
            # Then it still reports the same cancelled record and nothing moves
            self.assertEqual((status, again), (200, cancelled))
            self.assertEqual(ct101(app), (0, 2))
            self.assertEqual(app.stored_reservation_count(), 1)

    def test_ac06_replaying_original_request_after_cancel_does_not_reactivate(self):
        # Given Ada's reservation was cancelled
        with RunningApp() as app:
            ada = self.reserve(app, ADA_K1)
            cancelled = self.cancel(app, ada)
            # When the original create request is replayed
            status, replay = app.request('POST', '/reservations', ADA_K1)
            # Then it returns that same cancelled reservation; no seat taken, no new row
            self.assertEqual((status, replay), (200, cancelled))
            self.assertEqual(ct101(app), (0, 2))
            self.assertEqual(app.stored_reservation_count(), 1)

    def test_ac06_ui_cancel_button_cancels_and_releases_the_seat(self):
        # Given Ada has an active CT-101 reservation
        with RunningApp() as app:
            ada = self.reserve(app, ADA_K1)
            html = app.page()
            self.assertIn('aria-label="Cancel reservation for Ada in CT-101"', html)
            # When the helper presses its Cancel button
            status, html = app.post_form('/ui/cancel', {'reservationId': ada['id']})
            # Then the page confirms the stored cancelled status and the seat is back, in UI and API
            self.assertEqual(status, 200)
            self.assertIn('cancelled', alert_text(html))
            self.assertRegex(html, r'<p id="message" role="status" class="message-cancelled"',
                             'cancellation confirmation must use the red cancelled style')
            self.assertEqual(table_rows(html, 'reservations')[1][4], 'cancelled')
            self.assertEqual(table_rows(html, 'sessions')[1][3:], ['0', '2'])
            self.assertEqual(ct101(app), (0, 2))
            self.assertNotIn('aria-label="Cancel reservation for Ada in CT-101"', html)

    def test_ac06_new_request_key_is_needed_for_a_new_reservation(self):
        # Given Ada's K1 reservation was cancelled
        with RunningApp() as app:
            ada = self.reserve(app, ADA_K1)
            self.cancel(app, ada)
            # When Ada reserves again with a new key
            again = self.reserve(app, {**ADA_K1, 'requestKey': 'K1-retry'})
            # Then it is a new active reservation with a different ID
            self.assertNotEqual(again['id'], ada['id'])
            self.assertEqual(again['status'], 'active')
            self.assertEqual(ct101(app), (1, 1))


if __name__ == '__main__':
    unittest.main()
