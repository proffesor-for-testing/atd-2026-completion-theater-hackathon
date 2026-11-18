#!/usr/bin/env python3
"""Black-box acceptance tests for the Session Seat Desk (AC-02 .. AC-08).

Stdlib only. Every test gets its own server subprocess on a free port with a
fresh temporary DATA_DIR (reset first). Run:  python3 -m unittest test_acceptance -v
"""
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app.py")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServerCase(unittest.TestCase):
    """Base class: one fresh server (reset) per test."""

    def setUp(self):
        self.data_dir = tempfile.mkdtemp(prefix="seatdesk-")
        self.proc = None
        self.port = None
        self.reset()
        self.start()

    def tearDown(self):
        self.stop()
        shutil.rmtree(self.data_dir, ignore_errors=True)

    # ----- process control -------------------------------------------------
    def _env(self, port=None):
        env = dict(os.environ)
        env["DATA_DIR"] = self.data_dir
        if port is not None:
            env["PORT"] = str(port)
        return env

    def reset(self):
        r = subprocess.run(
            [sys.executable, APP, "--reset"], cwd=HERE, env=self._env(),
            capture_output=True, timeout=20,
        )
        self.assertEqual(r.returncode, 0, "reset failed: %r" % r.stderr[-500:])

    def start(self):
        self.port = free_port()
        self.proc = subprocess.Popen(
            [sys.executable, APP], cwd=HERE, env=self._env(self.port),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 15
        while time.time() < deadline:
            if self.proc.poll() is not None:
                self.fail("server exited early with code %s" % self.proc.returncode)
            try:
                st, _ = self.req("GET", "/sessions", timeout=1)
                if st == 200:
                    return
            except Exception:
                pass
            time.sleep(0.05)
        self.fail("server did not become ready")

    def stop(self):
        p, self.proc = self.proc, None
        if p is None:
            return
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=5)

    def restart_fresh(self):
        self.stop()
        self.reset()
        self.start()

    # ----- HTTP helpers ----------------------------------------------------
    def req(self, method, path, body=None, raw=None, timeout=10):
        """Return (status, parsed_json_or_None)."""
        data = None
        if raw is not None:
            data = raw
        elif body is not None:
            data = json.dumps(body).encode()
        r = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.port, path), data=data, method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                status, text = resp.status, resp.read()
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read()
        try:
            parsed = json.loads(text.decode("utf-8")) if text else None
        except ValueError:
            parsed = None
        return status, parsed

    def reserve(self, session="CT-101", alias="Ada", key="K1"):
        return self.req("POST", "/reservations",
                        {"sessionId": session, "attendeeAlias": alias, "requestKey": key})

    def reserve_ok(self, session="CT-101", alias="Ada", key="K1"):
        st, body = self.reserve(session, alias, key)
        self.assertTrue(200 <= st < 300, "expected 2xx, got %s %r" % (st, body))
        self.assertIsInstance(body, dict)
        return body

    def cancel(self, rid):
        return self.req("POST", "/reservations/%s/cancel" % rid, {})

    def sessions(self):
        st, body = self.req("GET", "/sessions")
        self.assertEqual(st, 200)
        self.assertIn("sessions", body)
        return {s["id"]: s for s in body["sessions"]}

    def counts(self):
        s = self.sessions()
        return {k: (v["activeCount"], v["remainingSeats"]) for k, v in s.items()}

    # ----- assertion helpers ----------------------------------------------
    def assert_2xx(self, st, body=None):
        self.assertTrue(200 <= st < 300, "expected 2xx, got %s %r" % (st, body))

    def assert_rejected(self, st, body):
        self.assertTrue(400 <= st < 500, "expected 4xx, got %s %r" % (st, body))
        self.assertIsInstance(body, dict, "error body must be a JSON object")
        err = body.get("error")
        self.assertTrue(err, "missing/empty error in %r" % (body,))
        if isinstance(err, dict):
            self.assertTrue(err.get("message") or err.get("code"), "empty error object %r" % (err,))

    def assert_record(self, rec, session, alias, key, status, rid=None):
        self.assertIsInstance(rec, dict)
        self.assertTrue(isinstance(rec.get("id"), str) and rec["id"], "id missing: %r" % (rec,))
        if rid is not None:
            self.assertEqual(rec["id"], rid)
        self.assertEqual(rec.get("sessionId"), session)
        self.assertEqual(rec.get("attendeeAlias"), alias)
        self.assertEqual(rec.get("requestKey"), key)
        self.assertEqual(rec.get("status"), status)

    # ----- sqlite independent readback ------------------------------------
    def db_rows(self):
        """Return list of dict rows from the reservations table in seats.db."""
        path = os.path.join(self.data_dir, "seats.db")
        self.assertTrue(os.path.exists(path), "seats.db not found in DATA_DIR")
        con = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        try:
            con.row_factory = sqlite3.Row
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            cands = [t for t in tables if "reserv" in t.lower()]
            self.assertTrue(cands, "no reservation table among %r" % tables)
            table = cands[0]
            return [dict(r) for r in con.execute('SELECT * FROM "%s"' % table)]
        finally:
            con.close()

    def db_statuses(self):
        rows = self.db_rows()
        for r in rows:
            self.assertIn("status", r, "no status column in %r" % (r,))
        return sorted(r["status"] for r in rows)


class TestAc02Sessions(ServerCase):
    def test_ac02_seeded_counts(self):
        st, body = self.req("GET", "/sessions")
        self.assertEqual(st, 200)
        self.assertEqual(set(body.keys()), {"sessions"})
        by_id = {s["id"]: s for s in body["sessions"]}
        self.assertEqual(set(by_id), {"CT-101", "CT-102"})
        self.assertEqual(len(body["sessions"]), 2)
        a, b = by_id["CT-101"], by_id["CT-102"]
        self.assertEqual(a["title"], "Catching Ghost Databases")
        self.assertEqual(b["title"], "Tests That Can Fail")
        for s, cap in ((a, 2), (b, 3)):
            self.assertEqual(type(s["capacity"]), int)
            self.assertEqual(type(s["activeCount"]), int)
            self.assertEqual(type(s["remainingSeats"]), int)
            self.assertEqual(s["capacity"], cap)
            self.assertEqual(s["activeCount"], 0)
            self.assertEqual(s["remainingSeats"], cap)


class TestAc03Reserve(ServerCase):
    def test_ac03_reserve_and_readback_equal(self):
        rec = self.reserve_ok("CT-101", "Ada", "K1")
        self.assert_record(rec, "CT-101", "Ada", "K1", "active")
        st, got = self.req("GET", "/reservations/%s" % rec["id"])
        self.assertEqual(st, 200)
        self.assertEqual(got, rec)
        c = self.sessions()["CT-101"]
        self.assertEqual((c["activeCount"], c["remainingSeats"]), (1, 1))
        self.assertEqual(self.counts()["CT-102"], (0, 3))

    def test_ac03_ids_are_distinct_per_reservation(self):
        a = self.reserve_ok("CT-101", "Ada", "K1")
        b = self.reserve_ok("CT-101", "Grace", "K2")
        self.assertNotEqual(a["id"], b["id"])


class TestAc04Capacity(ServerCase):
    def test_ac04_sequential_capacity_rejection(self):
        self.reserve_ok("CT-101", "Ada", "K1")
        self.reserve_ok("CT-101", "Grace", "K2")
        self.assertEqual(self.counts()["CT-101"], (2, 0))
        st, body = self.reserve("CT-101", "Linus", "K3")
        self.assert_rejected(st, body)
        self.assertEqual(self.counts()["CT-101"], (2, 0))
        self.assertEqual(self.counts()["CT-102"], (0, 3))
        # other session still bookable
        self.reserve_ok("CT-102", "Linus", "K4")
        self.assertEqual(self.counts()["CT-102"], (1, 2))

    def test_ac04_race_one_seat_left_five_batches(self):
        n = 10
        for batch in range(5):
            if batch:
                self.restart_fresh()
            self.reserve_ok("CT-101", "Seed", "seed-%d" % batch)
            self.assertEqual(self.counts()["CT-101"], (1, 1))
            barrier = threading.Barrier(n)
            results = [None] * n

            def worker(i, batch=batch, barrier=barrier, results=results):
                try:
                    barrier.wait(timeout=10)
                    results[i] = self.reserve("CT-101", "Racer%d" % i, "race-%d-%d" % (batch, i))
                except Exception as e:  # noqa
                    results[i] = ("exc", repr(e))

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30)
            for r in results:
                self.assertIsNotNone(r, "worker did not finish")
                self.assertNotEqual(r[0], "exc", r)
            ok = [r for r in results if 200 <= r[0] < 300]
            bad = [r for r in results if 400 <= r[0] < 500]
            self.assertEqual(len(ok), 1, "batch %d results %r" % (batch, results))
            self.assertEqual(len(bad), 9, "batch %d results %r" % (batch, results))
            for st, body in bad:
                self.assert_rejected(st, body)
            self.assertEqual(self.counts()["CT-101"], (2, 0), "batch %d" % batch)
            self.assertEqual(self.db_statuses(), ["active", "active"], "batch %d" % batch)


class TestAc05Idempotency(ServerCase):
    def test_ac05_replay_same_id(self):
        first = self.reserve_ok("CT-101", "Ada", "K1")
        again = self.reserve_ok("CT-101", "Ada", "K1")
        self.assertEqual(again, first)
        self.assertEqual(self.counts()["CT-101"], (1, 1))
        self.assertEqual(len(self.db_rows()), 1)

    def test_ac05_replay_with_padded_alias_trimmed(self):
        first = self.reserve_ok("CT-101", "Ada", "K1")
        again = self.reserve_ok("CT-101", " Ada ", "K1")
        self.assertEqual(again["id"], first["id"])
        self.assertEqual(again["attendeeAlias"], "Ada")
        self.assertEqual(again, first)
        self.assertEqual(self.counts()["CT-101"], (1, 1))

    def test_ac05_new_request_with_padded_alias_stored_trimmed(self):
        rec = self.reserve_ok("CT-101", "  Grace\t", "K9")
        self.assertEqual(rec["attendeeAlias"], "Grace")

    def test_ac05_key_reuse_different_alias_rejected(self):
        self.reserve_ok("CT-101", "Ada", "K1")
        st, body = self.reserve("CT-101", "Grace", "K1")
        self.assert_rejected(st, body)
        # case-sensitive comparison: different case is a different alias
        st, body = self.reserve("CT-101", "ada", "K1")
        self.assert_rejected(st, body)
        self.assertEqual(self.counts()["CT-101"], (1, 1))
        self.assertEqual(len(self.db_rows()), 1)

    def test_ac05_key_reuse_different_session_rejected(self):
        self.reserve_ok("CT-101", "Ada", "K1")
        st, body = self.reserve("CT-102", "Ada", "K1")
        self.assert_rejected(st, body)
        self.assertEqual(self.counts(), {"CT-101": (1, 1), "CT-102": (0, 3)})
        self.assertEqual(len(self.db_rows()), 1)

    def test_ac05_replay_when_session_full_returns_original(self):
        first = self.reserve_ok("CT-101", "Ada", "K1")
        self.reserve_ok("CT-101", "Grace", "K2")
        self.assertEqual(self.counts()["CT-101"], (2, 0))
        st, body = self.reserve("CT-101", "Ada", "K1")
        self.assert_2xx(st, body)
        self.assertEqual(body, first)
        self.assertEqual(self.counts()["CT-101"], (2, 0))
        self.assertEqual(len(self.db_rows()), 2)


class TestAc06Cancel(ServerCase):
    def test_ac06_cancel_releases_one_seat(self):
        rec = self.reserve_ok("CT-101", "Ada", "K1")
        self.reserve_ok("CT-101", "Grace", "K2")
        self.assertEqual(self.counts()["CT-101"], (2, 0))
        st, body = self.cancel(rec["id"])
        self.assert_2xx(st, body)
        self.assert_record(body, "CT-101", "Ada", "K1", "cancelled", rid=rec["id"])
        self.assertEqual(self.counts()["CT-101"], (1, 1))
        st, got = self.req("GET", "/reservations/%s" % rec["id"])
        self.assertEqual(st, 200)
        self.assertEqual(got, body)
        # freed seat is bookable again with a new key
        self.reserve_ok("CT-101", "Linus", "K3")
        self.assertEqual(self.counts()["CT-101"], (2, 0))

    def test_ac06_recancel_returns_same_cancelled_record(self):
        rec = self.reserve_ok("CT-101", "Ada", "K1")
        st1, c1 = self.cancel(rec["id"])
        st2, c2 = self.cancel(rec["id"])
        self.assert_2xx(st1, c1)
        self.assert_2xx(st2, c2)
        self.assertEqual(c1, c2)
        self.assertEqual(c2["status"], "cancelled")
        self.assertEqual(self.counts()["CT-101"], (0, 2))

    def test_ac06_cancelled_key_replay_does_not_reactivate(self):
        rec = self.reserve_ok("CT-101", "Ada", "K1")
        st, c = self.cancel(rec["id"])
        self.assert_2xx(st, c)
        before = self.counts()
        st, again = self.reserve("CT-101", "Ada", "K1")
        self.assert_2xx(st, again)
        self.assertEqual(again["id"], rec["id"])
        self.assertEqual(again["status"], "cancelled")
        self.assertEqual(self.counts(), before)
        self.assertEqual(self.counts()["CT-101"], (0, 2))
        st, got = self.req("GET", "/reservations/%s" % rec["id"])
        self.assertEqual(got["status"], "cancelled")
        self.assertEqual(self.db_statuses(), ["cancelled"])


class TestAc07Durability(ServerCase):
    def test_ac07_restart_preserves_state(self):
        active = self.reserve_ok("CT-101", "Ada", "K1")
        gone = self.reserve_ok("CT-101", "Grace", "K2")
        st, cancelled = self.cancel(gone["id"])
        self.assert_2xx(st, cancelled)
        before_counts = self.counts()
        self.assertEqual(before_counts["CT-101"], (1, 1))
        _, a_before = self.req("GET", "/reservations/%s" % active["id"])
        _, g_before = self.req("GET", "/reservations/%s" % gone["id"])

        self.stop()
        self.start()  # no reset

        self.assertEqual(self.counts(), before_counts)
        st, a_after = self.req("GET", "/reservations/%s" % active["id"])
        self.assertEqual(st, 200)
        st, g_after = self.req("GET", "/reservations/%s" % gone["id"])
        self.assertEqual(st, 200)
        self.assertEqual(a_after, a_before)
        self.assertEqual(g_after, g_before)
        self.assertEqual(a_after["status"], "active")
        self.assertEqual(g_after["status"], "cancelled")
        # replay still idempotent after restart
        self.assertEqual(self.reserve_ok("CT-101", "Ada", "K1"), a_before)

        # independent store readback
        rows = self.db_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(self.db_statuses(), ["active", "cancelled"])
        ids = {str(v) for r in rows for v in r.values()}
        self.assertIn(active["id"], ids)
        self.assertIn(gone["id"], ids)

    def test_ac07_restart_does_not_reset(self):
        rec = self.reserve_ok("CT-102", "Ada", "K1")
        self.stop()
        self.start()
        self.assertEqual(self.counts(), {"CT-101": (0, 2), "CT-102": (1, 2)})
        st, got = self.req("GET", "/reservations/%s" % rec["id"])
        self.assertEqual(st, 200)
        self.assertEqual(got, rec)
        self.stop()
        self.start()
        self.assertEqual(self.counts()["CT-102"], (1, 2))


class TestAc08InvalidInput(ServerCase):
    def _assert_unchanged_and_alive(self, expected_rows=0):
        self.assertEqual(self.counts(), {"CT-101": (0, 2), "CT-102": (0, 3)})
        self.assertEqual(len(self.db_rows()), expected_rows)

    def test_ac08_unknown_session(self):
        st, body = self.reserve("CT-999", "Ada", "K1")
        self.assert_rejected(st, body)
        self._assert_unchanged_and_alive()

    def test_ac08_blank_alias(self):
        for alias in ("   ", "", "\t \n"):
            st, body = self.reserve("CT-101", alias, "K-blank")
            self.assert_rejected(st, body)
        self._assert_unchanged_and_alive()

    def test_ac08_missing_request_key(self):
        st, body = self.req("POST", "/reservations",
                            {"sessionId": "CT-101", "attendeeAlias": "Ada"})
        self.assert_rejected(st, body)
        st, body = self.reserve("CT-101", "Ada", "")
        self.assert_rejected(st, body)
        self._assert_unchanged_and_alive()

    def test_ac08_malformed_json(self):
        st, body = self.req("POST", "/reservations", raw=b'{broken')
        self.assert_rejected(st, body)
        self._assert_unchanged_and_alive()

    def test_ac08_json_array_body(self):
        st, body = self.req("POST", "/reservations", raw=b'[1,2,3]')
        self.assert_rejected(st, body)
        self._assert_unchanged_and_alive()

    def test_ac08_non_string_request_key(self):
        st, body = self.req("POST", "/reservations",
                            {"sessionId": "CT-101", "attendeeAlias": "Ada", "requestKey": 123})
        self.assert_rejected(st, body)
        self._assert_unchanged_and_alive()

    def test_ac08_unknown_reservation_cancel_and_get(self):
        st, body = self.req("POST", "/reservations/does-not-exist/cancel", {})
        self.assert_rejected(st, body)
        st, body = self.req("GET", "/reservations/does-not-exist")
        self.assert_rejected(st, body)
        self._assert_unchanged_and_alive()

    def test_ac08_server_survives_all_invalid_input(self):
        self.reserve("CT-999", "Ada", "K1")
        self.reserve("CT-101", "   ", "K2")
        self.req("POST", "/reservations", {"sessionId": "CT-101", "attendeeAlias": "Ada"})
        self.req("POST", "/reservations", raw=b'{broken')
        self.req("POST", "/reservations", raw=b'[]')
        self.req("POST", "/reservations/nope/cancel", {})
        self.assertIsNone(self.proc.poll(), "server process died")
        self._assert_unchanged_and_alive()
        # still functional
        rec = self.reserve_ok("CT-101", "Ada", "K-good")
        self.assert_record(rec, "CT-101", "Ada", "K-good", "active")
        self.assertEqual(len(self.db_rows()), 1)


if __name__ == "__main__":
    unittest.main()
