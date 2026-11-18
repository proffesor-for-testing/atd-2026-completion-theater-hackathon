# Session Seat Desk — team handoff README

**Team ID and aliases:** team-annie (alias: Annie)

**Runtime and version:** Python 3.11+ (built and tested with CPython 3.12.16 on macOS). Standard library only, including `sqlite3`. Use the same interpreter for every command. On macOS the system `python3` may be 3.9; select a 3.11+ executable explicitly (for example `/opt/homebrew/bin/python3.12`).

**Dependency installation:** none. There are no third-party packages, so there is no lockfile.

**Build-time tools (not needed to run):** Claude Code was the coding assistant. The app has no AI dependency and needs no account, key or network service.

## Run

Run every command from **this app directory** (in the repository it is `starter-python/`; in an extracted snapshot it is whatever directory you extracted to). In all commands below, `python3` means **a Python 3.11+ interpreter**. Check it with `python3 --version`. If it reports an older version (macOS ships 3.9), use an explicit executable such as `python3.12` or `/opt/homebrew/bin/python3.12` (macOS), or `py -3.12` (Windows), and use the same one throughout.

```sh
python3 app.py --reset     # explicit fresh fixture: seeds CT-101 (2) and CT-102 (3)
python3 app.py             # start in foreground; never resets
```

Open http://127.0.0.1:8765 . Environment variables: `PORT` (default 8765) and `DATA_DIR` (default `./.state`). Example of an isolated fixture: `DATA_DIR=/tmp/seat-fixture-1 PORT=9001 python3 app.py --reset && DATA_DIR=/tmp/seat-fixture-1 PORT=9001 python3 app.py`.

**Stop / restart:** Ctrl+C (or SIGTERM) stops the process. Run `python3 app.py` again with the **same** `DATA_DIR` and **without** `--reset` to restart with preserved state. The startup line prints the port, state file and PID.

**Reset:** `python3 app.py --reset` (with the same `DATA_DIR`). It drops and recreates only the tables in `DATA_DIR/seats.db`. It refuses to touch a `seats.db` that has no matching `.fixture-owner` marker. Never run it between the stop and restart steps of AC-07.

## Test

```sh
python3 -m unittest -v test_app
echo $?     # 0 = all passed, non-zero = any failure or error
```

The tests start the real `app.py` as a child process on a free loopback port with a temporary `DATA_DIR`, after `--reset`, and use HTTP only. Some tests also read SQLite directly to check that no hidden row was inserted. Coverage: AC-01 (UI served, static check only), AC-02, AC-03, AC-04 sequential and 10 concurrent attempts, AC-05 (trimmed replay, alias/session/case conflicts), AC-06, AC-07 (real process stop and start, new PID), AC-08 (all five invalid cases plus empty key). No tests are skipped. Coverage was not measured.

## State

SQLite file `DATA_DIR/seats.db` (default `.state/seats.db` inside this app directory, WAL mode). Inspect it independently:

```sh
sqlite3 .state/seats.db "SELECT id, session_id, attendee_alias, request_key, status FROM reservations ORDER BY created_seq;"
sqlite3 .state/seats.db "SELECT * FROM sessions;"
```

Tables: `sessions(id, title, capacity)` and `reservations(id, session_id, attendee_alias, request_key UNIQUE, status, created_seq)`. Active and remaining counts are computed from stored rows on every read and never cached.

Concurrency: each create or cancel runs inside one `BEGIN IMMEDIATE` SQLite transaction. That transaction does the key lookup, the capacity count and the insert, so concurrent writers are serialized.

## API (rules v1.1, shared field names; `adapter.json` maps them)

| Method and path | Success | Errors |
| --- | --- | --- |
| GET /sessions | 200 `{"sessions":[{"id","title","capacity","activeCount","remainingSeats"}]}` | — |
| POST /reservations | 201 new record; 200 same-key replay (current status) | 400 malformed JSON / blank alias / missing or empty key / missing sessionId; 404 unknown session; 409 `CAPACITY_FULL`; 409 `REQUEST_KEY_CONFLICT` |
| GET /reservations/{id} | 200 record | 404 |
| POST /reservations/{id}/cancel | 200 cancelled record (also on repeat) | 400 malformed JSON; 404 unknown |
| GET /reservations | 200 `{"reservations":[...]}` (extra, used by the UI) | — |

Sample: `curl -s -X POST localhost:8765/reservations -H 'Content-Type: application/json' -d '{"sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1"}'` →
`{"id": "res-…", "sessionId": "CT-101", "attendeeAlias": "Ada", "requestKey": "K1", "status": "active"}`

Errors use `{"error":{"code":"…","message":"…"}}`. Aliases are trimmed before they are stored and compared. Comparison is case-sensitive. Request keys are global and compared exactly. A replay returns the existing record even when that session is now full, and even when the record is cancelled (it is never reactivated).

## UI

`/` is one HTML page with no external resources. It shows the sessions table, a reserve form (session, alias, request key), a reservations table with Cancel buttons and an ID lookup. All values shown come from API responses. A **Receipts** panel logs every HTTP call (method, path, status, latency, raw request/response JSON, copy as curl). Each reservation has **↺ Replay**, which resends its original request and shows that the same ID returns and no seat is consumed. The **Demo tools** checkbox (off by default) reveals **⚡ Race ×10** on each session card. It fires 10 simultaneous real bookings (aliases `Racer-1…10`) at one session and reports whether capacity held. It writes to the store, so use it only on a demo fixture. A booking is reported as successful only after the server confirms it. Errors appear in a visible `role="status"` region. All controls have labels and work with the keyboard.

## Handoff

**Fork / branch:** https://github.com/acoetzeect/atd-2026-completion-theater-hackathon — `submission/team-annie`

**Declared app directory:** `starter-python/` (this README, `app.py`, `static/index.html`, `sessions.json`, `adapter.json`, `test_app.py`).

The frozen full commit, PR URL, snapshot sourceId and archive SHA-256 are recorded in the PR and the evidence manifest, not in this file.

**Known gaps / not done:**
- An AI audit on the earlier commit reported these low-severity behaviors. We kept them deliberately: they meet the contract, and changing them this close to the freeze adds risk.
  - JSON is parsed with Python's `json`, so `NaN` and duplicate keys (last one wins) are accepted.
  - There is no length limit on aliases.
  - A whitespace-only request key (for example `"   "`) is accepted. Keys are compared exactly and are not trimmed.
  - PUT/DELETE/PATCH return the standard library's 501 HTML page, not a JSON error. These methods are outside the contract.
  - `Content-Length: -1` returns 413, not 400.
  - Nothing prevents two processes from serving the same `DATA_DIR`. Capacity still held in that test because SQLite serializes writers.
- The UI is not tested automatically. UI agreement (AC-02/03/07) needs a manual browser check.
- The concurrency tests are bounded (10 parallel attempts, plus the shared verifier's 10×10). They do not prove the app is free of all races.
- The unknown-session check runs after the request-key lookup. So reusing an existing key with an unknown session returns 409 conflict, not 404. In both cases nothing changes.
- There is no rate limiting or auth (out of scope). The server binds only to 127.0.0.1.
