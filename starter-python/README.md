# Session Seat Desk

Reserve and cancel seats in two fictional workshops (CT-101, capacity 2; CT-102, capacity 3) through a local JSON API and a basic server-rendered HTML page. Built for the Completion Theater Hackathon, ATD 2026 (rules v1.1).

## Runtime

- **Python 3.11+, standard library only.** No pip install, lockfile, API key, account, database server or network service is needed. It was developed and tested on Python 3.12.10 on Windows 11.
- Check the interpreter from the repo root with `python tools/preflight.py`. On Windows use `py -3` in place of `python`/`python3` in every command.

## Run, reset, stop

From this directory (`starter-python/`):

```sh
python app.py --reset   # create/re-seed the fixture DB (only once, or to start a scenario over)
python app.py           # serve on http://127.0.0.1:8765 ; stop with Ctrl+C
```

- **Restart without `--reset` keeps all state.** The app never resets on start. If no database exists yet, it refuses to start and tells you to run `--reset`.
- `--reset` only touches a directory carrying this app's fixture marker. It refuses an unmarked existing database.
- Environment variables:

  | Variable | Default | Meaning |
  |---|---|---|
  | `PORT` | `8765` | listen port |
  | `DATA_DIR` | `./.state` | fixture state directory |
  | `HOST` | `127.0.0.1` | bind address; Docker sets `0.0.0.0` |

  Use a new `DATA_DIR` per experiment, and never point it at a real database.
- Optional Docker run from the repo root: `docker compose up -d --build` publishes the app on 127.0.0.1:8765 only. State lives in the `app-data` volume. `docker compose restart` restarts the app without resetting, and `docker compose down -v` deletes the state.

## State location

SQLite at `$DATA_DIR/seats.db` (default `starter-python/.state/seats.db`), with tables `sessions` and `reservations`. A `.fixture-owner` marker file sits next to it. Every count is computed from the `reservations` rows on each request; nothing is cached in memory. Inspect it independently with:

```sh
python -c "import sqlite3; print(sqlite3.connect('.state/seats.db').execute('select * from reservations').fetchall())"
```

## API (contract v1.1, no adapter mapping needed)

| Method and path | Success | Rejections |
|---|---|---|
| `GET /sessions` | 200 `{"sessions":[{id,title,capacity,activeCount,remainingSeats}]}` | — |
| `POST /reservations` `{sessionId, attendeeAlias, requestKey}` | **201** new reservation; **200** replay of the same key + session + trimmed alias (current status, even if cancelled) | 400 `INVALID_JSON`/`INVALID_INPUT`, 404 `UNKNOWN_SESSION`, 409 `CAPACITY_FULL`, 409 `KEY_CONFLICT` |
| `GET /reservations/{id}` | 200 `{id,sessionId,attendeeAlias,requestKey,status}` | 404 `NOT_FOUND` |
| `POST /reservations/{id}/cancel` `{}` | 200 the cancelled record (repeat cancels too) | 400 `INVALID_JSON`, 404 `NOT_FOUND` |

- Errors are `{"error":{"code":"…","message":"…"}}` and never come with a 200.
- Aliases are trimmed before they are stored and compared, and must be 1–30 characters after trimming. Comparison is case-sensitive.
- Request keys are globally unique.
- `adapter.json` maps fields one-to-one, uses the `sessions` wrapper and no reservation wrapper, and starts/resets with `["{python}", "app.py"]` / `["{python}", "app.py", "--reset"]`.

## UI

Open http://127.0.0.1:8765. Everything on the page is rendered from SQLite on each request:
- the sessions table (the same function feeds `GET /sessions`)
- a labelled reserve form (Session, Attendee alias)
- a reservations table with a Cancel button per active reservation

No JavaScript is required, and every control is a native form element reachable by keyboard.

- **Success:** the page shows a confirmation only after a redirect that re-reads the stored reservation, so success text never comes from the request alone.
- **Rejection:** a rejection returns the API's 4xx status and shows the error in a `role="alert"` region.
- **Double submit:** each page load embeds a fresh request key, so submitting the same form twice is a replay, not a second booking.

## Tests

```sh
python -m unittest discover -s tests -t . -v   # all tests; exit status is non-zero on any failure
python -m compileall -q .                       # syntax check (stdlib "lint")
```

- 28 acceptance tests are in `tests/acceptance/test_acNN_*.py`, one file per AC with Given/When/Then comments. They run the real `app.py` as a subprocess on a free port with a temporary `DATA_DIR` (`tests/support.py`), and talk to it only over HTTP.
- "No state change" assertions check both `GET /sessions` and the raw SQLite row count.
- AC-04 fires 10 batches × 10 simultaneous distinct requests at the last seat.
- AC-07 kills and relaunches the process without a reset.
- No tests are skipped.
- Shared verifier (from the repo root): `python tools/verify.py --source starter-python --adapter starter-python/adapter.json --evidence <new-dir-outside-repo>`. On the pre-freeze source this reported API PASS for AC02–AC08 with 10×10 race batches. AC01 and UI agreement are NOT RUN by design and need a human check.

## Known gaps

- **Concurrency is evidence, not proof.** Seats are guarded by one `BEGIN IMMEDIATE` SQLite transaction per write, which covers the capacity check, the key lookup and the insert. That is designed to be race-free within one process or across processes sharing the DB file. The tests and verifier show 100 bounded race attempts with exactly one winner each time, but that does not prove the absence of all concurrency defects.
- **UI checks have no browser.** UI tests parse the server-rendered HTML, and no browser or screen reader was run in automation. Check keyboard and screen-reader behaviour manually.
- **No delete or edit.** Reservations can only be created and cancelled, by design of the PRD.
- **Timeouts.** A write waits up to 10 s for the SQLite lock. Under extreme contention a request could fail with a 500 `INTERNAL` error rather than a 4xx.
- **No HTTP reset endpoint.** Reset is CLI-only, by design.
