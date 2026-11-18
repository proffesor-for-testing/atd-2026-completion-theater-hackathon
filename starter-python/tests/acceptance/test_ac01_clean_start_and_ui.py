import unittest

from tests.support import RunningApp


class AC01CleanStartAndUI(unittest.TestCase):
    def test_ac01_ui_shows_both_seeded_sessions_after_fresh_reset(self):
        # Given a freshly reset app started from source
        with RunningApp() as app:
            # When I open the UI
            status, html = app.request('GET', '/')
            # Then the page lists both seeded sessions (server-rendered, see A-01)
            self.assertEqual(status, 200)
            for text in ('CT-101', 'Catching Ghost Databases', 'CT-102', 'Tests That Can Fail'):
                self.assertIn(text, html)


if __name__ == '__main__':
    unittest.main()
