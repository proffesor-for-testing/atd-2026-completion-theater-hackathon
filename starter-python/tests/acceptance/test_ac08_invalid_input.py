import unittest

from tests.support import RunningApp, alert_text

VALID = {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1'}

INVALID_CREATES = {
    'unknown session': {**VALID, 'sessionId': 'CT-999'},
    'blank alias': {**VALID, 'attendeeAlias': ''},
    'whitespace-only alias': {**VALID, 'attendeeAlias': '   \t'},
    'missing alias': {'sessionId': 'CT-101', 'requestKey': 'K1'},
    'missing request key': {'sessionId': 'CT-101', 'attendeeAlias': 'Ada'},
    'empty request key': {**VALID, 'requestKey': ''},
    'non-string request key': {**VALID, 'requestKey': 42},
    'alias longer than 30 characters': {**VALID, 'attendeeAlias': 'A' * 31},
    'missing session': {'attendeeAlias': 'Ada', 'requestKey': 'K1'},
}

MALFORMED_BODIES = {
    'malformed JSON': b'{"sessionId": "CT-101", ',
    'not JSON at all': b'reserve please',
    'JSON array instead of object': b'[]',
    'empty body': b'',
}


class AC08InvalidInput(unittest.TestCase):
    def assert_rejected_without_state_change(self, app, method, path, body=None, raw=None):
        sessions_before = app.request('GET', '/sessions')
        rows_before = app.stored_reservation_count()
        status, response = app.request(method, path, body, raw)
        self.assertTrue(400 <= status < 500, 'expected 4xx, got %s %r' % (status, response))
        self.assertIsInstance(response, dict)
        self.assertTrue(response.get('error'), 'non-empty JSON error required')
        self.assertEqual(app.request('GET', '/sessions'), sessions_before)
        self.assertEqual(app.stored_reservation_count(), rows_before)

    def test_ac08_invalid_reservation_fields_reject_with_clear_error_and_no_state_change(self):
        # Given a running app with one existing reservation
        with RunningApp() as app:
            self.assertEqual(app.request('POST', '/reservations', {**VALID, 'requestKey': 'K0'})[0], 201)
            for name, body in INVALID_CREATES.items():
                with self.subTest(name):
                    # When I submit an invalid reservation
                    # Then it is a 4xx with an error and nothing changed in API or store
                    self.assert_rejected_without_state_change(app, 'POST', '/reservations', body)

    def test_ac08_malformed_bodies_reject_with_clear_error_and_no_state_change(self):
        # Given a running app
        with RunningApp() as app:
            for name, raw in MALFORMED_BODIES.items():
                with self.subTest(name):
                    # When I send a body that is not a JSON object
                    # Then it is a 4xx with an error and nothing changed
                    self.assert_rejected_without_state_change(app, 'POST', '/reservations', raw=raw)

    def test_ac08_cancelling_unknown_reservation_rejects_with_no_state_change(self):
        # Given a running app
        with RunningApp() as app:
            # When I cancel an ID that was never issued
            # Then it is a 4xx with an error and nothing changed
            self.assert_rejected_without_state_change(app, 'POST', '/reservations/no-such-id/cancel', {})

    def test_ac08_alias_of_exactly_30_characters_after_trimming_is_accepted(self):
        # Given a running app (A-05: alias max 30 characters, counted after trimming)
        with RunningApp() as app:
            # When the alias is exactly 30 characters, padded with whitespace
            alias = 'B' * 30
            status, body = app.request('POST', '/reservations', {**VALID, 'attendeeAlias': '  %s \t' % alias})
            # Then it is accepted and stored trimmed
            self.assertEqual(status, 201, body)
            self.assertEqual(body['attendeeAlias'], alias)
            # And 31 characters gives a clear length error
            status, body = app.request('POST', '/reservations', {**VALID, 'requestKey': 'K2',
                                                                 'attendeeAlias': 'B' * 31})
            self.assertEqual(status, 400)
            self.assertIn('30 characters', body['error']['message'])

    def test_ac08_ui_alias_input_is_limited_to_30_characters(self):
        # Given the UI
        with RunningApp() as app:
            # Then the alias field itself stops typing past 30 characters
            self.assertIn('maxlength="30"', app.page())

    def test_ac08_ui_shows_visible_errors_with_4xx_and_no_state_change(self):
        cases = {
            'blank alias': ('/ui/reserve', {'sessionId': 'CT-101', 'attendeeAlias': '   ', 'requestKey': 'U1'},
                            'attendeeAlias must not be blank'),
            'unknown reservation': ('/ui/cancel', {'reservationId': 'no-such-id'}, 'Unknown reservation'),
        }
        # Given a running app
        with RunningApp() as app:
            for name, (path, form, message) in cases.items():
                with self.subTest(name):
                    sessions_before = app.request('GET', '/sessions')
                    # When the helper submits a bad form
                    status, html = app.post_form(path, form)
                    # Then the page answers 4xx with the error visible in the alert region, nothing changed
                    self.assertEqual(status, 400 if name == 'blank alias' else 404)
                    self.assertIn('role="alert"', html)
                    self.assertIn(message, alert_text(html))
                    self.assertEqual(app.request('GET', '/sessions'), sessions_before)
                    self.assertEqual(app.stored_reservation_count(), 0)

    def test_ac08_process_stays_available_after_bad_requests(self):
        # Given a running app that has received every kind of bad request
        with RunningApp() as app:
            for body in INVALID_CREATES.values():
                app.request('POST', '/reservations', body)
            for raw in MALFORMED_BODIES.values():
                app.request('POST', '/reservations', raw=raw)
            # When I then make a valid reservation
            status, body = app.request('POST', '/reservations', VALID)
            # Then the process still serves it normally
            self.assertEqual(status, 201)
            self.assertEqual(app.request('GET', '/reservations/' + body['id']), (200, body))
            self.assertIsNone(app.proc.poll(), 'server process must still be running')


if __name__ == '__main__':
    unittest.main()
