# Session Seat Desk — Team Alt

Reserve and cancel seats in two fictional workshops through a pastel, keyboard-usable UI and a
local JSON API, with state in SQLite that survives a restart.

| | |
| --- | --- |
| **Team** | Team Alt |
| **Fork / branch** | `altlv/atd-2026-completion-theater-hackathon`, branch `submission/team-alt` |
| **Declared app directory** | `starter-python/` — this README, all source, adapter and tests |
| **Frozen commit, sourceId, artifactSha256** | Recorded in the PR and the evidence manifest after the final commit, not here |

## Run it (needs only Python)

**Runtime:** Python 3.11+ standard library, with no `pip install`. Built and tested with CPython 3.12.10 and SQLite 3.49.1 on Windows 11.
On Windows use `py -3`; on macOS/Linux use `python3`. Run these from this directory.

```sh
py -3 app.py --reset     # explicit fixture reset: seeds CT-101 (2 seats) and CT-102 (3 seats)
py -3 app.py             # serve at http://127.0.0.1:8765 — stop with Ctrl+C
```

- **Restart:** run `py -3 app.py` again **without** `--reset`. Startup never resets. It refuses to start
  if there is no initialised fixture, rather than silently creating one.
- **Port / state:** `PORT` (default `8765`) and `DATA_DIR` (default `./.state`). The app binds `127.0.0.1` only.
- **Reset safety:** `--reset` only touches a directory carrying this app's `.fixture-owner` marker. It
  refuses any other existing database. Use a fresh `DATA_DIR` per experiment.

## State

The SQLite file is at `$DATA_DIR/seats.db` (default `starter-python/.state/seats.db`). Every request opens
a fresh connection, so nothing is cached in memory. To inspect it independently of the API:

```sh
py -3 -c "import sqlite3,sys; [print(r) for r in sqlite3.connect(sys.argv[1]).execute('select id,session_id,attendee_alias,request_key,status from reservations')]" .state/seats.db
```

**Server log:** one JSON line per request and per startup, written to stdout and to
`$DATA_DIR/server.log`. Fields: `ts`, `method`, `path`, `status`, `ms`, plus `event`
(`reservation.created` / `replayed` / `cancelled` / `rejected` with `code` / `server.start` with
`activeBySession` read from disk). Aliases and request keys are deliberately not logged.

## API

The paths and field names follow `docs/api-contract.md` exactly, and `adapter.json` maps them for `tools/verify.py`.

| Method and path | Success | Rejections (always 4xx + `{"error":{"code","message"}}`) |
| --- | --- | --- |
| `GET /sessions` | 200 `{"sessions":[{id,title,capacity,activeCount,remainingSeats}]}` | — |
| `POST /reservations` | **201** new, **200** replay of the same key | 400 validation, 404 unknown session, 409 `CAPACITY_FULL` / `REQUEST_KEY_CONFLICT`, 413, 415, 403 cross-origin `Origin` or foreign `Host` (every endpoint) |
| `GET /reservations/{id}` | 200 record | 404 |
| `POST /reservations/{id}/cancel` with `{}` | 200 cancelled record (also on repeat) | 404, 400 non-empty body |
| `GET /reservations?sessionId=&status=` | 200 `{"reservations":[…]}` (extra: drives the UI list) | 400 bad status |

A sample request and response:

```http
POST /reservations
Content-Type: application/json

{"sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1"}

201 Created
{"id":"3f1c…-uuid","sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1",
 "status":"active","createdAt":"2026-11-18T19:58:01.123+00:00","cancelledAt":null}
```

These rules come from the PRD:
- Aliases are trimmed, then compared case-sensitively.
- Request keys are globally unique.
- Replaying a cancelled reservation returns it still cancelled.
- Cancel is a status change, never a delete.

## Tests

| Suite | Command | Needs |
| --- | --- | --- |
| Unit, store rules (14) | `py -3 -m unittest -v test_app` | Python only |
| API, security and UI (Playwright) | `npm ci` once, then `npx playwright test` | Node 22.13+ for `node:sqlite` — only 24.21 has actually been run |
| Type check | `npm run typecheck` | Node |

Both runners return a nonzero exit on any failure. Playwright runs with `retries: 0` and `forbidOnly`.
If Chromium is missing, run `npx playwright install chromium` once. Every Playwright test starts its **own**
app process with its own fresh `DATA_DIR` (`tests/support/`). It checks writes against the API **and** reads
the SQLite file directly.

- `tests/api/` covers:
  - AC-02 to AC-08, with 10 concurrency batches of 10 requests for one seat
  - a real stop and restart (the PID changes)
  - OWASP API checks in `security.spec.ts`: headers/CSP, CSRF and cross-origin, mass assignment, body
    and field limits, injection, path traversal, error hygiene, and non-sequential IDs
- `tests/ui/` covers:
  - full CRUD through the browser, with the UI, network response and stored state agreeing
  - the cancel dialog, visible errors, the capacity-full state, and resubmitting a used key
  - XSS rendering, restart then reload, and a keyboard-only flow
  - axe WCAG 2.2 A/AA checks

The page is served with a CSP that forbids inline scripts, and user text is only ever written with `textContent`.

## Known gaps and limits

- **No rate limiting.** It would break the mandated AC-04 concurrency probe. Body size, field lengths and
  socket idle time are capped instead.
- **No authentication or authorisation, so not OWASP A01/API1/API5 compliant.** The PRD excludes
  users. `GET /reservations` lists every ID, alias and request key to anyone who can reach the
  port, so anyone on this machine can cancel any reservation. Random IDs do not change that.
- **DNS rebinding is blocked** by a `Host` allow-list (`127.0.0.1:<port>`, `localhost:<port>`). Before
  this, a rebound page could book and cancel seats (found by probing, after the suite was green).
- **One alias can hold several seats** with different request keys. The PRD allows it; nothing limits it.
- **`npm audit`: 0 vulnerabilities** at freeze (test tooling only; the app has no dependencies).
  **Not checked:** fuzzing, DAST/SAST scanning, macOS/Linux.
- **Bounded race evidence.** The ten race batches show nothing went wrong in those trials. They do not prove
  the app is race-free. Writes use SQLite `BEGIN IMMEDIATE`, which takes the write lock before the
  capacity read.
- **Accessibility evidence.** axe finds only automatically detectable WCAG issues. No screen-reader
  session has been run.
- **Single-process only.** Tested with one process and one SQLite file on the local disk.

## Build tooling (not needed to run)

The app was built with Claude Code (an AI coding agent). Running it does not need any AI account or service.
