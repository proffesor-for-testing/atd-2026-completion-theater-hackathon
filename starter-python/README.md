# Optional Python scaffold

Python 3.11+ with standard library only. No pip install, API key, Docker, database server or deployment is required. Any other stack is welcome. This scaffold supplies transport, static-page serving, a fixture schema and explicit reset. **All scored reservation behavior is deliberately unimplemented.**

From this directory:

```sh
python3 app.py --reset
python3 app.py
```

On Windows replace `python3` with `py -3`. Open http://127.0.0.1:8765 . Stop with Ctrl+C. Restart with the same command **without** --reset to preserve state. The placeholder UI and /health do not satisfy the PRD.

The default state is .state/seats.db under this directory. DATA_DIR changes the fixture directory and PORT changes the listener port. Reset refuses an existing database without the matching fixture ownership marker. Use a new directory for every experiment; never point it at a real database.

Implement the API in app.py or split it into modules. Handle overlapping requests safely. Replace the static page with actual API-backed state. Do not show a successful reservation until the API confirms it. Basic labels, keyboard access and visible error messages belong in the basic UI, not in optional creativity work.

```sh
python3 -m unittest -v test_app
```

This starts RED on purpose. A placeholder health test must not become your only app test. Replace the sentinel with meaningful tests, including rejected input, replay and restart. Passing repository helper tests means only that the helper tools work, not that your app works.

The adapter.json file tells the shared verifier how to start/reset your app. Keep it synchronized with your actual commands and response field names. `{python}` resolves to the verifier's Python interpreter, including on Windows.
