---
name: atdd-workflow
description: The acceptance-test-driven loop for this repo. Use it whenever you start work on any acceptance criterion (AC-xx) or feature, write or fix a test, or are about to write production code, even for a "quick" change, because every code change must trace back to an AC test.
---

# ATDD loop

Every behaviour in this repo exists because an AC in `docs/acceptance-criteria.md` asks for it, and every AC is pinned down by an acceptance test. That's what lets several people (and several Claude sessions) work in parallel within the time box without breaking each other's features. It is also the evidence the auditors and judges score.

## The loop (one AC at a time)

1. **Pick** the next `todo` AC (by the build order, or ask). Set its status to `red` in the AC table.
2. **Write the acceptance test first** in `starter-python/tests/acceptance/`, named after the ID, e.g. `test_ac03_reservation.py`. Test through HTTP against the real process (`tests.support.RunningApp`, which runs the app as a subprocess with a temp `DATA_DIR` on a free port), never by importing `app.py` internals. Structure it as Given / When / Then:
   ```python
   class AC03Reservation(unittest.TestCase):
       def test_ac03_reserve_ada_k1_returns_active_and_readback_matches(self):
           # Given a freshly reset app
           with RunningApp() as app:
               # When Ada reserves CT-101 with key K1
               status, body = app.request('POST', '/reservations',
                   {'sessionId': 'CT-101', 'attendeeAlias': 'Ada', 'requestKey': 'K1'})
               # Then it is active, readable by ID, and CT-101 has 1 seat left
               self.assertEqual(status, 201)
               self.assertEqual(body['status'], 'active')
               self.assertEqual(app.request('GET', '/reservations/' + body['id']), (200, body))
   ```
   For AC-07, call `app.stop()` then `app.start()` (no reset) inside the same `with`. For AC-04, fire requests from a `concurrent.futures.ThreadPoolExecutor`.
3. **Watch it fail:** from `starter-python/`, run `python -m unittest discover -s tests/acceptance -t . -v`. It must fail on an assertion. A failure caused by an import or config error proves nothing, so fix the wiring first.
4. **Make it pass** with the simplest code that works. Drop to unit TDD (`starter-python/tests/unit/`, red → green) only for logic with branches or edge cases, such as alias trimming, key-conflict rules or validation. Plain wiring doesn't need unit tests.
5. **Refactor** while everything is green: `python -m unittest discover -s tests -t . -v`.
6. **Finish** using `definition-of-done`, then commit using `git-workflow`.

## Rules of thumb
- One AC in flight per person. Finish or abandon it before starting another.
- Assert on **independent readback** (GET `/sessions`, GET `/reservations/{id}`), not only on the POST response. A response that disagrees with storage is the "Ghost Database" pattern the auditors hunt for.
- For "no state change" claims (AC-04/05b/08), assert the counts before and after.
- If an AC is ambiguous, encode the assumption in the test and add it to `## Assumptions`; don't stop to ask.
- Never delete, skip or weaken an existing AC test to make yours pass ("Test Theater"). If two ACs conflict, record the conflict as an assumption and tell the team.
