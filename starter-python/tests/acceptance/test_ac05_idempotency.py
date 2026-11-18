import unittest

from tests.support import RunningApp

ADA_K1 = {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1'}


class AC05aReplay(unittest.TestCase):
    def test_ac05_replay_same_key_returns_original_id_without_using_a_seat(self):
        # Given Ada has reserved CT-101 with K1
        with RunningApp() as app:
            status, original = app.request('POST', '/reservations', ADA_K1)
            self.assertEqual(status, 201)
            # When the identical request is sent again
            status, replay = app.request('POST', '/reservations', ADA_K1)
            # Then it returns the original record (2xx, same ID, current status) and no seat is used
            self.assertEqual(status, 200)
            self.assertEqual(replay, original)
            _, body = app.request('GET', '/sessions')
            self.assertEqual(body['sessions'][0]['activeCount'], 1)
            self.assertEqual(app.stored_reservation_count(), 1)

    def test_ac05_replay_matches_on_trimmed_alias(self):
        # Given Ada has reserved CT-101 with K1
        with RunningApp() as app:
            _, original = app.request('POST', '/reservations', ADA_K1)
            # When the same key is replayed with surrounding whitespace on the alias
            status, replay = app.request('POST', '/reservations', {**ADA_K1, 'attendeeAlias': '  Ada \t'})
            # Then it is the same reservation, not a conflict and not a new seat
            self.assertEqual((status, replay), (200, original))
            self.assertEqual(app.stored_reservation_count(), 1)


class AC05bKeyConflict(unittest.TestCase):
    CONFLICTS = {
        'different alias': {**ADA_K1, 'attendeeAlias': 'Grace'},
        'alias differs only by case': {**ADA_K1, 'attendeeAlias': 'ada'},
        'different session (keys are global)': {**ADA_K1, 'sessionId': 'CT-102'},
        'different session and alias': {'sessionId': 'CT-102', 'attendeeAlias': 'Grace', 'requestKey': 'K1'},
    }

    def test_ac05_reused_key_with_different_session_or_alias_conflicts_without_state_change(self):
        # Given Ada has reserved CT-101 with K1
        with RunningApp() as app:
            _, original = app.request('POST', '/reservations', ADA_K1)
            for name, body in self.CONFLICTS.items():
                with self.subTest(name):
                    sessions_before = app.request('GET', '/sessions')
                    # When K1 is reused for a different session or alias
                    status, response = app.request('POST', '/reservations', body)
                    # Then it is a 409 conflict with an error, and nothing changed
                    self.assertEqual(status, 409, response)
                    self.assertTrue(response.get('error'))
                    self.assertEqual(app.request('GET', '/sessions'), sessions_before)
                    self.assertEqual(app.stored_reservation_count(), 1)
            # And the original reservation is untouched
            self.assertEqual(app.request('GET', '/reservations/' + original['id']), (200, original))


if __name__ == '__main__':
    unittest.main()
