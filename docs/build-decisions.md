# Build decisions

Decisions made so far for the Session Seat Desk build. Change a decision here before changing the code that depends on it.

## Stack

- **Language:** Python 3.13.3 from the project venv at `.venv/` (`.venv/bin/python`). All app and test commands run through this interpreter. No other Python.
- **Test runner:** pytest 9.2.0, installed into `.venv`.
- **HTTP:** standard library `http.server` (`ThreadingHTTPServer`), as in the starter.
- **Storage:** a local JSON file, not SQLite. The PRD allows "SQLite or a local file". Writes go to a temp file and are moved into place atomically (`os.replace`), and an in-process lock serialises reservation writes so capacity checks and inserts happen together.
- **UI:** a plain HTML page served by the app, calling the JSON API.

## Working agreement

- Test-first, one test at a time: write one failing test, see it fail for the right reason, make it pass, then refactor.
- Tests drive the app through its HTTP interface and run it as a real subprocess, with a temporary `DATA_DIR` and `PORT`. A restart test stops the process and starts it again.
- Each test starts from a fresh reset of its own fixture directory.

## Layout

All app code, tests and experiments live in `starter-python/` (the declared app directory).

- `tests/unit/test_<module>.py`: unit tests, one file per code module, same name. Marked `unit` automatically.
- `tests/acceptance/test_ac<nn>_<topic>.py`: one file per PRD criterion, run against a real process. Marked `acceptance` automatically.
- `tests/support/`: the harness (`fixture_app.py`), shared by acceptance tests.
- `experiments/exp_<question>.py`: explorations. Not collected by pytest.

Commands, from `starter-python/`:

- All tests: `../.venv/bin/python -m pytest`
- Unit only: `../.venv/bin/python -m pytest tests/unit`
- Acceptance only: `../.venv/bin/python -m pytest -m acceptance`

## Locations

- App directory: `starter-python/` (declared app directory for submission).
- Acceptance criteria: `docs/acceptance-criteria.md`.
- Fixture state: under `DATA_DIR` only. Never the repository root or a real database.

## Open

- Whether the UI check is automated (for example, a simple HTML and DOM test) or manual with recorded steps.
