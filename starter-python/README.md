# Session Seat Desk (team README)

Seat reservations for two fictional workshops: local JSON API, one-page UI, SQLite state. Fictional aliases only.

- **Team ID / members:** team-a (fill in aliases)
- **Runtime:** Python 3.11+ (developed on 3.13.5, SQLite 3.45.3). Standard library only.
- **Dependencies:** none. No install step, no lockfile, no `.env`, no AI account or hidden service needed to RUN. AI coding assistance was used to BUILD only.
- **Declared app directory:** `starter-python/`

## Run

From this directory (on Windows use `py -3` instead of `python3`):

```sh
python3 app.py --reset    # creates/reset the fixture store and seeds CT-101 and CT-102
python3 app.py            # serves http://127.0.0.1:8765 in the foreground; Ctrl+C stops it
```

Restart with the **same command without `--reset`**; state is preserved. The app refuses to start (exit 2) if `--reset` was never run for that `DATA_DIR`, or if the database there lacks this app's `.fixture-owner` marker, the same ownership check `--reset` applies. It never resets itself.

Config: `PORT` (default `8765`), `DATA_DIR` (default `.state/` next to `app.py`). It binds `127.0.0.1` only.
Reset only touches a `DATA_DIR` that carries this app's ownership marker, or one without a database yet. Use a new directory per experiment.

## State

SQLite file `DATA_DIR/seats.db` (default `./.state/seats.db`). Inspect it with:

```sh
sqlite3 .state/seats.db "SELECT id, session_id, attendee_alias, request_key, status FROM reservations"
```

Active seats are computed as `COUNT(*) WHERE status='active'`; there is no separate counter. Every write runs in a `BEGIN IMMEDIATE` transaction, so concurrent requests for the last seat are serialized by SQLite.

## Test

```sh
python3 -m unittest -v test_app test_spec_gaps
```

The exit status is non-zero if any test fails. The tests start the real app as a subprocess on a free port with a temporary `DATA_DIR`, call it over HTTP and also read `seats.db` directly. They cover AC-02..AC-08, including ten batches of ten concurrent attempts for one seat, a real stop/restart without reset, and no row created by any rejected request. There are no skipped tests. They do not drive the browser UI (see known gaps). `test_spec_gaps.py` adds requirement-gap tests found by tracing the PRD and API contract against `test_app.py` (CT-102 boundary, exactly-one seat release, key conflict on a cancelled reservation, concurrent same-key replays, restart idempotency, reset behaviour, rejections against non-empty state, error shape, JSON `Content-Type`, loopback-only bind, exit-status reporting, and a static UI structure check). `test_coverage.py` tests the coverage tooling below.

## Coverage

```sh
python3 coverage_report.py                       # runs test_app under tracing, prints % and missed lines
python3 coverage_report.py --fail-under 95       # exit 2 if below 95%
python3 coverage_report.py --json ../cov.json    # also write the result (keep it outside this directory)
```

Stdlib only (no `coverage` package). `test_app.py` launches the app through `covtrace.py` when `COVERAGE_DIR` is set; each traced process (server, reset, restart) records the `app.py` lines it executed, and the report merges them and compares against the executable lines of the compiled file. **Line coverage only, `app.py` only:** no branch coverage, and the UI JavaScript and `covtrace.py` itself are not measured. The exit status is non-zero if the tests fail, if no data was recorded, or if the threshold is missed. High coverage shows code was executed, not that the assertions are strong; the mutation checks under "Verified so far" address that.

## API (matches `docs/api-contract.md`; `adapter.json` is the shared-verifier mapping)

| Request | Success | Rejection |
| --- | --- | --- |
| `GET /sessions` | `200 {"sessions":[{"id","title","capacity","activeCount","remainingSeats"}]}` | none |
| `POST /reservations` `{"sessionId","attendeeAlias","requestKey"}` | `201` new, or `200` replay of the same key/session/trimmed alias (original ID and current status, never reactivated) | `400` invalid/missing field or malformed JSON; `404 UNKNOWN_SESSION`; `409 CAPACITY_FULL`; `409 KEY_CONFLICT` (key reused with another session or alias; keys are global) |
| `GET /reservations/{id}` | `200` record | `404 NOT_FOUND` |
| `POST /reservations/{id}/cancel` `{}` | `200` cancelled record (repeat is a no-op) | `404 NOT_FOUND`; `400` malformed JSON; `411` chunked (`Transfer-Encoding`) body |

Reservation record: `{"id","sessionId","attendeeAlias","requestKey","status":"active"|"cancelled"}` (no wrapper). Errors: `{"error":{"code","message"}}` with a 4xx/5xx status, never HTTP 200. Other: `GET /health` → `{"status":"ok"}` (liveness only), `GET /` → UI, unknown path → `404`, wrong method → `405`.

Rules implemented: aliases are trimmed then compared case-sensitively; blank or whitespace-only alias rejected; `requestKey` must be a non-empty string (whitespace-only is also rejected: our choice, the PRD only says non-empty); body limit 64 KiB; request bodies are read by `Content-Length` only, so any `Transfer-Encoding` request is rejected with `411` (it previously let a malformed chunked cancel succeed).

Sample:

```sh
curl -s -X POST localhost:8765/reservations -H 'Content-Type: application/json' \
  -d '{"sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1"}'
# {"id": "…", "sessionId": "CT-101", "attendeeAlias": "Ada", "requestKey": "K1", "status": "active"}
```

## Verified so far (observed, this machine, Python 3.13.5)

- `python3 -m unittest test_app test_coverage test_spec_gaps`: 47 tests, all pass (21 + 6 + 20). Four injected faults (cancel ignoring a malformed body, non-JSON `Content-Type`, error body without `code`, binding `0.0.0.0`) pass `test_app` but each fails the matching `test_spec_gaps` test.
- `python3 coverage_report.py`: **97.7% measured line coverage of `app.py`** (211/216 lines). Missed: lines 227-230 (500 and broken-pipe handlers) and 266 (`KeyboardInterrupt` in `main`). The first run, before the edge-case tests were added, measured 90.2%; `test_spec_gaps` adds assertions, not new lines, so the figure did not move.
- Negative control: three deliberate mutations (capacity off-by-one, deferred instead of immediate transaction, replay reactivating a cancelled reservation) each turned the suite RED; the original was restored.
- `tools/verify.py` with this `adapter.json`: AC02..AC08 API PASS, source hash unchanged before/after. API PASS is not an acceptance score.
- Manual browser run (Playwright): both seeded sessions shown; reserve updated the table to active 1 / remaining 1; cancel returned to 0 / 2; after a real process kill and restart without reset, the reservation was still `cancelled` and counts were unchanged; a whitespace-only alias showed a visible error and changed nothing.

## Known gaps and unexecuted checks

- AC-01 cold start by another team: **NOT RUN**. A QE agent followed the Run section on a clean copy and it worked, but that is still the builder's side, not an independent team.
- The UI has no automated tests (only a static structure check); its behaviour was checked by hand in one browser (Chromium via Playwright): double-click books one seat, a rejected reserve clears the record box so Cancel cannot act on an older reservation, and a stopped server gives truthful messages. Other browsers and a screen reader were not tried. Known UI gaps: the page overflows horizontally at 320px width and with a very long alias; a page reload after a lost response generates a new request key, so a retry could book a second seat.
- The optional organizer test `tests/test_tools.py::ShippedStarterTransportTests::test_cold_shipped_starter_reset_health_placeholder_and_501` fails on this branch, by design: it asserts the unimplemented scaffold behaviour (`/health` = scaffold, 501 stubs).
- Race testing is bounded (ten batches of ten); it is evidence for those trials, not proof of freedom from concurrency defects.
- Coverage is line-only and was measured on POSIX (macOS). The tracer flushes every 0.2 s, so on Windows (hard process kill) the last fraction of a second of a traced process may be missing; this is untested there.
- One failure of `test_ct102_boundary_and_isolation_from_ct101` was seen once during mutation runs and not reproduced (0 failures in 25 isolated and 18 full-module reruns on the unmodified app). Cause unknown; a possible suspect is the free-port helper, which picks a port and releases it before the app binds.
- The static UI check does not establish UI agreement with the API (AC-02/03/07 in the browser were checked manually, once).
- The unhandled-exception (500) and client-disconnect paths are not exercised by any test.
- Fixed after a QE-fleet pass: bad client input that returned 500 (lone-surrogate text, deeply nested JSON) is now 400; chunked bodies get 411; startup refuses a database without this app's marker.
- Open: `HEAD`/`OPTIONS` get Python's HTML 501 page, not JSON; a `text/plain` POST is accepted (any web page could create seats on a locally running app); if `seats.db` is deleted while running, SQLite recreates an empty file and the app answers 503 until `--reset`; there is no socket timeout (a stuck client holds a thread); with 100 simultaneous new connections some macOS clients saw connect timeouts (small listen backlog).
- Known and left as is: a non-numeric `PORT` exits with a Python traceback; store failures answer 5xx (503 locked, 500 unexpected), not 4xx, because they are server faults (both confirmed by running).
- No favicon (browser logs a 404 for `/favicon.ico`). No reset endpoint (reset is CLI only). No waitlist, search or other optional features.
- The test sources and README were written with AI assistance; a human has not independently reviewed them yet.
