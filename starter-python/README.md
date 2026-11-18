# Session Seat Desk (Team Jonas)

A local JSON API plus a basic browser UI for reserving seats in two fictional workshops (CT-101, CT-102). State lives in SQLite and survives restarts. Python 3.11+, **standard library only**: there is nothing to install.

> **Disclosure.** This app was built with AI agents before the session's 60-minute build window. Behavioural claims below are backed by tests or commands in this directory. Process claims (who wrote which tests, mutation results, UI checks) are backed by receipts in the evidence sidecar attached to the PR, not by this commit. Judge the receipts, not this README.

## Run

| Step | Command (run in this directory) |
| --- | --- |
| Runtime | `python3 --version`; needs 3.11+ (built and tested on 3.12.3, Linux) |
| Install | none: stdlib only, no lockfile needed |
| Reset fixture (explicit, only this `DATA_DIR`) | `python3 app.py --reset` |
| Start | `python3 app.py`, then open http://127.0.0.1:8765 |
| Stop | Ctrl+C (or SIGTERM). Every write is committed before its response is sent. |
| Restart without reset | `python3 app.py` again. Startup **never** resets. |
| Test | `python3 -m unittest -v test_acceptance test_store_check test_hardening` (about 40 s; exit status 0 means all passed, failures and errors exit 1; the last line prints counts and any skips) |
| Verify the stored data directly | `python3 app.py --check` (exit 0 = ok, 1 = problems; prints JSON) |

Configuration comes from environment variables: `PORT` (default 8765) and `DATA_DIR` (default `./.state`). The server binds only to 127.0.0.1. On Windows use `py -3` in place of `python3`.

Reset refuses to touch a `seats.db` that lacks the fixture ownership marker. Use a new `DATA_DIR` for each experiment.

## State

- **Location:** `$DATA_DIR/seats.db`, by default `starter-python/.state/seats.db`. `.state/` is excluded from the source snapshot.
- **Tables:** `sessions`, `reservations` (`request_key` is UNIQUE across all sessions), and `audit_log` (a hash-chained record of every reserve and cancel).
- **Inspect a record:** `sqlite3 .state/seats.db "select id,session_id,attendee_alias,request_key,status from reservations"`. The `sqlite3` CLI is optional; `python3 app.py --check` gives the same view without it.

## API (fixed paths; field names exactly as `docs/api-contract.md`)

| Request | Success | Rejections (4xx + `{"error":{"code","message"}}`) |
| --- | --- | --- |
| `GET /sessions` | 200 `{"sessions":[{id,title,capacity,activeCount,remainingSeats}]}` | none |
| `POST /reservations` `{sessionId,attendeeAlias,requestKey}` | **201** new booking; **200** replay of the same key with the same session and trimmed alias (returns the original record and its current status) | 400 `MALFORMED_JSON` / `INVALID_BODY` / `INVALID_ALIAS` / `INVALID_REQUEST_KEY` / `INVALID_SESSION_ID`; 404 `UNKNOWN_SESSION`; 409 `REQUEST_KEY_CONFLICT`, `CAPACITY_FULL`; 413 `BODY_TOO_LARGE` |
| `GET /reservations/{id}` | 200 reservation | 404 `UNKNOWN_RESERVATION` |
| `POST /reservations/{id}/cancel` `{}` | 200 cancelled record (repeat cancellations return the same record) | 404 `UNKNOWN_RESERVATION`, 400 if the body is not a JSON object |
| `GET /reservations?alias=Ada` (extra) | 200 `{"reservations":[...]}`; used by the UI's "find booking" box | none |
| `GET /fonts/*.woff2`, `/room.js`, `/vendor/three.module.min.js` | bundled UI assets on an exact whitelist: two fonts (SIL OFL 1.1, `static/fonts/OFL.txt`) and three.js r169 (MIT, `static/vendor/three.LICENSE.txt`), so the UI needs no network | 404 for anything else |
| `GET /health` (extra) | 200 store path, server pid, number of audited changes, last audit hash | 503 `STORE_MISSING` |
| Any other method or path | none | JSON 404 / 405; no HTML error pages anywhere |

Reservation: `{"id","sessionId","attendeeAlias","requestKey","status","createdAt","cancelledAt"}`. `id` is a UUID string. The alias is stored trimmed. Comparisons are otherwise case-sensitive. `adapter.json` uses the default mapping (no wrapper).

Input rules: `requestKey` must be a non-empty string, exactly as the PRD says (`"   "` is a valid key). The alias is trimmed and must contain at least one visible character; zero-width or invisible-only aliases count as blank. Both fields are limited to 200 characters and the request body to 64 KB (413). Invalid Unicode, deeply nested JSON and malformed request lines get 400/405 JSON, never 500.

Order of decisions in `POST /reservations`: validate input, then session exists (so reusing K1 with an unknown session gives 404, not 409; both are rejections with no state change), then **key replay or conflict**, then capacity, then insert. A replay therefore returns the original record even when the session is now full or the booking was cancelled. Every check-then-write runs under one process-wide lock **and** a SQLite `BEGIN IMMEDIATE` transaction.

## Tests and what they establish

| Suite | What it does | Independence |
| --- | --- | --- |
| `test_acceptance.py` (24 tests) | Black-box tests for AC-02 to AC-08: starts the real server as a subprocess, uses a fresh `DATA_DIR` per test, runs real restarts, 5 race batches of 10 threads, and reads SQLite directly | Written by a separate agent (AQE `qe-tdd-specialist`) instructed to work from the PRD only, without reading `app.py`. The brief is in the sidecar; independence is a process claim, not something this commit can prove |
| `test_store_check.py` (6 tests) | `app.py --check` passes on a clean store and **fails** on 5 kinds of tampering: reactivated booking, ghost row, overbooking, alias edited in place, rewritten audit history | Negative controls for the checker itself |
| `test_hardening.py` (13 tests) | Regression tests for issues found by our internal review (Fable) and an AQE chaos audit: invisible aliases, surrogates, deep JSON, non-object bodies, odd methods, bad request lines, size limits, PRD-literal request keys | Each was reported as a defect by the reviewers before the fix (their reports are in the sidecar) |
| `tools/verify.py` (organizer) | API challenges for AC-02 to AC-08, including 10 concurrent batches and a real process restart | Organizer code, unmodified |

Coverage was **not measured**, and we make no coverage claim. The sensitivity of the tests is shown with mutation testing (see the evidence manifest), not with a percentage.

## Beyond the PRD

- **D1, "The Room": seat availability at a glance.** Above the session cards, a 3D diorama (three.js, procedural, no build step) shows each table with one chair per seat. Each active reservation is a little character with the attendee's generated avatar, sitting in a chair; a full table's lamp lights up. It is a *read-only second view*: it owns no booking state and is driven only by successive `GET /sessions` + `GET /reservations` snapshots. When a new active reservation appears in a snapshot, its character drops into the lowest free chair (confetti); when one turns `cancelled`, the character floats away as a ghost. People keep their chair across updates. Clicking the room only preselects that session in the labelled form and focuses the alias field, so keyboard users lose nothing. The camera tilts only with the visitor's pointer, there is no idle animation loop, and with `prefers-reduced-motion` all motion is off (state changes apply instantly). If WebGL is unavailable, the room stays hidden and the 2D app is unchanged. Demo: cancel with `curl`, press Refresh, and the ghost leaves. Limits: it is not real-time (it redraws on refresh, focus and your own actions), and the layout is fixed to the two fixture sessions and their capacities (2 and 3 chairs).

- **Attendee profiles with generated avatars.** Each alias gets a deterministic illustrated avatar computed in the browser from the alias text (an FNV-1a hash picks colour, eyes and mouth). There are no photos, uploads or stored images, so no personal data, in line with the PRD's fictional-alias rule. Clicking a name opens a profile (native `<dialog>`, Esc closes it and focus returns) listing every booking for that alias, read live from `GET /reservations?alias=`. The same avatar appears on the attendee's name tag in the 3D room.
- **Also: a retry-safe booking UI.** The form keeps its request key until the server confirms success. A double-click, a timeout followed by a retry, or a resubmit therefore cannot book a second seat. The UI says "Already processed" on a replay. A "find by alias" box lets a helper locate an attendee's booking without knowing its ID.
- **D2, independent store verification.** `python3 app.py --check` reads the database directly, not through HTTP. It checks that active ≤ capacity and that aliases are trimmed. It then replays the hash-chained `audit_log` (each entry hashes the full record and the previous hash) and requires the result to equal the reservations table exactly: session, alias, key and status. This catches ghost rows, silent reactivations and edited history that API counts alone cannot show. `test_store_check.py` proves the checker fails when it should.

## Known gaps and limits

- Ten bounded race batches show that no overbooking occurred in those trials. They do not prove race freedom. Running two server processes on one `DATA_DIR` relies on SQLite `BEGIN IMMEDIATE` alone, since the thread lock is per process.
- The UI was checked in Chromium on Linux only. No screen-reader test was done. The 3D room has no automated test of its pixels; its correctness rests on rendering only server data (see `static/room.js`) and on manual checks: a booking drops a character into a free chair, a curl cancel sends it away as a ghost after refresh, others keep their seats, and with WebGL disabled the room hides.
- Slow or stalled clients are disconnected after 15 s. The thread count is still unbounded under a flood of connections; this is a local fixture, not a hardened server.
- `--check` assumes the audit log is written only by this app. Someone with write access to the file can recompute the chain, so it shows inconsistency, not tamper-proofing against an attacker.
- Deliberate choices beyond the PRD: invisible-only aliases are treated as blank; 200-character limits on alias and key. Aliases differing only in invisible characters (for example `\u200bAda` and `Ada`) are different attendees, because comparisons are exact.
- `GET /sessions` can return 503 `STORE_MISSING` if the database file is deleted while the server runs.
- Tested on Linux only; the Windows `py -3` command is untested.
- There is no authentication, by design (PRD scope).

## Handoff

- Fork and branch: recorded in the PR. Declared app directory: `starter-python/`.
- The frozen full commit SHA, snapshot `sourceId` and `artifactSha256` are recorded in the PR and evidence manifest after the final commit (not in this file, to avoid a self-referencing commit).
- Building needed Claude Code and Agentic QE agents. **Running needs only Python.** No account, key or network is required.
