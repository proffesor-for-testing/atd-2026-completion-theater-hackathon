import unittest

from tests.support import RunningApp, table_rows


class AC07DurableState(unittest.TestCase):
    def test_ac07_active_and_cancelled_reservations_survive_process_restart_without_reset(self):
        # Given one active and one cancelled reservation
        with RunningApp() as app:
            status, active = app.request('POST', '/reservations',
                                         {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1'})
            self.assertEqual(status, 201, active)
            status, other = app.request('POST', '/reservations',
                                        {'sessionId': 'CT-102', 'attendeeAlias': 'Grace', 'requestKey': 'K2'})
            self.assertEqual(status, 201, other)
            status, cancelled = app.request('POST', '/reservations/%s/cancel' % other['id'], {})
            self.assertEqual((status, cancelled['status']), (200, 'cancelled'))
            sessions_before = app.request('GET', '/sessions')
            ui_before = table_rows(app.request('GET', '/')[1], 'sessions')
            first_pid = app.proc.pid

            # When the process is stopped and started again WITHOUT --reset
            app.stop()
            app.start()
            self.assertNotEqual(app.proc.pid, first_pid, 'must be a real new process, not a refresh')

            # Then fresh HTTP requests and the UI show the same IDs, statuses and counts
            self.assertEqual(app.request('GET', '/reservations/' + active['id']), (200, active))
            self.assertEqual(app.request('GET', '/reservations/' + cancelled['id']), (200, cancelled))
            self.assertEqual(app.request('GET', '/sessions'), sessions_before)
            counts = {s['id']: (s['activeCount'], s['remainingSeats']) for s in sessions_before[1]['sessions']}
            self.assertEqual(counts, {'CT-101': (1, 1), 'CT-102': (0, 3)})
            self.assertEqual(table_rows(app.request('GET', '/')[1], 'sessions'), ui_before)
            # And replaying the cancelled request after restart still does not reactivate it
            replay = app.request('POST', '/reservations',
                                 {'sessionId': 'CT-102', 'attendeeAlias': 'Grace', 'requestKey': 'K2'})
            self.assertEqual(replay, (200, cancelled))
            self.assertEqual(app.stored_reservation_count(), 2)


if __name__ == '__main__':
    unittest.main()
