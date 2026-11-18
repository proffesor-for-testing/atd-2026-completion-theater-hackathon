# Session Seat Desk — team-a

Seat reservations for two fictional workshops, with a local JSON API and a basic browser UI. Built from the organizer's optional Python scaffold for the Completion Theater Hackathon (rules version 1.1).

**Team ID and members' aliases:** team-a — _members: fill in aliases_

**Fork and branch:** https://github.com/jameskblack/atd-2026-completion-theater-hackathon, branch `submission/team-a`

**Declared app directory:** `seat-desk/`. It holds this README, all app source, `adapter.json` and the tests. `starter-python/` is the untouched organizer scaffold and is not part of this submission.

## Runtime and dependencies

- **Runtime:** Python 3.11 or newer, standard library only. It was built and tested with CPython 3.14.4 on Windows 11.
- **Install:** none. There are no third-party packages, so there's no lockfile. No account, API key, database server, network service or AI model is needed to run the app or its tests.
- **Building:** the app was built with an AI coding agent, but the agent isn't needed to run it.

Run every command below from inside `seat-desk/`. On Windows use `py -3` in place of `python3`, and use the same interpreter for every command.

## Start, stop, restart, reset

```sh
python3 app.py --reset        # 1. one-time explicit fresh seed (fixture directory only)
python3 app.py                # 2. start; open http://127.0.0.1:8765
```

- **Stop:** press Ctrl+C in the terminal where the app is running.
- **Restart:** run `python3 app.py` again **without** `--reset`. Ordinary start never resets or reseeds; it refuses to start if no database exists yet.
- **Reset:** `python3 app.py --reset` deletes all reservations and reseeds CT-101 (capacity 2) and CT-102 (capacity 3). It only touches a database it created itself: it refuses any `seats.db` that lacks the `.fixture-owner` marker file.
- **Configuration:** environment variables only. `PORT` (default `8765`) sets the port, and `DATA_DIR` (default `seat-desk/.state`) sets the fixture directory. Use a new `DATA_DIR` per experiment:

  ```sh
  DATA_DIR=/tmp/seatdesk-1 PORT=8800 python3 app.py --reset
  DATA_DIR=/tmp/seatdesk-1 PORT=8800 python3 app.py
  ```

  In PowerShell, set them first: `$env:DATA_DIR='C:\temp\seatdesk-1'; $env:PORT='8800'`.

The server binds to `127.0.0.1` only and runs in the foreground.

## State location and how to inspect it

- **State file:** `$DATA_DIR/seats.db`, a SQLite database. The default is `seat-desk/.state/seats.db`, and the app prints the full path at startup.
- **Tables:** `sessions(id, title, capacity)` and `reservations(id, session_id, attendee_alias, request_key UNIQUE, status)`.
- **Remaining seats** aren't stored; they're always computed from active rows.

To read the records directly, independently of the API:

```sh
python3 -c "import sqlite3,sys; [print(r) for r in sqlite3.connect(sys.argv[1]).execute('select * from reservations')]" .state/seats.db
```

## Tests

```sh
python3 -m unittest -v test_app
```

The command exits **0 only if every test passes**. Any failure or error exits 1, and nothing is skipped.

Each test launches a **separate `app.py` process** with a fresh `DATA_DIR` and port and talks to it over HTTP. Where the PRD asks for it, the test also reads the SQLite file directly. The suite has 14 tests:

| Area | What the tests check |
| --- | --- |
| AC-02 | Exact seeded sessions after a fresh reset |
| UI | The page is served, with labelled controls |
| AC-03 | A reservation is created, read back by ID, counts change, and the store row matches |
| AC-04 | Sequential capacity: the third booking is rejected with 409 `CAPACITY_FULL` and no row is inserted. Concurrency: 10 simultaneous attempts for the last seat give exactly one 201 and nine 409s |
| AC-05 | A trimmed-alias replay returns the same record. Reusing a key with a different alias, a different session or a different alias case is a 409 with the store unchanged. A replay succeeds even when the session is full |
| AC-06 | Cancel releases one seat, a repeat cancel is stable, a replay after cancel returns the cancelled record without reactivating it, and a new key books again |
| AC-07 | After a real process stop and restart on the same `DATA_DIR`, with a new PID and no reset, the active and cancelled records and the counts are unchanged |
| AC-08 | All five invalid cases are rejected with 4xx and an `error`, with no change to the API counts or the store, and the process stays up. Extra malformed shapes are also rejected |
| Model-based | Three seeded random sequences of 40 operations each (reserve, replay, conflict, cancel) are checked after every step against a reference model and the SQLite store |

**Negative controls**, run in disposable copies only, never in this source:

- Removing the capacity check made both AC-04 tests fail.
- Making ordinary start call reset made the AC-07 restart test fail.

The receipts are recorded in the team's evidence manifest.

## API

Paths and fields follow `docs/api-contract.md` exactly, so the shipped `adapter.json` needs no remapping. Its settings:

- `start` is `["{python}", "app.py"]` and `reset` is `["{python}", "app.py", "--reset"]`.
- Session records are wrapped in `{"sessions": [...]}`.
- Reservations are returned unwrapped (`"reservation": ""`).

| Method and path | Success | Rejections |
| --- | --- | --- |
| `GET /sessions` | 200 `{"sessions":[{"id","title","capacity","activeCount","remainingSeats"}]}` | none |
| `POST /reservations` body `{"sessionId","attendeeAlias","requestKey"}` | **201** new record; **200** replay of the same key, session and trimmed alias, returning its current status | 400 `MALFORMED_JSON` / `INVALID_BODY` / `MISSING_REQUEST_KEY` / `INVALID_ALIAS` / `MISSING_SESSION`; 404 `UNKNOWN_SESSION`; 409 `KEY_CONFLICT`; 409 `CAPACITY_FULL` |
| `GET /reservations/{id}` | 200 record | 404 `UNKNOWN_RESERVATION` |
| `POST /reservations/{id}/cancel` body `{}` | 200 cancelled record, on the first and every repeat call | 404 `UNKNOWN_RESERVATION`; 400 `MALFORMED_JSON` |
| `GET /reservations` (extra) | 200 `{"reservations":[...]}`, used by the UI to list all records | none |

Errors always use the form `{"error":{"code":"…","message":"…"}}` with a 4xx status. An unexpected server error returns 500 with code `INTERNAL`, and the server keeps running.

Sample request and response:

```text
POST /reservations  {"sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1"}
201 {"id":"<uuid4>","sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1","status":"active"}
```

How the rules are applied:

- Aliases are trimmed before they're stored and compared; otherwise comparison is case-sensitive.
- Request keys are globally unique and compared exactly.
- Validation happens before any state is read.
- Replay, conflict and capacity checks plus the insert run in **one transaction**, under a process-wide lock and SQLite `BEGIN IMMEDIATE`.

## UI

The page at http://127.0.0.1:8765/ works with the keyboard alone:

- **Seat table:** a labelled table that reads `/sessions`.
- **Booking form:** a session dropdown, an alias field and a request key field.
  - The key is pre-filled with a random value and has a "New key" button.
  - After a rejection or network failure the key is **kept**, so a retry replays the same request instead of booking twice.
- **Reservations table:** reads `/reservations` and has a Cancel button for each active reservation.
- **Status line:** announced to screen readers, showing errors and confirmations.
- **Source of truth:** a success message appears only after the API confirms, and every number is read back from the server.

## Known failures, gaps and unexecuted checks

- **Concurrency:** this is bounded evidence only. The tests use 10 attempts and the shared verifier uses 10 batches of 10. This doesn't prove the app is free of every race, and running several processes against one `DATA_DIR` wasn't tested beyond SQLite's own lock.
- **UI:** not covered by automated tests beyond the page being served with labelled controls. UI agreement for AC-02, AC-03 and AC-07 was checked by hand and is recorded in the evidence manifest.
- **Platforms:** tested only on Windows 11 with CPython 3.14.4. macOS and Linux weren't tried.
- **Coverage:** not measured. No coverage tool was run.
- **Not built:** a waitlist, search and authentication, all out of scope.
- **Request keys:** whitespace-only keys such as `" "` are accepted as non-empty strings, following the PRD wording, "non-empty string".

The PR URL, frozen full commit, snapshot sourceId and archive SHA-256 are recorded in the PR and the evidence manifest, not in this file.
