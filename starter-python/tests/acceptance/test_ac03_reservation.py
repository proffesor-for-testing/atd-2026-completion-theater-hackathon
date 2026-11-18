import unittest

from tests.support import RunningApp, alert_text, form_request_key, table_rows

ADA_K1 = {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1'}


class AC03Reservation(unittest.TestCase):
    def test_ac03_reserve_ada_k1_returns_active_record_with_stable_id(self):
        # Given a freshly reset app
        with RunningApp() as app:
            # When Ada reserves CT-101 with key K1
            status, body = app.request('POST', '/reservations', ADA_K1)
            # Then it succeeds with a generated ID, the request fields and active status
            self.assertEqual(status, 201)
            self.assertIsInstance(body.get('id'), str)
            self.assertTrue(body['id'])
            self.assertEqual(body, {'id': body['id'], **ADA_K1, 'status': 'active'})

    def test_ac03_get_reservation_by_id_returns_the_same_record(self):
        # Given Ada has reserved CT-101
        with RunningApp() as app:
            status, created = app.request('POST', '/reservations', ADA_K1)
            self.assertEqual(status, 201)
            # When I read it back by ID, twice
            first = app.request('GET', '/reservations/' + created['id'])
            second = app.request('GET', '/reservations/' + created['id'])
            # Then storage returns the same record both times
            self.assertEqual(first, (200, created))
            self.assertEqual(second, (200, created))

    def test_ac03_remaining_seats_drop_to_one_in_api_and_ui(self):
        # Given Ada has reserved CT-101
        with RunningApp() as app:
            app.request('POST', '/reservations', ADA_K1)
            # When I read the sessions and open the UI
            _, body = app.request('GET', '/sessions')
            _, html = app.request('GET', '/')
            # Then CT-101 has 1 active and 1 remaining, CT-102 is untouched, and the UI agrees
            counts = {s['id']: (s['activeCount'], s['remainingSeats']) for s in body['sessions']}
            self.assertEqual(counts, {'CT-101': (1, 1), 'CT-102': (0, 3)})
            ui = {row[0]: (row[3], row[4]) for row in table_rows(html, 'sessions')[1:]}
            self.assertEqual(ui, {'CT-101': ('1', '1'), 'CT-102': ('0', '3')})

    def test_ac03_ui_reserve_form_is_labelled(self):
        # Given the UI
        with RunningApp() as app:
            html = app.page()
            # Then the reserve form's visible controls have labels (keyboard/screen-reader usable)
            for control in ('session', 'alias'):
                self.assertIn('<label for="%s">' % control, html)
                self.assertIn('id="%s"' % control, html)
            self.assertIn('<button type="submit">Reserve</button>', html)

    def test_ac03_ui_reserve_shows_stored_confirmation_and_updates_counts(self):
        # Given the UI
        with RunningApp() as app:
            key = form_request_key(app.page())
            # When the helper submits the reserve form for Ada in CT-101
            status, html = app.post_form('/ui/reserve',
                                         {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': key})
            # Then the page confirms from storage, lists the reservation, and agrees with the API
            self.assertEqual(status, 200)
            _, api = app.request('GET', '/sessions')
            (reservation,) = table_rows(html, 'reservations')[1:]
            self.assertEqual(reservation[1:5], ['CT-101', 'Ada', key, 'active'])
            self.assertEqual(app.request('GET', '/reservations/' + reservation[0])[1]['status'], 'active')
            self.assertIn('active', alert_text(html))
            self.assertIn(reservation[0], alert_text(html))
            self.assertNotRegex(html, r'<p id="message"[^>]*message-cancelled')  # active booking is not red
            self.assertEqual(table_rows(html, 'sessions')[1][3:], ['1', '1'])
            self.assertEqual(api['sessions'][0]['remainingSeats'], 1)

    def test_ac03_ui_double_submit_of_same_form_is_a_replay_not_a_second_booking(self):
        # Given the helper has submitted the reserve form once
        with RunningApp() as app:
            form = {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': form_request_key(app.page())}
            app.post_form('/ui/reserve', form)
            # When the same form is submitted again (double click / resubmit)
            status, html = app.post_form('/ui/reserve', form)
            # Then there is still exactly one reservation
            self.assertEqual(status, 200)
            self.assertEqual(len(table_rows(html, 'reservations')[1:]), 1)
            self.assertEqual(app.stored_reservation_count(), 1)

    def test_ac03_unknown_reservation_id_is_404(self):
        # Given a freshly reset app
        with RunningApp() as app:
            # When I read an ID that was never issued
            status, body = app.request('GET', '/reservations/does-not-exist')
            # Then it is a 4xx with an error, not an empty success
            self.assertEqual(status, 404)
            self.assertTrue(body.get('error'))


if __name__ == '__main__':
    unittest.main()
