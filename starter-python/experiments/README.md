# Experiments

Throwaway explorations: probing a library, checking a race, testing an idea before it becomes a test. Not part of the suite and not collected by pytest (files are named `exp_*.py`, not `test_*.py`).

- Name files `exp_<question>.py` and start each with a one-line question in the docstring.
- Run one with `../.venv/bin/python experiments/exp_<question>.py` from `starter-python/`.
- Anything that becomes a requirement moves into `tests/unit/` or `tests/acceptance/`, test first.
- Experiments may write only under a temporary directory, never the repository or a real database.
