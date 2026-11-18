---
name: definition-of-done
description: The checklist that decides when an acceptance criterion counts as done, plus the pre-freeze and demo check. Use it whenever you are about to mark an AC done, say a feature is finished, or prepare for the 21:55 freeze, the PR submission or the demo.
---

# Definition of done

An AC is done when an auditor from another team could watch it work on the frozen commit. "Code written" is not done, and claiming done without that evidence is the "Completion Theater" this event punishes.

## Per AC (all from `starter-python/`)
1. `python -m unittest discover -s tests/acceptance -t . -v`: the AC's test passes.
2. `python -m unittest discover -s tests -t . -v`: the **whole** suite passes, so nothing else broke. Check the exit status; no skipped tests.
3. `python -m compileall -q .`: clean.
4. Demo path: `python app.py --reset` (in a scratch `DATA_DIR`), then `python app.py`, and exercise the AC once by hand: open http://127.0.0.1:8765 and use `curl` against the API. Confirm the UI and `GET /sessions` agree. Tests can pass while the real app is miswired.
5. If response field names changed, update `adapter.json` and run the shared verifier (`tools/README.md`).
6. In `docs/acceptance-criteria.md`, set the status to `done` and fill in the Test column.
7. Committed and pushed per `git-workflow`.

## Before freeze (from ~21:40)
- Stop starting new ACs. Finish or revert whatever is in flight so the branch is green.
- Run a fresh clone or clean `DATA_DIR`: reset, start, and see the UI with two sessions.
- `starter-python/README.md` lists the run, reset and test commands, the Python version, the state location (`DATA_DIR/seats.db`), the API field mapping (`adapter.json`) and **known gaps**. Honest gaps earn evidence points, while hidden ones lose audit points.
- Run the AC-07 restart by hand once: one active and one cancelled reservation survive stop and start without a reset.
- Freeze and submit per `git-workflow`.
