# Session Seat Desk (Python, stdlib only)

Reserves seats in two fictional workshops (CT-101, CT-102) through a local JSON
API and a basic HTML UI. State is stored durably in SQLite.

- **Runtime:** Python 3.11+ (tested on 3.12), standard library only. No pip
  install, API key, Docker, database server or deployment. No lockfile is
  needed because there are no third-party dependencies.
- **State location:** `DATA_DIR/seats.db` (default `.state/seats.db` in this
  directory) plus the fixture marker `DATA_DIR/.fixture-owner`.
- **Config:** `PORT` (default `8765`) and `DATA_DIR`. The server binds `127.0.0.1` only.

## Run / reset / test

From this directory (on Windows use `py -3` instead of `python3`):

```sh
python3 app.py --reset          # explicit fresh fixture: seeds CT-101 (cap 2) and CT-102 (cap 3)
python3 app.py                  # serve http://127.0.0.1:8765 — never resets
python3 -m unittest -v test_app # behavioral tests; non-zero exit on any failure
```

Open http://127.0.0.1:8765 . Stop with Ctrl+C. Restart with `python3 app.py`
(**without** `--reset`) to keep state. Reset refuses a `seats.db` that lacks the
fixture marker; use a fresh `DATA_DIR` for each experiment and never point it at
a real database. Isolated example:

```sh
DATA_DIR=/tmp/ssd-audit PORT=9000 python3 app.py --reset
DATA_DIR=/tmp/ssd-audit PORT=9000 python3 app.py
```

Windows PowerShell:

```powershell
$env:DATA_DIR="$env:TEMP\ssd-audit"; $env:PORT="9000"; py -3 app.py --reset
py -3 app.py
```

Configuration names are listed in `.env.example` (names only; the app does not
read `.env` files).

## API

Field names follow `docs/api-contract.md` exactly; `adapter.json` maps them 1:1
(`sessions: "sessions"`, `reservation: ""`, i.e. no reservation wrapper).

| Method and path | Success | Rejections |
| --- | --- | --- |
| `GET /sessions` | 200 `{"sessions":[{id,title,capacity,activeCount,remainingSeats}]}` | — |
| `POST /reservations` | 201 new record; 200 idempotent replay (same key + session + trimmed alias) returns the original record and current status, even if the session is now full | 400 `MALFORMED_JSON` / `INVALID_BODY` / `BLANK_ALIAS` / `MISSING_REQUEST_KEY` / `INVALID_REQUEST_KEY` (non-string, empty or whitespace-only key) / `FIELD_TOO_LONG` (>200 chars) / `INVALID_TEXT` (lone surrogate or NUL) / `INVALID_LENGTH`; 411 chunked body; 404 `UNKNOWN_SESSION`; 409 `CAPACITY_FULL`; 409 `REQUEST_KEY_CONFLICT` |
| `GET /reservations/{id}` | 200 record `{id,sessionId,attendeeAlias,requestKey,status}` | 404 `RESERVATION_NOT_FOUND` |
| `POST /reservations/{id}/cancel` (`{}`) | 200 cancelled record (also on repeat) | 400 malformed JSON; 404 unknown id |
| `GET /reservations` (extra, used by UI) | 200 `{"reservations":[...]}` | — |
| `GET /health` | 200 `{"status":"ok"}` (liveness only, not acceptance) | — |

Rejections use `{"error":{"code":"...","message":"..."}}` with a 4xx status
(also 413 for bodies over 64 KiB, 404 JSON for unknown routes/methods). Server-side
failures use the same JSON shape: 503 `STORE_BUSY` (another writer holds the
store; writers wait at most ~10 s), 500 `STORE_ERROR` (store missing tables or
corrupt — reset a fresh `DATA_DIR`) or 500 `INTERNAL_ERROR`; the process stays up. `HEAD` requests get a bodiless 405. `remainingSeats` is the raw
`capacity - activeCount`, never clamped, so an oversell would be visible.

Rules implemented: aliases are trimmed before storage and comparison and are
otherwise case-sensitive; an alias with no visible characters (only whitespace,
control, zero-width or BOM characters) counts as blank; request keys are globally unique and compared exactly
(case-sensitive, not trimmed), and a whitespace-only key is rejected (stricter
than the PRD's "non-empty string");
a cancelled reservation is never reactivated by replay; a new key is needed for a
new reservation. Each write runs in a `BEGIN IMMEDIATE` SQLite transaction under a
process-wide lock, so capacity checks and inserts are atomic.

## UI

Open http://127.0.0.1:8765 . `static/index.html` (no build step, no external
assets) renders only what `GET /sessions` and `GET /reservations` return and
re-reads them every 5 s while the tab is visible, so API-made changes appear
without a reload. "Live · checked HH:MM:SS" turns into a red "Offline" state
(dashed borders plus an error banner) if the server is unreachable, instead of
showing stale numbers as current.

- **One board per session**: capacity bar, "N of M seats taken · K remaining",
  an attendee card per active booking and "+ Add attendee" in the next open seat.
- **Book**: "+ Add attendee" opens the form inside the seat; Enter books, Esc
  closes. The form stays open for the next attendee while seats remain. A
  request key is generated per booking; tick **Show request keys** to see/edit
  it (needed for replay/conflict checks such as AC-05 with key `K1`).
- **Cancel**: the **Cancel** button on an attendee's card → "Yes, release seat"
  / "Keep booking" (Esc keeps). The confirmation toast offers "Book … again"
  (a new booking with a new key; a cancelled reservation is never reactivated).
- **Find attendee** (`/`): highlights matching cards and filters the records.
- **All records** (expand at the bottom): every reservation with full ID,
  status and request key, plus lookup by ID via `GET /reservations/{id}`.
- Accessibility: labelled, keyboard-operable controls; focus moves to the
  logical next control after booking, cancelling or closing; errors appear in
  place with `role="alert"` and `aria-invalid`; dark mode and reduced motion are
  respected; no sideways page scroll down to 320 px. All text is inserted with
  `textContent` (no HTML injection from aliases).

## Tests

`test_app.py` starts the real `app.py` subprocess on an ephemeral port with a
temporary `DATA_DIR` and covers AC-02…AC-08 over HTTP, including a 10-way race
for the last seat, a real stop/restart without reset, malformed JSON and direct
SQLite readback to confirm no hidden rows were inserted.

## Known gaps

- AC-01 and UI agreement (AC-02/03/07) are verified manually in a browser; the
  unit tests only check that the page is served and wired to the API.
- Race tests are bounded trials (one 10-way batch here, 10×10 in the shared
  verifier); they do not prove the absence of all concurrency defects.
- No authentication, by design (local fictional fixture only). Do not expose the
  port beyond loopback.
