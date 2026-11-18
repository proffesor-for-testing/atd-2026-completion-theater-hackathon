import unittest

from tests.support import RunningApp, table_rows

FRESH = [
    {'id': 'CT-101', 'title': 'Catching Ghost Databases', 'capacity': 2, 'activeCount': 0, 'remainingSeats': 2},
    {'id': 'CT-102', 'title': 'Tests That Can Fail', 'capacity': 3, 'activeCount': 0, 'remainingSeats': 3},
]


class AC02SessionReadback(unittest.TestCase):
    def test_ac02_get_sessions_returns_seeded_counts_after_fresh_reset(self):
        # Given a freshly reset app
        with RunningApp() as app:
            # When I read the sessions
            status, body = app.request('GET', '/sessions')
            # Then both sessions come back with integer counts per the contract
            self.assertEqual(status, 200)
            self.assertEqual(body, {'sessions': FRESH})

    def test_ac02_ui_shows_the_same_numbers_as_the_api(self):
        # Given a freshly reset app
        with RunningApp() as app:
            # When I read the API and open the UI
            api_status, body = app.request('GET', '/sessions')
            self.assertEqual(api_status, 200)
            status, html = app.request('GET', '/')
            # Then the UI sessions table matches the API row for row
            self.assertEqual(status, 200)
            expected = [[s['id'], s['title'], str(s['capacity']), str(s['activeCount']),
                         str(s['remainingSeats'])] for s in body['sessions']]
            rows = table_rows(html, 'sessions')
            self.assertEqual(rows[1:], expected)  # rows[0] is the header


if __name__ == '__main__':
    unittest.main()
