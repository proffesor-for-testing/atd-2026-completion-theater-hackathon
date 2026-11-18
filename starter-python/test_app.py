"""Behavioral HTTP/store/process tests for Session Seat Desk (Python 3.11+).

Every test owns a disposable fixture outside source. Browser accessibility and
visual UI agreement are separate executed checks; this suite does not claim them.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

APP = Path(__file__).resolve().with_name("app.py")
EXPECTED_SESSIONS = [
    {"id": "CT-101", "title": "Catching Ghost Databases", "capacity": 2,
     "activeCount": 0, "remainingSeats": 2},
    {"id": "CT-102", "title": "Tests That Can Fail", "capacity": 3,
     "activeCount": 0, "remainingSeats": 3},
]


def fixture_environment(state):
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
               "HOME", "USERPROFILE", "LANG", "LC_ALL"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(PORT="0", DATA_DIR=str(state), PYTHONDONTWRITEBYTECODE="1",
               PYTHONIOENCODING="utf-8")
    return env


class FixtureServer:
    def __init__(self, root, trace_dir=None):
        self.root = Path(root)
        self.state = self.root / "fixture state ü"
        self.env = fixture_environment(self.state)
        self.process = None
        self.reader = None
        self.log = None
        self.base = None
        self.trace_dir = Path(trace_dir) if trace_dir is not None else None
        if self.trace_dir is not None:
            if self.trace_dir.resolve().is_relative_to(APP.parent.resolve()):
                raise ValueError("Test receipts must stay outside the app source")
            self.trace_dir.mkdir(parents=True, exist_ok=False)

    def record(self, kind, **value):
        if self.trace_dir is not None:
            value.update(kind=kind, timestamp=datetime.now(timezone.utc).isoformat())
            with (self.trace_dir / "trace.jsonl").open("a", encoding="utf-8") as receipt:
                receipt.write(json.dumps(value, ensure_ascii=True) + "\n")

    def reset(self, env=None):
        command = [sys.executable, "-B", str(APP), "--reset"]
        selected_env = self.env if env is None else env
        completed = subprocess.run(
            command, cwd=APP.parent,
            env=selected_env, text=True, encoding="utf-8",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10,
            check=False)
        self.record("fixture-reset", command=command, cwd=str(APP.parent),
                    statePath=selected_env["DATA_DIR"], exitCode=completed.returncode,
                    stdoutStderr=completed.stdout)
        return completed

    def start(self):
        if self.process is not None:
            raise RuntimeError("Server already started")
        self.log = (self.root / "server.log").open("a", encoding="utf-8")
        ready = queue.Queue()
        self.process = subprocess.Popen(
            [sys.executable, "-B", str(APP)], cwd=APP.parent, env=self.env,
            text=True, encoding="utf-8", stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)

        def read_output():
            for line in self.process.stdout:
                self.log.write(line)
                self.log.flush()
                match = re.search(r"http://127\.0\.0\.1:(\d+)", line)
                if match:
                    ready.put("http://127.0.0.1:" + match.group(1))

        self.reader = threading.Thread(target=read_output, daemon=True)
        self.reader.start()
        try:
            self.base = ready.get(timeout=8)
            self.record("process-start", pid=self.process.pid, url=self.base,
                        statePath=str(self.state))
        except queue.Empty:
            detail = (self.root / "server.log").read_text(encoding="utf-8")
            self.stop()
            raise AssertionError("Server did not announce readiness:\n" + detail)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                if self.request("GET", "/sessions")[0] == 200:
                    return
            except OSError:
                pass
            time.sleep(0.02)
        raise AssertionError("Server announced URL but /sessions was unavailable")

    def stop(self):
        if self.process is None:
            return None
        process = self.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if self.reader is not None:
            self.reader.join(timeout=2)
        if process.stdout is not None:
            process.stdout.close()
        if self.log is not None:
            self.log.close()
        result = {"pid": process.pid, "exitCode": process.returncode}
        self.record("process-stop", **result)
        if self.trace_dir is not None:
            (self.trace_dir / "server.log").write_bytes((self.root / "server.log").read_bytes())
        self.process = None
        return result

    def request(self, method, path, payload=None, raw=None):
        body = raw
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        request = Request(self.base + path, data=body, method=method,
                          headers={"Content-Type": "application/json"})
        opener = build_opener(ProxyHandler({}))
        try:
            response = opener.open(request, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            raw_response = response.read()
            self.record("http", method=method, path=path, status=response.status,
                        requestBody=None if body is None else body.decode("utf-8", errors="backslashreplace"),
                        rawRequestHex=None if body is None else body.hex(),
                        rawResponseText=raw_response.decode("utf-8", errors="replace"),
                        rawResponseHex=raw_response.hex())
            value = json.loads(raw_response.decode("utf-8"))
            self.record("parsed-json", method=method, path=path, status=response.status,
                        responseBody=value)
            return response.status, value

    def store(self):
        with closing(sqlite3.connect(self.state / "seats.db")) as connection:
            snapshot = {
                "sessions": connection.execute(
                    "SELECT id,title,capacity FROM sessions ORDER BY id").fetchall(),
                "reservations": connection.execute(
                    "SELECT id,session_id,attendee_alias,request_key,status "
                    "FROM reservations ORDER BY id").fetchall(),
            }
        self.record("sqlite-readback", statePath=str(self.state / "seats.db"), rows=snapshot)
        return snapshot


class RequiredBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="seat desk tests ü ")
        self.addCleanup(self.temp.cleanup)
        receipts = os.environ.get("SEAT_DESK_TEST_RECEIPTS")
        trace_dir = Path(receipts) / self._testMethodName if receipts else None
        self.server = FixtureServer(self.temp.name, trace_dir=trace_dir)
        self.addCleanup(self.server.stop)
        reset = self.server.reset()
        self.assertEqual(reset.returncode, 0, reset.stdout)
        self.server.start()

    def create(self, key="K1", alias="Ada", session="CT-101"):
        status, record = self.server.request("POST", "/reservations", {
            "sessionId": session, "attendeeAlias": alias, "requestKey": key})
        self.assertGreaterEqual(status, 200, record)
        self.assertLess(status, 300, record)
        return record

    def counts(self):
        status, payload = self.server.request("GET", "/sessions")
        self.assertEqual(status, 200, payload)
        return {row["id"]: row for row in payload["sessions"]}

    def assert_record_readback(self, record):
        expected = (record["id"], record["sessionId"], record["attendeeAlias"],
                    record["requestKey"], record["status"])
        self.assertIn(expected, self.server.store()["reservations"])
        self.assertEqual(self.server.request("GET", "/reservations/" + record["id"]),
                         (200, record))
        return expected

    def assert_rejected_unchanged(self, method, path, payload=None, raw=None):
        before_store = self.server.store()
        before_counts = self.counts()
        status, error = self.server.request(method, path, payload=payload, raw=raw)
        self.assertGreaterEqual(status, 400, error)
        self.assertLess(status, 500, error)
        self.assertTrue(error.get("error"), error)
        self.assertEqual(self.server.store(), before_store)
        self.assertEqual(self.counts(), before_counts)

    def concurrent(self, payloads):
        barrier = threading.Barrier(len(payloads))

        def send(payload):
            barrier.wait(timeout=10)
            return self.server.request("POST", "/reservations", payload)

        with ThreadPoolExecutor(max_workers=len(payloads)) as pool:
            return list(pool.map(send, payloads))

    def test_exact_seed_sessions_and_integer_counts(self):
        status, payload = self.server.request("GET", "/sessions")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"sessions": EXPECTED_SESSIONS})
        self.assertEqual(self.server.store()["reservations"], [])
        self.assertEqual(self.server.store()["sessions"], [
            ("CT-101", "Catching Ghost Databases", 2),
            ("CT-102", "Tests That Can Fail", 3)])
        for row in payload["sessions"]:
            for field in ("capacity", "activeCount", "remainingSeats"):
                self.assertIs(type(row[field]), int)

    def test_ui_page_is_served_without_external_service(self):
        with build_opener(ProxyHandler({})).open(self.server.base + "/", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/html", response.headers["Content-Type"])
            self.assertIn("Session Seat Desk", response.read().decode("utf-8"))

    def test_create_has_stable_http_and_independent_store_readback(self):
        created = self.create()
        self.assertIsInstance(created["id"], str)
        self.assertTrue(created["id"])
        self.assertEqual({k: v for k, v in created.items() if k != "id"}, {
            "sessionId": "CT-101", "attendeeAlias": "Ada",
            "requestKey": "K1", "status": "active"})
        status, stored = self.server.request("GET", "/reservations/" + created["id"])
        self.assertEqual(status, 200)
        self.assertEqual(stored, created)
        self.assertEqual(self.server.store()["reservations"], [
            (created["id"], "CT-101", "Ada", "K1", "active")])
        self.assertEqual(self.counts()["CT-101"]["remainingSeats"], 1)

    def test_capacity_rejects_third_request_without_any_new_row(self):
        self.create("K1", "Ada")
        self.create("K2", "Bea")
        self.assert_rejected_unchanged("POST", "/reservations", {
            "sessionId": "CT-101", "attendeeAlias": "Cy", "requestKey": "K3"})
        self.assertEqual(len(self.server.store()["reservations"]), 2)
        self.assertEqual(self.counts()["CT-101"]["activeCount"], 2)
        self.assertEqual(self.counts()["CT-101"]["remainingSeats"], 0)

    def test_simultaneous_last_seat_has_exactly_one_winner(self):
        seed = self.create("seed")
        seed_row = self.assert_record_readback(seed)
        payloads = [{"sessionId": "CT-101", "attendeeAlias": "Racer " + str(i),
                     "requestKey": "race-" + str(i)} for i in range(10)]
        results = self.concurrent(payloads)
        self.assertEqual(sum(200 <= status < 300 for status, _ in results), 1, results)
        for status, value in results:
            if not 200 <= status < 300:
                self.assertTrue(400 <= status < 500, value)
                self.assertTrue(value.get("error"), value)
        self.assertEqual(len(self.server.store()["reservations"]), 2)
        winner = next(value for status, value in results if 200 <= status < 300)
        winner_row = self.assert_record_readback(winner)
        self.assertEqual(self.server.store()["reservations"], sorted([seed_row, winner_row]))
        loser_keys = {payload["requestKey"] for payload in payloads} - {winner["requestKey"]}
        self.assertFalse(loser_keys & {row[3] for row in self.server.store()["reservations"]})
        self.assertEqual(self.counts()["CT-101"]["activeCount"], 2)
        self.assertEqual(self.counts()["CT-101"]["remainingSeats"], 0)

    def test_concurrent_identical_key_is_one_stored_record(self):
        payload = {"sessionId": "CT-101", "attendeeAlias": "Ada", "requestKey": "same"}
        results = self.concurrent([payload] * 10)
        self.assertTrue(all(200 <= status < 300 for status, _ in results), results)
        self.assertEqual(len({value["id"] for _, value in results}), 1)
        self.assertEqual(len(self.server.store()["reservations"]), 1)
        row = self.assert_record_readback(results[0][1])
        self.assertEqual(self.server.store()["reservations"], [row])
        self.assertEqual(self.counts()["CT-101"]["activeCount"], 1)

    def test_concurrent_conflicting_global_key_has_one_winner(self):
        payloads = [{"sessionId": "CT-101" if i % 2 else "CT-102",
                     "attendeeAlias": "Alias " + str(i), "requestKey": "one-global-key"}
                    for i in range(10)]
        results = self.concurrent(payloads)
        self.assertEqual(sum(200 <= status < 300 for status, _ in results), 1, results)
        for status, value in results:
            if not 200 <= status < 300:
                self.assertEqual(status, 409, value)
                self.assertTrue(value.get("error"), value)
        self.assertEqual(len(self.server.store()["reservations"]), 1)
        winner = next(value for status, value in results if 200 <= status < 300)
        row = self.assert_record_readback(winner)
        self.assertEqual(self.server.store()["reservations"], [row])
        self.assertIn({key: winner[key] for key in ("sessionId", "attendeeAlias", "requestKey")}, payloads)
        self.assertEqual(sum(row["activeCount"] for row in self.counts().values()), 1)

    def test_trimmed_replay_works_when_full_and_global_conflicts_do_not_mutate(self):
        original = self.create()
        self.create("K2", "Bea")
        before = self.server.store()
        replay = self.create("K1", " Ada ")
        self.assertEqual(replay, original)
        self.assertEqual(self.server.store(), before)
        for session, alias in (("CT-101", "Other"), ("CT-102", "Ada"),
                               ("CT-101", "ada")):
            with self.subTest(session=session, alias=alias):
                self.assert_rejected_unchanged("POST", "/reservations", {
                    "sessionId": session, "attendeeAlias": alias, "requestKey": "K1"})

    def test_cancel_once_repeat_and_cancelled_replay_after_refill(self):
        original = self.create()
        path = "/reservations/" + original["id"] + "/cancel"
        status, cancelled = self.server.request("POST", path, {})
        self.assertEqual(status, 200)
        self.assertEqual(cancelled["id"], original["id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.counts()["CT-101"]["remainingSeats"], 2)
        before = self.server.store()
        self.assertEqual(self.server.request("POST", path, {}), (200, cancelled))
        self.assertEqual(self.server.store(), before)
        self.create("K2", "Bea")
        self.create("K3", "Cy")
        before = self.server.store()
        self.assertEqual(self.create(), cancelled)
        self.assertEqual(self.server.store(), before)
        self.assertEqual(self.counts()["CT-101"]["activeCount"], 2)
        self.assertEqual(self.counts()["CT-101"]["remainingSeats"], 0)

    def test_new_key_after_cancel_creates_distinct_record(self):
        old = self.create()
        self.server.request("POST", "/reservations/" + old["id"] + "/cancel", {})
        new = self.create("K2")
        self.assertNotEqual(old["id"], new["id"])
        self.assertEqual(len(self.server.store()["reservations"]), 2)
        self.assertEqual(self.counts()["CT-101"]["activeCount"], 1)

    def test_all_five_invalid_cases_leave_full_state_unchanged_and_service_available(self):
        cancelled = self.create()
        self.server.request("POST", "/reservations/" + cancelled["id"] + "/cancel", {})
        self.create("active", "Bea")
        cases = [
            ("unknown session", "POST", "/reservations",
             {"sessionId": "CT-999", "attendeeAlias": "Cy", "requestKey": "bad-session"}, None),
            ("blank alias", "POST", "/reservations",
             {"sessionId": "CT-101", "attendeeAlias": " \t ", "requestKey": "bad-alias"}, None),
            ("missing key", "POST", "/reservations",
             {"sessionId": "CT-101", "attendeeAlias": "Cy"}, None),
            ("malformed JSON", "POST", "/reservations", None, b'{"sessionId":'),
            ("unknown cancellation", "POST", "/reservations/unknown/cancel", {}, None),
        ]
        for name, method, path, payload, raw in cases:
            with self.subTest(case=name):
                self.assert_rejected_unchanged(method, path, payload, raw)

    def test_nonstandard_constants_and_nonobject_json_never_mutate(self):
        self.create()
        bodies = [b"[]", b"null", b"1", b'"text"', b"\xff"]
        for constant in ("NaN", "Infinity", "-Infinity"):
            bodies.append(('{"sessionId":"CT-101","attendeeAlias":"Bea",'
                           '"requestKey":"bad-json","extra":' + constant + "}").encode("utf-8"))
        for body in bodies:
            with self.subTest(body=body):
                self.assert_rejected_unchanged("POST", "/reservations", raw=body)

    def test_key_and_alias_types_reject_and_nonempty_keys_are_preserved(self):
        for key in ("", None, 7, True, []):
            with self.subTest(key=key):
                self.assert_rejected_unchanged("POST", "/reservations", {
                    "sessionId": "CT-101", "attendeeAlias": "Ada", "requestKey": key})
        for alias in ("", None, 7, True, []):
            with self.subTest(alias=alias):
                self.assert_rejected_unchanged("POST", "/reservations", {
                    "sessionId": "CT-101", "attendeeAlias": alias, "requestKey": "invalid-alias"})
        spaced = self.create(" key ", " Ada ", "CT-102")
        plain = self.create("key", "Ada", "CT-102")
        self.assertEqual(spaced["requestKey"], " key ")
        self.assertEqual(spaced["attendeeAlias"], "Ada")
        self.assertNotEqual(spaced["id"], plain["id"])

    def test_unknown_read_is_clear_4xx_without_mutation(self):
        self.create()
        self.assert_rejected_unchanged("GET", "/reservations/unknown")

    def test_actual_process_restart_preserves_active_cancelled_and_global_key(self):
        cancelled = self.create()
        active = self.create("K2", "Bea")
        self.server.request("POST", "/reservations/" + cancelled["id"] + "/cancel", {})
        before_store, before_counts = self.server.store(), self.counts()
        old_pid = self.server.process.pid
        stopped = self.server.stop()
        self.assertEqual(stopped["pid"], old_pid)
        self.assertIsNotNone(stopped["exitCode"])
        self.server.start()  # same DATA_DIR, explicitly no reset
        self.assertNotEqual(self.server.process.pid, old_pid)
        self.assertEqual(self.server.store(), before_store)
        self.assertEqual(self.counts(), before_counts)
        self.assertEqual(self.server.request("GET", "/reservations/" + active["id"]), (200, active))
        status, stored = self.server.request("GET", "/reservations/" + cancelled["id"])
        self.assertEqual(status, 200)
        self.assertEqual(stored["status"], "cancelled")
        self.assertEqual(self.create(), stored)
        self.assert_rejected_unchanged("POST", "/reservations", {
            "sessionId": "CT-102", "attendeeAlias": "Ada", "requestKey": "K1"})

    def test_reset_refuses_unmarked_or_foreign_owned_database(self):
        for marked in (False, True):
            with self.subTest(marked=marked):
                directory = Path(self.temp.name) / ("foreign marked" if marked else "unmarked")
                directory.mkdir()
                db = directory / "seats.db"
                with closing(sqlite3.connect(db)) as connection:
                    connection.execute("CREATE TABLE fixture_sentinel(value TEXT)")
                    connection.execute("INSERT INTO fixture_sentinel VALUES ('untouched')")
                    connection.commit()
                if marked:
                    (directory / ".fixture-owner").write_text("another-fixture", encoding="utf-8")
                before = db.read_bytes()
                result = self.server.reset(fixture_environment(directory))
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(db.read_bytes(), before)
                if not marked:
                    self.assertFalse((directory / ".fixture-owner").exists())

    def test_start_without_reset_does_not_create_or_reset_fixture(self):
        directory = Path(self.temp.name) / "not initialized"
        result = subprocess.run(
            [sys.executable, "-B", str(APP)], cwd=APP.parent,
            env=fixture_environment(directory), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            timeout=5, check=False)
        self.server.record("startup-without-reset", command=[sys.executable, "-B", str(APP)],
                           cwd=str(APP.parent), statePath=str(directory),
                           exitCode=result.returncode, stdoutStderr=result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse((directory / "seats.db").exists())

    def test_explicit_reset_isolated_and_reseeds_exact_sessions(self):
        other = Path(self.temp.name) / "unrelated fixture.txt"
        other.write_text("untouched", encoding="utf-8")
        self.create()
        self.assertTrue(self.server.state.is_relative_to(Path(self.temp.name)))
        self.assertNotEqual(self.server.base.rsplit(":", 1)[1], "0")
        self.server.stop()
        reset = self.server.reset()
        self.assertEqual(reset.returncode, 0, reset.stdout)
        self.server.start()
        self.assertEqual(other.read_text(encoding="utf-8"), "untouched")
        self.assertEqual(self.server.store()["reservations"], [])
        self.assertEqual(self.server.request("GET", "/sessions"), (200, {"sessions": EXPECTED_SESSIONS}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
