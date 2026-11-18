"""Spec-gap tests for Session Seat Desk: behaviors in the PRD / API contract that
test_app.py does not assert. Same approach: real app process, real HTTP, real SQLite."""
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
import urllib.error
import urllib.request

from test_app import AppCase, free_port, APP

STATIC_INDEX = Path(APP).parent / 'static' / 'index.html'


def cancel_path(rid):
    return '/reservations/%s/cancel' % rid


class CapacityBoundary(AppCase):
    def test_ct102_boundary_and_isolation_from_ct101(self):
        """AC-04: a 3-seat session fills exactly, rejects the 4th, and does not affect CT-101."""
        for key, alias in (('K1', 'Ada'), ('K2', 'Grace'), ('K3', 'Linus')):
            status, _ = self.reserve('CT-102', alias, key)
            self.assertEqual(status, 201)
        s = self.sessions()['CT-102']
        self.assertEqual((s['remainingSeats'], s['activeCount']), (0, 3))
        self.assertLessEqual(s['activeCount'], s['capacity'])
        self.assertEqual(self.db_counts(), (3, 3))
        self.assert_error(self.reserve('CT-102', 'Margaret', 'K4'))
        self.assertEqual(self.db_counts(), (3, 3))
        s = self.sessions()
        self.assertEqual(s['CT-102']['activeCount'], 3)
        self.assertEqual((s['CT-101']['remainingSeats'], s['CT-101']['activeCount']), (2, 0))
        for rec in s.values():
            for field in ('capacity', 'activeCount', 'remainingSeats'):
                self.assertIs(type(rec[field]), int, (rec['id'], field))
        status, _ = self.reserve('CT-101', 'Ada', 'K5')
        self.assertEqual(status, 201)
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 1)


class CancelReleasesExactlyOne(AppCase):
    def test_cancel_releases_one_seat_and_repeat_releases_nothing(self):
        """AC-06: cancel frees exactly one seat; a repeated cancel is a no-op returning the same record."""
        _, a = self.reserve(alias='Ada', key='K1')
        _, b = self.reserve(alias='Grace', key='K2')
        status, cancelled = self.request('POST', cancel_path(a['id']), {})
        self.assertEqual(status, 200)
        self.assertEqual(cancelled, dict(a, status='cancelled'))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 1)
        self.assertEqual(self.request('GET', '/reservations/' + b['id']), (200, b))
        status, c = self.reserve(alias='Linus', key='K3')
        self.assertEqual(status, 201)
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 0)
        status, again = self.request('POST', cancel_path(a['id']), {})
        self.assertEqual(status, 200)
        self.assertEqual(again, cancelled)
        self.assertEqual(self.request('GET', '/reservations/' + a['id']), (200, again))
        s = self.sessions()['CT-101']
        self.assertEqual((s['remainingSeats'], s['activeCount']), (0, 2))
        self.assert_error(self.reserve(alias='Margaret', key='K4'))
        self.assertEqual(self.db_counts(), (3, 2))


class KeyConflictOnCancelled(AppCase):
    def test_key_of_cancelled_reservation_still_conflicts_or_replays(self):
        """AC-05/AC-06: a cancelled reservation keeps its request key; mismatches conflict, same payload replays."""
        _, first = self.reserve('CT-101', 'Ada', 'K1')
        self.assertEqual(self.request('POST', cancel_path(first['id']), {})[0], 200)
        self.assert_error(self.reserve('CT-102', 'Ada', 'K1'))
        self.assert_error(self.reserve('CT-101', 'Grace', 'K1'))
        self.assertEqual(self.sessions()['CT-102']['activeCount'], 0)
        self.assertEqual(self.db_counts(), (1, 0))
        status, replay = self.reserve('CT-101', 'Ada', 'K1')
        self.assertIn(status, (200, 201))
        self.assertEqual((replay['id'], replay['status']), (first['id'], 'cancelled'))
        self.assertEqual(self.db_counts(), (1, 0))


class ConcurrentSameKey(AppCase):
    def test_ten_simultaneous_identical_requests_make_one_reservation(self):
        """AC-05: concurrent replays of one request key all succeed with one id and one stored row."""
        results = []
        lock = threading.Lock()
        barrier = threading.Barrier(10)

        def attempt():
            barrier.wait()
            out = self.reserve('CT-101', 'Ada', 'K1')
            with lock:
                results.append(out)

        threads = [threading.Thread(target=attempt) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(results), 10)
        for status, body in results:
            self.assertTrue(200 <= status < 300, (status, body))
        self.assertEqual(len({body['id'] for _, body in results}), 1, results)
        self.assertEqual(self.db_counts(), (1, 1))
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 1)


class RestartIdempotency(AppCase):
    def test_restart_keeps_full_records_and_idempotency(self):
        """AC-05/AC-07: after restart without reset, full records, key replays and capacity survive."""
        _, active = self.reserve('CT-101', 'Ada', 'K1')
        _, other = self.reserve('CT-101', 'Grace', 'K2')
        self.assertEqual(self.request('POST', cancel_path(other['id']), {})[0], 200)
        before_a = self.request('GET', '/reservations/' + active['id'])
        before_b = self.request('GET', '/reservations/' + other['id'])
        self.assertEqual(before_b[1]['status'], 'cancelled')
        self.stop()
        self.start()  # no reset
        self.assertEqual(self.request('GET', '/reservations/' + active['id']), before_a)
        self.assertEqual(self.request('GET', '/reservations/' + other['id']), before_b)
        status, replay_a = self.reserve('CT-101', 'Ada', 'K1')
        self.assertIn(status, (200, 201))
        self.assertEqual(replay_a['id'], active['id'])
        status, replay_b = self.reserve('CT-101', 'Grace', 'K2')
        self.assertIn(status, (200, 201))
        self.assertEqual((replay_b['id'], replay_b['status']), (other['id'], 'cancelled'))
        status, _ = self.reserve('CT-101', 'Linus', 'K3')
        self.assertEqual(status, 201)
        self.assertEqual(self.sessions()['CT-101']['remainingSeats'], 0)


class ResetBehavior(AppCase):
    def test_reset_restores_seed_after_use(self):
        """AC-01/AC-02: --reset returns the app to the seed state and forgets old reservations and keys."""
        _, active = self.reserve('CT-101', 'Ada', 'K1')
        _, other = self.reserve('CT-102', 'Grace', 'K2')
        self.assertEqual(self.request('POST', cancel_path(other['id']), {})[0], 200)
        self.stop()
        self.reset()
        self.start()
        s = self.sessions()
        self.assertEqual((s['CT-101']['activeCount'], s['CT-101']['remainingSeats']), (0, 2))
        self.assertEqual((s['CT-102']['activeCount'], s['CT-102']['remainingSeats']), (0, 3))
        self.assertEqual(self.db_counts(), (0, 0))
        self.assert_error(self.request('GET', '/reservations/' + active['id']))
        self.assert_error(self.request('GET', '/reservations/' + other['id']))
        status, fresh = self.reserve('CT-101', 'Ada', 'K1')
        self.assertEqual(status, 201)
        self.assertNotEqual(fresh['id'], active['id'])

    def test_reset_touches_only_its_own_fixture_dir(self):
        """AC-01: --reset on DATA_DIR A leaves a second marked fixture dir B untouched and adds no stray files."""
        with tempfile.TemporaryDirectory() as dir_b:
            env_b = dict(os.environ, DATA_DIR=dir_b, PORT=str(free_port()))
            subprocess.run(AppCase.app_command('--reset'), env=env_b,
                           check=True, capture_output=True, timeout=30)
            proc = subprocess.Popen(AppCase.app_command(), env=env_b,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                port_b = int(env_b['PORT'])
                deadline = time.time() + 10
                while True:
                    self.assertIsNone(proc.poll(), 'second app exited at startup')
                    try:
                        socket.create_connection(('127.0.0.1', port_b), timeout=0.2).close()
                        break
                    except OSError:
                        self.assertLess(time.time(), deadline, 'second app did not start listening')
                        time.sleep(0.05)
                body = json.dumps({'sessionId': 'CT-101', 'attendeeAlias': 'Ada',
                                   'requestKey': 'B1'}).encode()
                req = urllib.request.Request('http://127.0.0.1:%d/reservations' % port_b, data=body,
                                             method='POST', headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    self.assertEqual(resp.status, 201)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                proc.stdout.close()
                proc.stderr.close()
            # Put one reservation into A, then reset A only.
            self.assertEqual(self.reserve('CT-101', 'Grace', 'A1')[0], 201)
            self.stop()
            self.reset()
            with sqlite3.connect(os.path.join(dir_b, 'seats.db')) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0], 1)
            self.assertEqual(self.db_counts(), (0, 0))
            self.assertEqual(sorted(os.listdir(self.data_dir)), ['.fixture-owner', 'seats.db'])


class RejectionsAgainstExistingState(AppCase):
    def test_invalid_requests_leave_existing_reservations_untouched(self):
        """AC-08: invalid input is rejected with 4xx even when state exists, and changes nothing."""
        _, existing = self.reserve('CT-101', 'Ada', 'K1')
        self.assertEqual(self.reserve('CT-102', 'Grace', 'K2')[0], 201)
        good = {'sessionId': 'CT-101', 'attendeeAlias': 'Linus', 'requestKey': 'K9'}
        variants = [
            dict(good, attendeeAlias='\t\n'),
            dict(good, attendeeAlias=None),
            dict(good, sessionId=5),
            dict(good, sessionId=None),
            dict(good, sessionId='ct-101'),
            dict(good, sessionId=' CT-101'),
            dict(good, requestKey=None),
            {'sessionId': 'CT-101', 'attendeeAlias': '   ', 'requestKey': 'K1'},  # validation before replay
        ]
        for payload in variants:
            self.assert_error(self.request('POST', '/reservations', payload))
        self.assert_error(self.request('POST', cancel_path(existing['id']), raw=b'{bad'))
        self.assertEqual(self.request('GET', '/reservations/' + existing['id']), (200, existing))
        self.assertEqual(existing['status'], 'active')
        self.assertEqual(self.db_counts(), (2, 2))
        s = self.sessions()
        self.assertEqual((s['CT-101']['activeCount'], s['CT-102']['activeCount']), (1, 1))
        self.assertIsNone(self.proc.poll())
        self.assertEqual(self.request('GET', '/sessions')[0], 200)


class StartupRefusesForeignStore(unittest.TestCase):
    """The app must not serve a database it does not own: startup applies the same ownership
    marker check as --reset, so a foreign DATA_DIR is never read or written."""

    def start_against(self, data_dir):
        port = free_port()
        proc = subprocess.Popen(AppCase.app_command(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=dict(os.environ, DATA_DIR=data_dir, PORT=str(port)))
        try:
            _, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            self.fail('app kept running against a foreign store instead of refusing')
        return proc.returncode, stderr.decode(), port

    def assert_refused(self, data_dir):
        code, stderr, port = self.start_against(data_dir)
        self.assertNotEqual(code, 0)
        self.assertIn('fixture', stderr)
        with self.assertRaises(OSError):  # nothing is listening
            socket.create_connection(('127.0.0.1', port), timeout=1).close()

    def test_unmarked_existing_database_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            sqlite3.connect(os.path.join(tmp, 'seats.db')).close()  # someone else's db, no marker
            self.assert_refused(tmp)
            self.assertEqual(os.listdir(tmp), ['seats.db'])  # nothing was created or changed

    def test_marker_with_wrong_content_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            sqlite3.connect(os.path.join(tmp, 'seats.db')).close()
            Path(tmp, '.fixture-owner').write_text('some-other-tool')
            self.assert_refused(tmp)


class ClientInputIsNever5xx(AppCase):
    """Contract 'Errors': client-controlled bad input is a 4xx. These two inputs used to crash the
    handler (500 UnicodeEncodeError / RecursionError) although state stayed unchanged."""

    def assert_400_and_nothing_stored(self, status, body):
        self.assertEqual(status, 400, body)
        self.assertTrue(body['error']['message'])
        self.assertEqual(self.db_counts(), (0, 0))
        self.assertIsNone(self.proc.poll())
        self.assertEqual(self.reserve('CT-101', 'Ada', 'K1')[0], 201)  # still serving

    def test_lone_surrogate_in_any_text_field_is_400(self):
        good = {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1'}
        for field in good:
            raw = json.dumps(dict(good, **{field: '\ud83d'})).encode('ascii')  # json escapes it as \ud83d
            status, body = self.request('POST', '/reservations', raw=raw)
            self.assertEqual(status in (400, 404), True, (field, status, body))  # 404 for sessionId: unknown session
            self.assertTrue(body['error'])
        self.assertEqual(self.db_counts(), (0, 0))
        self.assertIsNone(self.proc.poll())
        self.assertEqual(self.reserve('CT-101', 'Ada', 'K1')[0], 201)

    def test_deeply_nested_json_within_size_limit_is_400(self):
        raw = b'{"sessionId":' + b'[' * 30000 + b']' * 30000 + b',"attendeeAlias":"a","requestKey":"q"}'
        self.assertLess(len(raw), 65536)
        self.assert_400_and_nothing_stored(*self.request('POST', '/reservations', raw=raw))

    def test_deeply_nested_json_on_cancel_is_400(self):
        raw = b'{"x":' + b'[' * 30000 + b']' * 30000 + b'}'
        status, body = self.request('POST', '/reservations/abc/cancel', raw=raw)
        self.assertEqual(status, 400, body)
        self.assertIsNone(self.proc.poll())


class ChunkedBodyRejected(AppCase):
    """API contract 'Errors': malformed JSON must reject without changing state. The server only
    frames bodies by Content-Length, so a chunked request is rejected with 411 rather than being
    misread as an empty body (which let a malformed chunked cancel succeed)."""

    def raw_chunked(self, path, chunk):
        request = ('POST %s HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n'
                   'Content-Type: application/json\r\n\r\n%x\r\n%s\r\n0\r\n\r\n'
                   % (path, len(chunk), chunk)).encode()
        with socket.create_connection(('127.0.0.1', self.port), timeout=10) as conn:
            conn.sendall(request)
            reply = b''
            while b'\r\n\r\n' not in reply:
                part = conn.recv(4096)
                if not part:
                    break
                reply += part
            head, _, rest = reply.partition(b'\r\n\r\n')
            while True:  # Content-Length is always sent; read until the connection closes
                part = conn.recv(4096)
                if not part:
                    break
                rest += part
        return int(head.split()[1]), json.loads(rest)

    def test_chunked_cancel_with_malformed_body_is_rejected_and_changes_nothing(self):
        _, rec = self.reserve('CT-101', 'Ada', 'K1')
        status, body = self.raw_chunked(cancel_path(rec['id']), '{bad')
        self.assertEqual(status, 411)
        self.assertTrue(body['error']['message'])
        self.assertEqual(self.request('GET', '/reservations/' + rec['id']), (200, rec))
        self.assertEqual(rec['status'], 'active')
        self.assertEqual(self.db_counts(), (1, 1))

    def test_chunked_requests_are_rejected_even_when_valid_and_server_survives(self):
        _, rec = self.reserve('CT-101', 'Ada', 'K1')
        self.assertEqual(self.raw_chunked(cancel_path(rec['id']), '{}')[0], 411)
        create = '{"sessionId":"CT-102","attendeeAlias":"Grace","requestKey":"K2"}'
        self.assertEqual(self.raw_chunked('/reservations', create)[0], 411)
        self.assertEqual(self.db_counts(), (1, 1))
        self.assertIsNone(self.proc.poll())
        self.assertEqual(self.reserve('CT-102', 'Grace', 'K2')[0], 201)


class ErrorShape(AppCase):
    def assert_error_object(self, status, body):
        err = body.get('error')
        if isinstance(err, str):
            self.assertTrue(err.strip(), (status, body))
        else:
            self.assertIsInstance(err, dict, (status, body))
            for field in ('code', 'message'):
                self.assertIsInstance(err.get(field), str, (status, body))
                self.assertTrue(err[field].strip(), (status, body))

    def test_error_bodies_have_contract_shape(self):
        """api-contract 'Errors': error is a non-empty string or an object with code and message."""
        self.reserve(alias='Ada', key='K1')
        self.reserve(alias='Grace', key='K2')
        cases = [
            (409, self.reserve(alias='Linus', key='K3')),
            (404, self.request('GET', '/reservations/unknown')),
            (400, self.request('POST', '/reservations', raw=b'{bad')),
        ]
        for expected, (status, body) in cases:
            self.assertEqual(status, expected, body)
            self.assert_error_object(status, body)


class JsonContentType(AppCase):
    def fetch(self, method, path, data=None):
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), data=data,
                                     method=method, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, resp.headers.get('Content-Type', '')
        except urllib.error.HTTPError as err:
            err.read()
            return err.code, err.headers.get('Content-Type', '')

    def test_content_types(self):
        """api-contract: API responses (success and error) are application/json; the UI is text/html."""
        good = json.dumps({'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1'}).encode()
        cases = [
            (200, self.fetch('GET', '/sessions')),
            (201, self.fetch('POST', '/reservations', good)),
            (404, self.fetch('GET', '/reservations/unknown')),
            (405, self.fetch('PUT', '/reservations', b'{}')),
            (400, self.fetch('POST', '/reservations', b'{bad')),
        ]
        for expected, (status, ctype) in cases:
            self.assertEqual(status, expected)
            self.assertTrue(ctype.lower().startswith('application/json'), (expected, ctype))
        status, ctype = self.fetch('GET', '/')
        self.assertEqual(status, 200)
        self.assertTrue(ctype.lower().startswith('text/html'), ctype)


def non_loopback_ipv4():
    candidates = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('192.0.2.1', 9))
            candidates.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        candidates.append(socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass
    for ip in candidates:
        if not ip.startswith('127.') and ip != '0.0.0.0':
            return ip
    return None


class LoopbackOnly(AppCase):
    def test_not_reachable_on_non_loopback_address(self):
        """Security posture: the server binds 127.0.0.1 only (PRD / README)."""
        ip = non_loopback_ipv4()
        if ip is None:
            self.skipTest('no non-loopback interface: NOT RUN')
        with self.assertRaises(OSError):
            socket.create_connection((ip, self.port), timeout=2).close()
        socket.create_connection(('127.0.0.1', self.port), timeout=2).close()


class ExitStatusMeta(unittest.TestCase):
    def test_failure_and_skip_are_reported_and_exit_nonzero(self):
        """Test-runner contract: a failing test gives non-zero exit; skips are visible as skipped=N."""
        code = textwrap.dedent('''
            import unittest
            class T(unittest.TestCase):
                def test_fails(self):
                    self.assertEqual(1, 2)
                @unittest.skip('visible skip')
                def test_skipped(self):
                    pass
        ''')
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'meta_module.py').write_text(code)
            result = subprocess.run([sys.executable, '-m', 'unittest', 'meta_module'], cwd=tmp,
                                    capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAILED', result.stderr)
        self.assertIn('skipped=1', result.stderr)


class _UiParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.controls = []
        self.label_for = set()
        self.roles = []
        self.script = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('input', 'select'):
            self.controls.append((tag, a))
        elif tag == 'label' and a.get('for'):
            self.label_for.add(a['for'])
        elif tag == 'script':
            self._in_script = True
        if 'role' in a:
            self.roles.append(a['role'])

    def handle_endtag(self, tag):
        if tag == 'script':
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.script.append(data)


class StaticUiContract(unittest.TestCase):
    def test_index_html_structure(self):
        """STATIC structure check of static/index.html only; NOT browser UI agreement with the API."""
        parser = _UiParser()
        parser.feed(STATIC_INDEX.read_text(encoding='utf-8'))
        self.assertTrue(parser.controls, 'no input/select found')
        for tag, attrs in parser.controls:
            self.assertTrue(attrs.get('id'), '%s without id: %r' % (tag, attrs))
            self.assertIn(attrs['id'], parser.label_for, 'no <label for> for %s#%s' % (tag, attrs['id']))
        self.assertIn('alert', parser.roles)
        script = ''.join(parser.script)
        for needle in ('/sessions', '/reservations', '/cancel'):
            self.assertIn(needle, script)


if __name__ == '__main__':
    unittest.main(verbosity=2)
