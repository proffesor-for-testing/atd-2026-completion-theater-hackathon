# Acceptance tests

One file per PRD criterion, named `test_ac<nn>_<topic>.py`. Each runs the app as a real process through `support/fixture_app.py` and checks only observable behaviour: HTTP responses, the stored state read back independently, and restarts.

Rules:

- Use the `app` fixture from `tests/conftest.py`. It gives a freshly reset instance with its own state directory.
- Never reset between the stop and restart steps of AC-07.
- Assert on the status code and the JSON body. Never read internal modules.
- Keep one criterion per file. Add one test at a time, red first.

Run only these: `.venv/bin/python -m pytest -m acceptance` from `starter-python/`.
