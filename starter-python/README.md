# Team handoff README: Session Seat Desk

Team ID and members' chosen aliases: TODO (fill in before freeze)

Runtime and version: Python 3.13.3 (3.11+ expected). The app uses only the standard library.

Dependency installation command (test-only dependencies, pinned in `requirements-dev.txt`):

```sh
cd starter-python
python3 -m venv ../.venv
../.venv/bin/python -m pip install -r requirements-dev.txt
```

On Windows use `py -3` in place of `python3`, and `..\.venv\Scripts\python` in place of `../.venv/bin/python`.

Start command and local URL:

```sh
python3 app.py --reset   # first run only: creates the fixture state with CT-101 and CT-102
python3 app.py           # then open http://127.0.0.1:8765
```

Set `PORT` to change the port. Set `DATA_DIR` to change the fixture directory. The default is `.state/` under this folder.

Stop / restart instructions: stop with Ctrl+C. Restart with `python3 app.py` (no `--reset`). Restart keeps all reservations and counts. Only `--reset` seeds fresh state, and it refuses to overwrite a state file it did not create.

Reset command (fixture directory only): `python3 app.py --reset`

Test command and how its exit status is reported:

```sh
cd starter-python
../.venv/bin/python -m pytest
```

pytest exits non-zero on any failure. Skipped tests are listed in the summary (`-ra`). Subsets: `-m unit`, `-m acceptance`, `-m integration`.

State file/database path and how to inspect a record: `.state/state.json` (JSON, containing `sessions` and `reservations`). Read it with `cat .state/state.json`, or read it over HTTP with `GET /sessions` and `GET /reservations/{id}`.

API field mapping, sample request and response:

```sh
curl -s http://127.0.0.1:8765/sessions
curl -s -X POST http://127.0.0.1:8765/reservations \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"CT-101","attendeeAlias":"Ada","requestKey":"K1"}'
curl -s http://127.0.0.1:8765/reservations/<id>
curl -s -X POST http://127.0.0.1:8765/reservations/<id>/cancel -d '{}'
```

`adapter.json` maps the response fields used by the verifier. It is kept in step with the responses in `app.py`.

Fork URL and submission branch: TODO

Declared app directory (contains this README, all source, adapter and tests): `starter-python/`

PR URL and frozen full commit are recorded in the PR / evidence manifest after the final commit, not by a circular self-referencing commit. Snapshot sourceId and archive SHA-256 are recorded alongside them: TODO

Known failures, missing features and unexecuted checks:

Implemented and covered by tests: seeded sessions and `GET /sessions` (AC-02 API), reservation create and read (AC-03), capacity rejection and concurrent single-seat race (AC-04), idempotent replay and key conflict (AC-05), cancellation and cancelled replay (AC-06), restart durability (AC-07), malformed JSON and missing or invalid fields (AC-08 partly), corrupt state reported as `STATE_CORRUPT`, the demo-data loader, and a basic page with a reservation form, seat counts, cancel controls, and a visible error region.

Not finished (open items in `docs/loop-todo.md` and `docs/UI_todo.md`):
- AC-01: no check yet that these steps work from a clean copy with no builder account.
- AC-02 and AC-03 UI: no acceptance test yet that the page counts match `GET /sessions` after a reservation.
- AC-03: no test yet for an unknown `GET /reservations/{id}` on the 4xx path.
- AC-08: no test yet that the process stays available after each rejected request.
- Reservation IDs and request keys are not yet checked for uniqueness across sessions.
- AC-09 (proposed criterion, pending ruling in the docs): the UI error region exists, but failures after a rejected action and the "UI still accepts actions" check are not yet tested.
- Browser (DOM) checks are manual and not automated.

Configuration names belong in .env.example. Never include values for private credentials. Document any local model or tool dependency needed to BUILD, separately from dependencies needed to RUN the app. The judge must not need your AI account.

No runtime secrets or model credentials are needed. The app runs without network access.
