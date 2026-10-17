# Builder verification checklist

Team: ____________________  Verifier: ____________________

Frozen source checksum or full commit: _______________________________________

Verification window: 21:40–22:00. Fixes are allowed until 21:55. Freeze source and tests at 21:55; package evidence during the final five minutes. Do not add features during this round.

## Evidence rules

Record a result for every row: PASS, FAIL or NOT RUN. Add the evidence class REPORTED, STATIC or EXECUTED. Only an EXECUTED PASS earns working-app points. A static code inspection or an agent's claim is useful context, but cannot establish runtime success. A deliberate rejection is a PASS when rejection and unchanged state are the expected behavior.

Run evidence against a source content hash before and after the check. Earlier receipts count only when both hashes equal the final frozen source identity. If the source changes, rerun affected checks. The shared verifier records this binding; no claim can be rescued by a later hash alone.

For each executed check capture the criterion ID, source identity, command or UI steps, expected result, actual result, status/exit code, timestamp and artifact path. Screenshots help with UI behavior; keep raw responses and test logs too. Redact secrets before sharing. Do not use coverage percentages as a verdict that the app works.

## Functional verification

Use a fresh fixture reset at the start of each scenario. Do not reset inside a scenario unless explicitly instructed. Record NOT RUN honestly when time expires.

| Check | Steps and oracle | Result / class / evidence path |
| --- | --- | --- |
| AC-01 | Follow README from a fresh source copy, install documented dependencies, start app and open UI. No builder account or hidden service. | __________________ |
| AC-02 | Reset fixture. GET /sessions and inspect UI. CT-101: capacity 2, active 0, remaining 2. CT-102: 3, 0, 3. | __________________ |
| AC-03 | Reset fixture. Reserve CT-101 / Ada / K1. Save returned ID. Read it through GET /reservations/{id}; check remaining 1 and UI agreement. | __________________ |
| AC-04a | Reset. Reserve CT-101 with K1 and K2. Try K3. Expect two successes, a 4xx capacity rejection, active 2, remaining 0. | __________________ |
| AC-04b | Reset. Create one CT-101 booking. Send K2 and K3 concurrently. Expect exactly one new success and one rejection; active 2, remaining 0. Use ten bounded batches when using the shared helper. Record concurrency and limits; passing a bounded race does not prove atomicity. AC-04 requires both 04a and 04b. | __________________ |
| AC-05 | Reset. Send Ada / CT-101 / K1 twice, including a whitespace-trimmed alias replay. Same ID, active 1. Reuse K1 with a different alias and then CT-102: both conflicts, no count change. | __________________ |
| AC-06 | Reset fixture. Create CT-101 / Ada / K1 and save its ID. Cancel it. Repeat cancellation. Remaining becomes 2 and stays 2. Replay original K1 create request: same cancelled ID, still remaining 2. | __________________ |
| AC-07 | Reset. Make K1 and K2 in CT-101; cancel K1. Capture IDs, statuses, active 1, remaining 1. Stop process. Restart without reset. Fresh HTTP and UI readback must match. Record state path and PID/process restart. | __________________ |
| AC-08 | Reset. Try each invalid-input case in PRD. Capture every rejection and before/after counts for both sessions. GET /sessions must still work. | __________________ |

## Five completion theater checks

| Pattern | Investigation | Result / evidence |
| --- | --- | --- |
| Ghost Database | Show actual persisted records and state path. Restart and query again. Confirm the app reads the same store it writes. | __________________ |
| Metric Theater | Trace any test count or coverage claim to a fresh tool output. If no coverage tool ran, say coverage was not measured. | __________________ |
| Test Theater | Read one important assertion. In a disposable copy, deliberately break the behavior or expected result and rerun that test. It must fail. Restore the copy. No code mutation in the frozen baseline. | __________________ |
| False Positives | Inspect raw stdout/stderr, exit status, skipped tests and start failures. Trigger a known failing check and confirm non-zero exit. A green wrapper cannot hide failure. | __________________ |
| Uncommitted Illusion | Extract the exact handed-over archive or check out the recorded commit in a fresh disposable directory. Confirm the required files and tests are present. Local files omitted from the artifact do not count. | __________________ |

## Evidence score preparation

The judge awards six binary items, 5 points each: exact source binding; reproducible run/reset/test instructions; raw executed results including failure/skip counts and exit codes; durable-state readback; a failing negative control for a meaningful test; and an honest claim-to-evidence manifest including gaps. These assess the evidence, separately from whether the app meets each acceptance criterion.

## Final handoff

- [ ] Frozen source identity is recorded and the archive opens.
- [ ] README covers runtime, install, start, reset, test, state path and API mapping.
- [ ] Evidence manifest points to readable logs and UI evidence, not agent summaries alone.
- [ ] Known failures and unexecuted checks are visible.
- [ ] Private configuration, credentials and unrelated files are excluded.
- [ ] Auditor has a working transfer path and a disposable directory of their own.
- [ ] Any post-freeze repair is separate and cannot overwrite the judged baseline.
