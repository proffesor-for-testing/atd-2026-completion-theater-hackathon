# Completion Theater — full submission review

Updated 2026-11-18T23:11:04.872378+00:00. All nine submissions (#4–#12) were run; only outgoing cross-team audit C1–C4 is deferred at the organizer’s request. Individuals are compared separately, including entries called Team A. This report supersedes earlier evidence-only zero/NOT RUN estimates.

Scores below are **AI recommendations awaiting named human adjudication**, using published rules 1.1: A /40, B /30, C /20, D /10. Compare A+B+D **out of 80**, without rescaling; final /100 and event ranking remain pending. PR #11 is an explicitly labelled AI rehearsal and is separate. Unadjudicated event score files retain zero/NOT RUN placeholders; those are not the app results.

[Rubric](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/blob/9ceda374014af3e3db08fed97a42fa4aabe1f8e4/docs/04-Scoring-Sheets.md) · [Acceptance criteria](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/blob/9ceda374014af3e3db08fed97a42fa4aabe1f8e4/docs/01-Starter-PRD.md) · [All 180 row records](criterion-results.csv) · [Source identities](source-identities.csv) · [Test counts](test-summary.csv) · [Screenshot hashes](screenshot-sha256.csv)

| PR / individual | App /40 | Evidence /30 | Audit /20 | Creativity /10 | Proposed /80 | Interpretation still open |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| [#4](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/pull/4) JonasHUL | 40 | 30 | Deferred | 10 | **80** | Human approval/eligibility pending |
| [#5](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/pull/5) jameskblack | 40 | 25 | Deferred | 5 | **70** | Human approval/eligibility pending |
| [#6](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/pull/6) acoetzeect (Annie) | 40 | 30 | Deferred | 10 | **80** | Human approval/eligibility pending |
| [#7](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/pull/7) altlv | 40 | 30 | Deferred | 10 | **80** | Human approval/eligibility pending |
| [#8](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/pull/8) saviauk | 40 | 30 | Deferred | 5 | **75** | D2 +5 if extra concurrent-key invariant accepted |
| [#9](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/pull/9) bitcoder | 35 | 30 | Deferred | 5 | **70** | A3 +5 if canonical-scenario interpretation accepted |
| [#10](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/pull/10) TomislavPrsa | 40 | 30 | Deferred | 0 | **70** | Human approval/eligibility pending |
| [#12](https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/pull/12) workroomprds | 35 | 25 | Deferred | 10 | **70** | A3 +5 if canonical-scenario interpretation accepted |

**Separate PR #11 rehearsal:** A 35/40 + B 30/30 + D 5/10 = **70/80**, C deferred. A3 alternative +5 is the same disputed rule as #9/#12; no human event place is assigned.

**Commit freshness.** Repository-wide PR collection checked at 2026-11-18 23:07:49 UTC; latest submission is #12 (no newer submission returned). Eight of nine reviewed commits equal the latest head. #8 retains its declared frozen commit; the newer head changes only root/agent guidance, no app files, with identical app sourceId. All nine latest app byte sets are therefore covered.

| PR | Full commit scored | Latest PR head checked | App path |
| --- | --- | --- | --- |
| #4 | `f33e7f1666d0e96aa4c15b1c1098ecc8c7f12b89` | `f33e7f1666d0e96aa4c15b1c1098ecc8c7f12b89` | `starter-python` |
| #5 | `54bb0a8e39002a59e01a291e790d51e7272832bd` | `54bb0a8e39002a59e01a291e790d51e7272832bd` | `seat-desk` |
| #6 | `037a59ac94a0da44a1141675f02377b289771fd9` | `037a59ac94a0da44a1141675f02377b289771fd9` | `starter-python` |
| #7 | `d858b3b6230b8d888d050f1744edaa1c37a5f7da` | `d858b3b6230b8d888d050f1744edaa1c37a5f7da` | `starter-python` |
| #8 | `5b018fcfea2271a304a95d0911c59d03a97a49f4` | `4a0fdad83ec672540c45c802507faefc7372f8ac` | `starter-python` |
| #9 | `1cfb2fec9ddd7c839f9473ecbabb6d0e523a7235` | `1cfb2fec9ddd7c839f9473ecbabb6d0e523a7235` | `starter-python` |
| #10 | `cb1b59ba50ee021c8e5b51208e3067c8a08122eb` | `cb1b59ba50ee021c8e5b51208e3067c8a08122eb` | `starter-python` |
| #11 | `65d3754b5fa1b7a6d8a0f5214795693b1aa93f7b` | `65d3754b5fa1b7a6d8a0f5214795693b1aa93f7b` | `starter-python` |
| #12 | `3c35e334d0eb57d034e732f4f4aac11efda42277` | `3c35e334d0eb57d034e732f4f4aac11efda42277` | `starter-python` |

**Execution and limits.** Exact committed snapshots ran as unprivileged UID 1001 in a disposable Debian 12 ARM64 QEMU VM with no host mounts, credentials or host socket. Each app/test/browser namespace had loopback only and no external route. Python 3.11.2, SQLite 3.40.1; browser harness Playwright 1.65.2/system Chromium 156. PR #7 used Node 24.22.3, exact locked npm dependencies, Playwright 1.63.0/Chromium 153; #12 used pytest 9.2.0/xdist 3.8.0. Dependency provisioning preceded offline execution. VM timing is not a product-performance measurement.

Every app completed: documented reset/start/tests; shared API AC-02–08; 10 × 10 capacity races; separate full store reads (SQLite for #4–11, JSON for #12); exact seeded titles; all five invalid requests against empty and populated stores; active/cancelled actual process restart; browser reserve/count/error/cancel/readback; meaningful capacity negative control (0 → assertion failure/1 → restored/0). Additional identical-key/global-key races ran for all nine. These bounded trials do not prove universal race freedom. Desktop Chromium checks do not establish screen-reader, all-browser or all-device compliance.

**Primary native suites and supplements** (all raw stdout/stderr/actual exits retained):

| PR | Primary command, from declared app copy | Primary result | Supplement / limitation |
| --- | --- | --- | --- |
| #4 | `/usr/bin/python3 -m unittest -v test_acceptance test_store_check test_hardening` | 43/43 passed; 0 skipped; exit 0 | No omitted primary cases. |
| #5 | `/usr/bin/python3 -m unittest -v test_app` | 14/14 passed; 0 skipped; exit 0 | No omitted primary cases. |
| #6 | `/usr/bin/python3 -m unittest -v test_app` | 10/10 passed; 0 skipped; exit 0 | No omitted primary cases. |
| #7 | `/usr/bin/python3 -m unittest -v test_app` | 14/14 passed; 0 skipped; exit 0 | 85 provided Playwright cases: 83 pass + 2 axe timeouts, exit 1; unchanged 120s supplement 2 pass, exit 0; typecheck pass. |
| #8 | `/usr/bin/python3 -B -m unittest -v test_app` | 18/18 passed; 0 skipped; exit 0 | No omitted primary cases. |
| #9 | `/usr/bin/python3 -m unittest -v test_app test_coverage test_spec_gaps` | 46/47 passed; 1 skipped; exit 0 | Skipped binding test later 1/1 pass, no skip; original result remains 46+1. Coverage separately traced. |
| #10 | `/usr/bin/python3 -m unittest discover -s tests -t . -v` | 30/30 passed; 0 skipped; exit 0 | No omitted primary cases. |
| #11 | `/usr/bin/python3 -B -m unittest -v test_app` | 16/16 passed; 0 skipped; exit 0 | No omitted primary cases. |
| #12 | `/opt/judge/pytest/bin/python -m pytest -v` | 67/67 passed; 0 skipped; exit 0 | 67 pytest cases, -n auto retained; one read-only cache warning. |

**Supplementary accessibility scans.** Fresh-state judge-authored axe scans are bounded observations, not full accessibility certification or participant D2 credit. Incomplete checks require manual investigation; zero violations alone is not a full pass. #7’s CSP blocks judge script injection; its two provided native axe scans completed separately.

| PR | Fresh-state judge scan | Raw receipt |
| --- | --- | --- |
| #4 | 0 violations; 0 incomplete rules / 0 affected nodes | `browser/pr-4/attempt-1/browser/axe-result.json` |
| #5 | 0 violations; 0 incomplete rules / 0 affected nodes | `browser/pr-5/attempt-1/browser/axe-result.json` |
| #6 | 0 violations; 1 incomplete rules / 44 affected nodes | `browser/pr-6/attempt-1/browser/axe-result.json` |
| #7 | Judge injection blocked by script-src self CSP; provided native axe 2/2 pass | `browser/pr-7/attempt-1/results.json (results.D2-axe); additional/pr-7/a11y-timeout-supplement/a11y-supplement.json` |
| #8 | 0 violations; 0 incomplete rules / 0 affected nodes | `browser/pr-8/attempt-1/browser/axe-result.json` |
| #9 | 0 violations; 0 incomplete rules / 0 affected nodes | `browser/pr-9/attempt-1/browser/axe-result.json` |
| #10 | 0 violations; 1 incomplete rules / 1 affected nodes | `browser/pr-10/attempt-1/browser/axe-result.json` |
| #11 | 0 violations; 0 incomplete rules / 0 affected nodes | `browser/pr-11/attempt-1/browser/axe-result.json` |
| #12 | 0 violations; 0 incomplete rules / 0 affected nodes | `browser/pr-12/attempt-1/browser/axe-result.json` |

**Scoring disputes and corrections.** A space-only key (`"   "`, three U+0020 characters) is nonempty under PRD text; #9/#11/#12 reject it with 400 while six comparators accept it. The strict proposal records A3 FAIL/0 once; the named Ada/K1 scenario passes everywhere. Because AC-03 names K1 specifically, an acceptance-scenario-only ruling retaining A3 is also defensible. A human must apply the same decision to all three; no duplicate A5/A8/B/D deduction. #8 D2 is separately disputed as an extra scenario versus distinct technique. Missing builder manifests hold B6 at 0 for #5/#12; judge-generated evidence supports B1–B5 but cannot retroactively supply B6.

Initial harness problems remain preserved: #5 receipt logger could not serialize a Python set (corrected logger, fresh browser run); #7 first native browser output parent lacked write permission (fixed organizer directory before completed run); #9 independent coverage parser rejected CPython line-0 sentinel (corrected analysis of retained traces). #6 browser timeouts/hidden lookup and #8 reused image labels are disclosed per entry. None was concealed as an application defect or silently changed to PASS.

All per-entry rows below inherit that entry’s exact commit/sourceId and review/execution interval. Each row states its expected observation and actual result, evidence class and proposed binary points. `PASS / EXECUTED` is observed execution; `STATIC` assesses supplied material. NOT RUN on a missing B6 manifest or undemonstrated optional D item records absent evidence after inspection; it is not a silently omitted runnable acceptance check. C rows alone are intentionally deferred. Full commands, timestamps, receipt paths and all 180 rows are also in the CSV.

## PR #4 — JonasHUL

Commit `f33e7f1666d0e96aa4c15b1c1098ecc8c7f12b89`; app `starter-python`. SourceId `a2c26e8a525a436fdd16ac8cfbc74b64b2da33995b0aeb2926c61c03dc762df6`. Retained ZIP SHA-256 `fb69452e1c40fcd29f84b42a3f890ae2c755844df14907e5974ba9eacb5fda6f`. Review/execution interval: 2026-11-18T22:06:09.775053+00:00 to 2026-11-18T23:11:04.872378+00:00.

Pre-built-with-AI disclosure is retained for organizer eligibility review; no improvised timing penalty. The documented classic fallback passed core UI checks. A separate unmodified default view rendered the immersive WebGL room with SwiftShader and booking API/store readback passed; its supplemental result is FAIL because the driver timed out locating refreshed session cards after booking (expected remaining 1/3, got no readable value), so default-view count agreement is not qualified. This is not evidence of an observed wrong count; classic-route agreement passed.

Proposed A 40/40, B 30/30, D 10/10 = **80/80**; C deferred; final human decision pending.

| Row | Result / class | Proposed | Expected → actual; raw receipt |
| --- | --- | ---: | --- |
| A1 | PASS / EXECUTED | 5 | Cold documented start and visible usable UI. → Both seeded sessions and usable reserve/cancel controls observed. Receipt: `browser/pr-4/attempt-1/results.json`. |
| A2 | PASS / EXECUTED | 5 | Exact seeded IDs/titles, capacity/active/remaining counts, UI agrees. → CT-101: 2/0/2; CT-102: 3/0/3; independent store and visible counts agree. Receipt: `core/pr-4/shared-api/report.json; browser/pr-4/attempt-1/results.json`. |
| A3 | PASS / EXECUTED | 5 | Valid reservation, stable ID, independent GET/store, remaining 1 and UI. → Ada/CT-101/K1 creates one active record; GET/store/UI agree. Receipt: `core/pr-4/deep-api-sql/report.json; browser/pr-4/attempt-1/results.json`. |
| A4 | PASS / EXECUTED | 5 | Sequential full rejection and ten batches × ten simultaneous distinct attempts. → Sequential third create rejects; every one-seat batch has exactly one create, nine rejections, two stored active rows. Receipt: `core/pr-4/shared-api/report.json; core/pr-4/shared-store-readback.json`. |
| A5 | PASS / EXECUTED | 5 | Same-key/trimmed-alias replay; globally conflicting alias/session reject. → Original ID/status returned without extra row/seat; both conflicts reject; extra identical/conflicting-key races also pass. Receipt: `core/pr-4/deep-api-sql/report.json`. |
| A6 | PASS / EXECUTED | 5 | Cancel once, repeat cancel, replay cancelled original without reactivation. → Exactly one seat released; repeated cancel and original-key replay retain cancelled ID and unchanged store. Receipt: `core/pr-4/deep-api-sql/report.json; browser/pr-4/attempt-1/results.json`. |
| A7 | PASS / EXECUTED | 5 | Real stop/start without reset; same active/cancelled IDs/statuses/counts through HTTP/store/UI. → Different process PIDs, same store, fresh HTTP and ordinary UI readback preserve both original records. Receipt: `core/pr-4/deep-api-sql/report.json; browser/pr-4/attempt-1/results.json`. |
| A8 | PASS / EXECUTED | 5 | All five invalid requests reject clearly, no store/count change, process remains available. → Unknown session, blank alias, missing key, malformed JSON and unknown cancel reject; entire populated store unchanged. Receipt: `integrity/integrity-evidence/pr-4/report.json; core/pr-4/shared-api/report.json`. |
| B1 | PASS / EXECUTED | 5 | Exact immutable source and receipt binding. → Retained commit/app/sourceId/archive verified; executed baseline hashes unchanged; deliberate mutation isolated. Receipt: `snapshot-rechecks/pr-4.json; core/pr-4/execution-summary.json`. |
| B2 | PASS / EXECUTED | 5 | Independently reproduce documented run/reset/test procedures. → Cold app start, isolated reset, native documented test command completed; exact argv/runtime recorded. Receipt: `core/pr-4/unit-command.json; browser/pr-4/attempt-1/results.json`. |
| B3 | PASS / EXECUTED | 5 | Fresh raw test counts, failures, skips, exit status. → Primary: 43 collected, 43 passed, 0 skipped, exit 0. Supplements/initial failures are preserved below. Receipt: `core/pr-4/unit-stdout.txt; core/pr-4/unit-stderr.txt; core/pr-4/unit-command.json`. |
| B4 | PASS / EXECUTED | 5 | Readable state before/after actual same-store process restart. → Raw process PIDs, full records and counts before/after restart retained; evaluated independently of A7. Receipt: `core/pr-4/deep-api-sql/report.json; browser/pr-4/attempt-1/results.json`. |
| B5 | PASS / EXECUTED | 5 | Meaningful behavioral negative control in separate copy, restored afterward. → Provided capacity assertion: baseline exit 0; behavioral mutant exit 1 with assertion failure; restored exit 0; baseline bytes unchanged. Receipt: `core/pr-4/negative-*-command.json; core/pr-4/negative-control.diff`. |
| B6 | PASS / STATIC | 5 | Delivered builder manifest separates claims, results, FAIL and NOT RUN. → Delivered manifest/addendum separates frozen execution, earlier-source mutation results and unrun UI work. Receipt: `pr-4/attachment-1/ev-final/MANIFEST.md; attachment-2/ui-frozen/README.md`. |
| C1 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C2 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C3 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C4 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| D1 | PASS / EXECUTED | 5 | Demonstrated concrete optional user benefit. → Alias search/profile locates a reservation without its ID; normal UI demonstration and unchanged stored state. Receipt: `browser/pr-4/attempt-1/results.json`. |
| D2 | PASS / EXECUTED | 5 | Demonstrated provided additional verification technique beyond mandatory checks. → Provided audit-chain/store checker: six tests detect ghost rows, silent reactivation and rewritten history. Receipt: `core/pr-4/unit-stderr.txt`. |

Screenshots: [fresh-usable-ui](screenshots/pr-4/attempt-1-browser-fresh-usable-ui.png); [reserved-Ada](screenshots/pr-4/attempt-1-browser-reserved-Ada.png); [restart-after-active](screenshots/pr-4/attempt-1-browser-restart-after-active.png); [restart-after-cancelled](screenshots/pr-4/attempt-1-browser-restart-after-cancelled.png); [ordinary-default-fresh](screenshots/pr-4/default-view-1-browser-ordinary-default-fresh.png); [D1-find-attendee](screenshots/pr-4/attempt-1-browser-D1-find-attendee.png).

## PR #5 — jameskblack

Commit `54bb0a8e39002a59e01a291e790d51e7272832bd`; app `seat-desk`. SourceId `89258831a07927876bff6337634e6f9c3f906dca9fd0102e3aac2146f9c2227a`. Retained ZIP SHA-256 `2d15b2382838883422d7953fce8738000a72f45f5d83897e3e35a9a7dcce1a6c`. Review/execution interval: 2026-11-18T21:58:14.632538+00:00 to 2026-11-18T23:11:04.872378+00:00.

This is the implemented seat-desk app, not the untouched starter-python scaffold. Earlier zero/NOT RUN estimates are superseded by actual execution. Original freeze/deadline receipt is unestablished; user authorized review of available individual submissions.

Proposed A 40/40, B 25/30, D 5/10 = **70/80**; C deferred; final human decision pending.

| Row | Result / class | Proposed | Expected → actual; raw receipt |
| --- | --- | ---: | --- |
| A1 | PASS / EXECUTED | 5 | Cold documented start and visible usable UI. → Both seeded sessions and usable reserve/cancel controls observed. Receipt: `browser/pr-5/attempt-1/results.json`. |
| A2 | PASS / EXECUTED | 5 | Exact seeded IDs/titles, capacity/active/remaining counts, UI agrees. → CT-101: 2/0/2; CT-102: 3/0/3; independent store and visible counts agree. Receipt: `core/pr-5/shared-api/report.json; browser/pr-5/attempt-1/results.json`. |
| A3 | PASS / EXECUTED | 5 | Valid reservation, stable ID, independent GET/store, remaining 1 and UI. → Ada/CT-101/K1 creates one active record; GET/store/UI agree. Receipt: `core/pr-5/deep-api-sql/report.json; browser/pr-5/attempt-1/results.json`. |
| A4 | PASS / EXECUTED | 5 | Sequential full rejection and ten batches × ten simultaneous distinct attempts. → Sequential third create rejects; every one-seat batch has exactly one create, nine rejections, two stored active rows. Receipt: `core/pr-5/shared-api/report.json; core/pr-5/shared-store-readback.json`. |
| A5 | PASS / EXECUTED | 5 | Same-key/trimmed-alias replay; globally conflicting alias/session reject. → Original ID/status returned without extra row/seat; both conflicts reject; extra identical/conflicting-key races also pass. Receipt: `core/pr-5/deep-api-sql/report.json`. |
| A6 | PASS / EXECUTED | 5 | Cancel once, repeat cancel, replay cancelled original without reactivation. → Exactly one seat released; repeated cancel and original-key replay retain cancelled ID and unchanged store. Receipt: `core/pr-5/deep-api-sql/report.json; browser/pr-5/attempt-1/results.json`. |
| A7 | PASS / EXECUTED | 5 | Real stop/start without reset; same active/cancelled IDs/statuses/counts through HTTP/store/UI. → Different process PIDs, same store, fresh HTTP and ordinary UI readback preserve both original records. Receipt: `core/pr-5/deep-api-sql/report.json; browser/pr-5/attempt-1/results.json`. |
| A8 | PASS / EXECUTED | 5 | All five invalid requests reject clearly, no store/count change, process remains available. → Unknown session, blank alias, missing key, malformed JSON and unknown cancel reject; entire populated store unchanged. Receipt: `integrity/integrity-evidence/pr-5/report.json; core/pr-5/shared-api/report.json`. |
| B1 | PASS / EXECUTED | 5 | Exact immutable source and receipt binding. → Retained commit/app/sourceId/archive verified; executed baseline hashes unchanged; deliberate mutation isolated. Receipt: `snapshot-rechecks/pr-5.json; core/pr-5/execution-summary.json`. |
| B2 | PASS / EXECUTED | 5 | Independently reproduce documented run/reset/test procedures. → Cold app start, isolated reset, native documented test command completed; exact argv/runtime recorded. Receipt: `core/pr-5/unit-command.json; browser/pr-5/attempt-1/results.json`. |
| B3 | PASS / EXECUTED | 5 | Fresh raw test counts, failures, skips, exit status. → Primary: 14 collected, 14 passed, 0 skipped, exit 0. Supplements/initial failures are preserved below. Receipt: `core/pr-5/unit-stdout.txt; core/pr-5/unit-stderr.txt; core/pr-5/unit-command.json`. |
| B4 | PASS / EXECUTED | 5 | Readable state before/after actual same-store process restart. → Raw process PIDs, full records and counts before/after restart retained; evaluated independently of A7. Receipt: `core/pr-5/deep-api-sql/report.json; browser/pr-5/attempt-1/results.json`. |
| B5 | PASS / EXECUTED | 5 | Meaningful behavioral negative control in separate copy, restored afterward. → Provided capacity assertion: baseline exit 0; behavioral mutant exit 1 with assertion failure; restored exit 0; baseline bytes unchanged. Receipt: `core/pr-5/negative-*-command.json; core/pr-5/negative-control.diff`. |
| B6 | NOT RUN / STATIC | 0 | Delivered builder manifest separates claims, results, FAIL and NOT RUN. → No delivered result/receipt manifest; blank PR template and README reference to a missing manifest. New judge receipts do not create builder B6 credit. Receipt: `pr-5/comments.json; source-seat-desk/README.md`. |
| C1 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C2 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C3 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C4 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| D1 | NOT RUN / STATIC | 0 | Demonstrated concrete optional user benefit. → No distinct optional user improvement demonstrated beyond required reserve/read/cancel/error controls. Receipt: `browser/pr-5/attempt-1/results.json`. |
| D2 | PASS / EXECUTED | 5 | Demonstrated provided additional verification technique beyond mandatory checks. → Provided reference-model tests: three seeds × 40 operations compare API/store invariants after each transition. Receipt: `core/pr-5/unit-stderr.txt`. |

Screenshots: [fresh-usable-ui](screenshots/pr-5/attempt-1-browser-fresh-usable-ui.png); [reserved-Ada](screenshots/pr-5/attempt-1-browser-reserved-Ada.png); [restart-after-active](screenshots/pr-5/attempt-1-browser-restart-after-active.png); [restart-after-cancelled](screenshots/pr-5/attempt-1-browser-restart-after-cancelled.png).

## PR #6 — acoetzeect (Annie)

Commit `037a59ac94a0da44a1141675f02377b289771fd9`; app `starter-python`. SourceId `6e60ffc98f525434d7a8e959fab9f18c9ff106611d2f8dec8f9e72f5bbbffa79`. Retained ZIP SHA-256 `592702338897bbc1b151a254f999caddcd6dce0b003104db8f71dae33b59e7b7`. Review/execution interval: 2026-11-18T22:08:46.976430+00:00 to 2026-11-18T23:11:04.872378+00:00.

Initial browser navigation/cancel timeouts and a hidden Technical details lookup were retained. Only the affected checks were repeated with a larger disclosed budget and the normal Technical details control; no application change.

Proposed A 40/40, B 30/30, D 10/10 = **80/80**; C deferred; final human decision pending.

| Row | Result / class | Proposed | Expected → actual; raw receipt |
| --- | --- | ---: | --- |
| A1 | PASS / EXECUTED | 5 | Cold documented start and visible usable UI. → Both seeded sessions and usable reserve/cancel controls observed. Receipt: `browser/pr-6/attempt-2/results.json`. |
| A2 | PASS / EXECUTED | 5 | Exact seeded IDs/titles, capacity/active/remaining counts, UI agrees. → CT-101: 2/0/2; CT-102: 3/0/3; independent store and visible counts agree. Receipt: `core/pr-6/shared-api/report.json; browser/pr-6/attempt-1/results.json`. |
| A3 | PASS / EXECUTED | 5 | Valid reservation, stable ID, independent GET/store, remaining 1 and UI. → Ada/CT-101/K1 creates one active record; GET/store/UI agree. Receipt: `core/pr-6/deep-api-sql/report.json; browser/pr-6/attempt-1/results.json`. |
| A4 | PASS / EXECUTED | 5 | Sequential full rejection and ten batches × ten simultaneous distinct attempts. → Sequential third create rejects; every one-seat batch has exactly one create, nine rejections, two stored active rows. Receipt: `core/pr-6/shared-api/report.json; core/pr-6/shared-store-readback.json`. |
| A5 | PASS / EXECUTED | 5 | Same-key/trimmed-alias replay; globally conflicting alias/session reject. → Original ID/status returned without extra row/seat; both conflicts reject; extra identical/conflicting-key races also pass. Receipt: `core/pr-6/deep-api-sql/report.json`. |
| A6 | PASS / EXECUTED | 5 | Cancel once, repeat cancel, replay cancelled original without reactivation. → Exactly one seat released; repeated cancel and original-key replay retain cancelled ID and unchanged store. Receipt: `core/pr-6/deep-api-sql/report.json; browser/pr-6/attempt-2/results.json`. |
| A7 | PASS / EXECUTED | 5 | Real stop/start without reset; same active/cancelled IDs/statuses/counts through HTTP/store/UI. → Different process PIDs, same store, fresh HTTP and ordinary UI readback preserve both original records. Receipt: `core/pr-6/deep-api-sql/report.json; browser/pr-6/attempt-2/results.json`. |
| A8 | PASS / EXECUTED | 5 | All five invalid requests reject clearly, no store/count change, process remains available. → Unknown session, blank alias, missing key, malformed JSON and unknown cancel reject; entire populated store unchanged. Receipt: `integrity/integrity-evidence/pr-6/report.json; core/pr-6/shared-api/report.json`. |
| B1 | PASS / EXECUTED | 5 | Exact immutable source and receipt binding. → Retained commit/app/sourceId/archive verified; executed baseline hashes unchanged; deliberate mutation isolated. Receipt: `snapshot-rechecks/pr-6.json; core/pr-6/execution-summary.json`. |
| B2 | PASS / EXECUTED | 5 | Independently reproduce documented run/reset/test procedures. → Cold app start, isolated reset, native documented test command completed; exact argv/runtime recorded. Receipt: `core/pr-6/unit-command.json; browser/pr-6/attempt-1/results.json`. |
| B3 | PASS / EXECUTED | 5 | Fresh raw test counts, failures, skips, exit status. → Primary: 10 collected, 10 passed, 0 skipped, exit 0. Supplements/initial failures are preserved below. Receipt: `core/pr-6/unit-stdout.txt; core/pr-6/unit-stderr.txt; core/pr-6/unit-command.json`. |
| B4 | PASS / EXECUTED | 5 | Readable state before/after actual same-store process restart. → Raw process PIDs, full records and counts before/after restart retained; evaluated independently of A7. Receipt: `core/pr-6/deep-api-sql/report.json; browser/pr-6/attempt-2/results.json`. |
| B5 | PASS / EXECUTED | 5 | Meaningful behavioral negative control in separate copy, restored afterward. → Provided capacity assertion: baseline exit 0; behavioral mutant exit 1 with assertion failure; restored exit 0; baseline bytes unchanged. Receipt: `core/pr-6/negative-*-command.json; core/pr-6/negative-control.diff`. |
| B6 | PASS / STATIC | 5 | Delivered builder manifest separates claims, results, FAIL and NOT RUN. → Delivered manifest identifies AI actors, old-source exclusions, intermediate failures and unmeasured coverage. Receipt: `pr-6/attachment-1/evidence-pack/EVIDENCE-MANIFEST.md`. |
| C1 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C2 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C3 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C4 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| D1 | PASS / EXECUTED | 5 | Demonstrated concrete optional user benefit. → Technical Replay and HTTP activity help reconcile retry behavior: same record/status, no extra seat. Receipt: `browser/pr-6/attempt-1/results.json`. |
| D2 | PASS / EXECUTED | 5 | Demonstrated provided additional verification technique beyond mandatory checks. → Judge reproduced the participant’s documented protocol (not a supplied executable multiprocess test): two real app processes share SQLite, one seed booking, then twenty attempts yield one create/nineteen capacity rejections and two active rows. Distinct question: cross-process coordination, not additional race volume. Receipt: `additional/pr-6/additional-summary.json`. |

Screenshots: [fresh-usable-ui](screenshots/pr-6/attempt-2-browser-fresh-usable-ui.png); [reserved-Ada](screenshots/pr-6/attempt-1-browser-reserved-Ada.png); [restart-after-active](screenshots/pr-6/attempt-2-browser-restart-after-active.png); [restart-after-cancelled](screenshots/pr-6/attempt-2-browser-restart-after-cancelled.png); [D1-replay-http-activity](screenshots/pr-6/attempt-1-browser-D1-replay-http-activity.png).

## PR #7 — altlv

Commit `d858b3b6230b8d888d050f1744edaa1c37a5f7da`; app `starter-python`. SourceId `b5a92ebbad9b83d7b57512072e4b840786679accc65d5b50990c99c16b7aae08`. Retained ZIP SHA-256 `50887a38abd3a0926b6170c014c5866fab4468ab0bceaea3e4c17c76b28593f6`. Review/execution interval: 2026-11-18T22:10:27.529768+00:00 to 2026-11-18T23:11:04.872378+00:00.

Python suite passed 14/14. Full provided Playwright suite: 83 passed, two axe timeouts, zero skipped, exit 1. Separate unchanged two-test axe run at 120s: 2/2 passed, exit 0. Exact lockfile dependencies and matching Chromium were preprovisioned; one worker/retries 0, all 85 cases retained; typecheck passed.

Proposed A 40/40, B 30/30, D 10/10 = **80/80**; C deferred; final human decision pending.

| Row | Result / class | Proposed | Expected → actual; raw receipt |
| --- | --- | ---: | --- |
| A1 | PASS / EXECUTED | 5 | Cold documented start and visible usable UI. → Both seeded sessions and usable reserve/cancel controls observed. Receipt: `browser/pr-7/attempt-1/results.json`. |
| A2 | PASS / EXECUTED | 5 | Exact seeded IDs/titles, capacity/active/remaining counts, UI agrees. → CT-101: 2/0/2; CT-102: 3/0/3; independent store and visible counts agree. Receipt: `core/pr-7/shared-api/report.json; browser/pr-7/attempt-1/results.json`. |
| A3 | PASS / EXECUTED | 5 | Valid reservation, stable ID, independent GET/store, remaining 1 and UI. → Ada/CT-101/K1 creates one active record; GET/store/UI agree. Receipt: `core/pr-7/deep-api-sql/report.json; browser/pr-7/attempt-1/results.json`. |
| A4 | PASS / EXECUTED | 5 | Sequential full rejection and ten batches × ten simultaneous distinct attempts. → Sequential third create rejects; every one-seat batch has exactly one create, nine rejections, two stored active rows. Receipt: `core/pr-7/shared-api/report.json; core/pr-7/shared-store-readback.json`. |
| A5 | PASS / EXECUTED | 5 | Same-key/trimmed-alias replay; globally conflicting alias/session reject. → Original ID/status returned without extra row/seat; both conflicts reject; extra identical/conflicting-key races also pass. Receipt: `core/pr-7/deep-api-sql/report.json`. |
| A6 | PASS / EXECUTED | 5 | Cancel once, repeat cancel, replay cancelled original without reactivation. → Exactly one seat released; repeated cancel and original-key replay retain cancelled ID and unchanged store. Receipt: `core/pr-7/deep-api-sql/report.json; browser/pr-7/attempt-1/results.json`. |
| A7 | PASS / EXECUTED | 5 | Real stop/start without reset; same active/cancelled IDs/statuses/counts through HTTP/store/UI. → Different process PIDs, same store, fresh HTTP and ordinary UI readback preserve both original records. Receipt: `core/pr-7/deep-api-sql/report.json; browser/pr-7/attempt-1/results.json`. |
| A8 | PASS / EXECUTED | 5 | All five invalid requests reject clearly, no store/count change, process remains available. → Unknown session, blank alias, missing key, malformed JSON and unknown cancel reject; entire populated store unchanged. Receipt: `integrity/integrity-evidence/pr-7/report.json; core/pr-7/shared-api/report.json`. |
| B1 | PASS / EXECUTED | 5 | Exact immutable source and receipt binding. → Retained commit/app/sourceId/archive verified; executed baseline hashes unchanged; deliberate mutation isolated. Receipt: `snapshot-rechecks/pr-7.json; core/pr-7/execution-summary.json`. |
| B2 | PASS / EXECUTED | 5 | Independently reproduce documented run/reset/test procedures. → Cold app start, isolated reset, native documented test command completed; exact argv/runtime recorded. Receipt: `core/pr-7/unit-command.json; browser/pr-7/attempt-1/results.json`. |
| B3 | PASS / EXECUTED | 5 | Fresh raw test counts, failures, skips, exit status. → Primary: 14 collected, 14 passed, 0 skipped, exit 0. Supplements/initial failures are preserved below. Receipt: `core/pr-7/unit-stdout.txt; core/pr-7/unit-stderr.txt; core/pr-7/unit-command.json`. |
| B4 | PASS / EXECUTED | 5 | Readable state before/after actual same-store process restart. → Raw process PIDs, full records and counts before/after restart retained; evaluated independently of A7. Receipt: `core/pr-7/deep-api-sql/report.json; browser/pr-7/attempt-1/results.json`. |
| B5 | PASS / EXECUTED | 5 | Meaningful behavioral negative control in separate copy, restored afterward. → Provided capacity assertion: baseline exit 0; behavioral mutant exit 1 with assertion failure; restored exit 0; baseline bytes unchanged. Receipt: `core/pr-7/negative-*-command.json; core/pr-7/negative-control.diff`. |
| B6 | PASS / STATIC | 5 | Delivered builder manifest separates claims, results, FAIL and NOT RUN. → Delivered comment distinguishes claims, execution and limits; missing old raw attachments were replaced for B1–B5 by fresh judge runs. Receipt: `PR comment 6991450805; pr-7/comments.json`. |
| C1 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C2 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C3 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C4 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| D1 | PASS / EXECUTED | 5 | Demonstrated concrete optional user benefit. → Session/status filters narrow a real mixed reservation list without changing the store. Receipt: `browser/pr-7/attempt-1/results.json`. |
| D2 | PASS / EXECUTED | 5 | Demonstrated provided additional verification technique beyond mandatory checks. → Provided axe scans of populated/cancelled and visible-error/modal states completed; original 30s timeouts retained, unchanged scans passed with explicit 120s supplement. Receipt: `additional/pr-7/a11y-timeout-supplement/a11y-supplement.json`. |

Screenshots: [fresh-usable-ui](screenshots/pr-7/attempt-1-browser-fresh-usable-ui.png); [reserved-Ada](screenshots/pr-7/attempt-1-browser-reserved-Ada.png); [restart-after-active](screenshots/pr-7/attempt-1-browser-restart-after-active.png); [restart-after-cancelled](screenshots/pr-7/attempt-1-browser-restart-after-cancelled.png); [D1-record-filters](screenshots/pr-7/attempt-1-browser-D1-record-filters.png).

## PR #8 — saviauk

Commit `5b018fcfea2271a304a95d0911c59d03a97a49f4`; app `starter-python`. SourceId `fe0142c21f84ff72cc34bf09197e0d8baefa3fe8e2ae47610a30f8c18d815d9e`. Retained ZIP SHA-256 `c6da4d4af9db0b1dc57b5ffab257c26d965c02ddbcf4677d17bd3d17910cf2ef`. Review/execution interval: 2026-11-18T22:11:47.370313+00:00 to 2026-11-18T23:11:04.872378+00:00.

Latest commit differs only outside starter-python; sourceId is identical. Two cancellation screenshot names were overwritten during a later D1 fixture; raw assertions remain valid and an explicit fresh cancellation recapture supplies unambiguous images. Conservative D2 interpretation differs from earlier provisional +5; human dispute retained.

Proposed A 40/40, B 30/30, D 5/10 = **75/80**; C deferred; final human decision pending.

| Row | Result / class | Proposed | Expected → actual; raw receipt |
| --- | --- | ---: | --- |
| A1 | PASS / EXECUTED | 5 | Cold documented start and visible usable UI. → Both seeded sessions and usable reserve/cancel controls observed. Receipt: `browser/pr-8/attempt-1/results.json`. |
| A2 | PASS / EXECUTED | 5 | Exact seeded IDs/titles, capacity/active/remaining counts, UI agrees. → CT-101: 2/0/2; CT-102: 3/0/3; independent store and visible counts agree. Receipt: `core/pr-8/shared-api/report.json; browser/pr-8/attempt-1/results.json`. |
| A3 | PASS / EXECUTED | 5 | Valid reservation, stable ID, independent GET/store, remaining 1 and UI. → Ada/CT-101/K1 creates one active record; GET/store/UI agree. Receipt: `core/pr-8/deep-api-sql/report.json; browser/pr-8/attempt-1/results.json`. |
| A4 | PASS / EXECUTED | 5 | Sequential full rejection and ten batches × ten simultaneous distinct attempts. → Sequential third create rejects; every one-seat batch has exactly one create, nine rejections, two stored active rows. Receipt: `core/pr-8/shared-api/report.json; core/pr-8/shared-store-readback.json`. |
| A5 | PASS / EXECUTED | 5 | Same-key/trimmed-alias replay; globally conflicting alias/session reject. → Original ID/status returned without extra row/seat; both conflicts reject; extra identical/conflicting-key races also pass. Receipt: `core/pr-8/deep-api-sql/report.json`. |
| A6 | PASS / EXECUTED | 5 | Cancel once, repeat cancel, replay cancelled original without reactivation. → Exactly one seat released; repeated cancel and original-key replay retain cancelled ID and unchanged store. Receipt: `core/pr-8/deep-api-sql/report.json; browser/pr-8/attempt-2/results.json`. |
| A7 | PASS / EXECUTED | 5 | Real stop/start without reset; same active/cancelled IDs/statuses/counts through HTTP/store/UI. → Different process PIDs, same store, fresh HTTP and ordinary UI readback preserve both original records. Receipt: `core/pr-8/deep-api-sql/report.json; browser/pr-8/attempt-1/results.json`. |
| A8 | PASS / EXECUTED | 5 | All five invalid requests reject clearly, no store/count change, process remains available. → Unknown session, blank alias, missing key, malformed JSON and unknown cancel reject; entire populated store unchanged. Receipt: `integrity/integrity-evidence/pr-8/report.json; core/pr-8/shared-api/report.json`. |
| B1 | PASS / EXECUTED | 5 | Exact immutable source and receipt binding. → Retained commit/app/sourceId/archive verified; executed baseline hashes unchanged; deliberate mutation isolated. Receipt: `snapshot-rechecks/pr-8.json; core/pr-8/execution-summary.json`. |
| B2 | PASS / EXECUTED | 5 | Independently reproduce documented run/reset/test procedures. → Cold app start, isolated reset, native documented test command completed; exact argv/runtime recorded. Receipt: `core/pr-8/unit-command.json; browser/pr-8/attempt-1/results.json`. |
| B3 | PASS / EXECUTED | 5 | Fresh raw test counts, failures, skips, exit status. → Primary: 18 collected, 18 passed, 0 skipped, exit 0. Supplements/initial failures are preserved below. Receipt: `core/pr-8/unit-stdout.txt; core/pr-8/unit-stderr.txt; core/pr-8/unit-command.json`. |
| B4 | PASS / EXECUTED | 5 | Readable state before/after actual same-store process restart. → Raw process PIDs, full records and counts before/after restart retained; evaluated independently of A7. Receipt: `core/pr-8/deep-api-sql/report.json; browser/pr-8/attempt-1/results.json`. |
| B5 | PASS / EXECUTED | 5 | Meaningful behavioral negative control in separate copy, restored afterward. → Provided capacity assertion: baseline exit 0; behavioral mutant exit 1 with assertion failure; restored exit 0; baseline bytes unchanged. Receipt: `core/pr-8/negative-*-command.json; core/pr-8/negative-control.diff`. |
| B6 | PASS / STATIC | 5 | Delivered builder manifest separates claims, results, FAIL and NOT RUN. → Structured delivered manifest/addendum records commands, statuses, source binding, corrections and frozen UI NOT RUN. Receipt: `pr-8/attachment-1/frozen-verification.json; attachment-2/report.json`. |
| C1 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C2 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C3 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C4 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| D1 | PASS / EXECUTED | 5 | Demonstrated concrete optional user benefit. → Load original request restores saved fields; cancelled-key replay returns the original cancelled ID without consuming a seat. Receipt: `browser/pr-8/attempt-1/results.json`. |
| D2 | FAIL / EXECUTED | 0 | Demonstrated provided additional verification technique beyond mandatory checks. → Extra identical/global-key races executed, but conservatively treated as additional scenarios using the required concurrency technique. Human may accept the distinct invariant for +5, uniformly. Receipt: `core/pr-8/deep-api-sql/report.json`. |

Screenshots: [fresh-usable-ui](screenshots/pr-8/attempt-1-browser-fresh-usable-ui.png); [reserved-Ada](screenshots/pr-8/attempt-1-browser-reserved-Ada.png); [restart-after-active](screenshots/pr-8/attempt-1-browser-restart-after-active.png); [restart-after-cancelled](screenshots/pr-8/attempt-1-browser-restart-after-cancelled.png); [before-cancel-Ada](screenshots/pr-8/attempt-2-browser-before-cancel-Ada.png); [cancelled-Ada](screenshots/pr-8/attempt-2-browser-cancelled-Ada.png); [D1-load-original-cancelled-request](screenshots/pr-8/attempt-1-browser-D1-load-original-cancelled-request.png).

## PR #9 — bitcoder

Commit `1cfb2fec9ddd7c839f9473ecbabb6d0e523a7235`; app `starter-python`. SourceId `ff67447ce929ceba8ad02d43ae662e5741cef2cfce8184758d20529cc18fceed`. Retained ZIP SHA-256 `76e628bfad7f06c6290882fd6d8078e682a612e88f037f7ccfe531abf859ad7b`. Review/execution interval: 2026-11-18T22:13:38.480278+00:00 to 2026-11-18T23:11:04.872378+00:00.

Primary 47-case run: 46 passed, one environment skip, exit 0. The unchanged skipped loopback-binding test separately passed in an isolated namespace with reserved 192.0.2.2 on lo and no external route. All 47 cases were exercised across those runs. Coverage runs retain their own original skip and differing incidental line hits.

Proposed A 35/40, B 30/30, D 5/10 = **70/80**; C deferred; final human decision pending.

| Row | Result / class | Proposed | Expected → actual; raw receipt |
| --- | --- | ---: | --- |
| A1 | PASS / EXECUTED | 5 | Cold documented start and visible usable UI. → Both seeded sessions and usable reserve/cancel controls observed. Receipt: `browser/pr-9/attempt-1/results.json`. |
| A2 | PASS / EXECUTED | 5 | Exact seeded IDs/titles, capacity/active/remaining counts, UI agrees. → CT-101: 2/0/2; CT-102: 3/0/3; independent store and visible counts agree. Receipt: `core/pr-9/shared-api/report.json; browser/pr-9/attempt-1/results.json`. |
| A3 | FAIL / EXECUTED | 0 | Valid reservation, stable ID, independent GET/store, remaining 1 and UI. → Ada/CT-101/K1 creates one active record; GET/store/UI agree. Contract counterexample: nonempty key "   " returns HTTP 400. Strict A3 proposal is disputed; canonical K1 flow PASS; alternative +5 requires uniform human ruling. Receipt: `core/pr-9/deep-api-sql/report.json; browser/pr-9/attempt-1/results.json`. |
| A4 | PASS / EXECUTED | 5 | Sequential full rejection and ten batches × ten simultaneous distinct attempts. → Sequential third create rejects; every one-seat batch has exactly one create, nine rejections, two stored active rows. Receipt: `core/pr-9/shared-api/report.json; core/pr-9/shared-store-readback.json`. |
| A5 | PASS / EXECUTED | 5 | Same-key/trimmed-alias replay; globally conflicting alias/session reject. → Original ID/status returned without extra row/seat; both conflicts reject; extra identical/conflicting-key races also pass. Receipt: `core/pr-9/deep-api-sql/report.json`. |
| A6 | PASS / EXECUTED | 5 | Cancel once, repeat cancel, replay cancelled original without reactivation. → Exactly one seat released; repeated cancel and original-key replay retain cancelled ID and unchanged store. Receipt: `core/pr-9/deep-api-sql/report.json; browser/pr-9/attempt-1/results.json`. |
| A7 | PASS / EXECUTED | 5 | Real stop/start without reset; same active/cancelled IDs/statuses/counts through HTTP/store/UI. → Different process PIDs, same store, fresh HTTP and ordinary UI readback preserve both original records. Receipt: `core/pr-9/deep-api-sql/report.json; browser/pr-9/attempt-1/results.json`. |
| A8 | PASS / EXECUTED | 5 | All five invalid requests reject clearly, no store/count change, process remains available. → Unknown session, blank alias, missing key, malformed JSON and unknown cancel reject; entire populated store unchanged. Receipt: `integrity/integrity-evidence/pr-9/report.json; core/pr-9/shared-api/report.json`. |
| B1 | PASS / EXECUTED | 5 | Exact immutable source and receipt binding. → Retained commit/app/sourceId/archive verified; executed baseline hashes unchanged; deliberate mutation isolated. Receipt: `snapshot-rechecks/pr-9.json; core/pr-9/execution-summary.json`. |
| B2 | PASS / EXECUTED | 5 | Independently reproduce documented run/reset/test procedures. → Cold app start, isolated reset, native documented test command completed; exact argv/runtime recorded. Receipt: `core/pr-9/unit-command.json; browser/pr-9/attempt-1/results.json`. |
| B3 | PASS / EXECUTED | 5 | Fresh raw test counts, failures, skips, exit status. → Primary: 47 collected, 46 passed, 1 skipped, exit 0. Supplements/initial failures are preserved below. Receipt: `core/pr-9/unit-stdout.txt; core/pr-9/unit-stderr.txt; core/pr-9/unit-command.json`. |
| B4 | PASS / EXECUTED | 5 | Readable state before/after actual same-store process restart. → Raw process PIDs, full records and counts before/after restart retained; evaluated independently of A7. Receipt: `core/pr-9/deep-api-sql/report.json; browser/pr-9/attempt-1/results.json`. |
| B5 | PASS / EXECUTED | 5 | Meaningful behavioral negative control in separate copy, restored afterward. → Provided capacity assertion: baseline exit 0; behavioral mutant exit 1 with assertion failure; restored exit 0; baseline bytes unchanged. Receipt: `core/pr-9/negative-*-command.json; core/pr-9/negative-control.diff`. |
| B6 | PASS / STATIC | 5 | Delivered builder manifest separates claims, results, FAIL and NOT RUN. → Delivered builder-only manifest excludes old-source work and identifies actual failures, missing checks and raw-output limits. Receipt: `pr-9/attachment-1/evidence-manifest.md`. |
| C1 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C2 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C3 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C4 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| D1 | NOT RUN / STATIC | 0 | Demonstrated concrete optional user benefit. → No distinct optional user improvement demonstrated; required record lookup alone is not D1. Receipt: `browser/pr-9/attempt-1/results.json`. |
| D2 | PASS / EXECUTED | 5 | Demonstrated provided additional verification technique beyond mandatory checks. → Provided child-process line tracing executed: documented aggregate 211/216 (97.69%); independent retained traces 210/216 (97.22%). Line coverage is not behavioral completeness. Receipt: `additional/pr-9/coverage-analysis-corrected.json`. |

Screenshots: [fresh-usable-ui](screenshots/pr-9/attempt-1-browser-fresh-usable-ui.png); [reserved-Ada](screenshots/pr-9/attempt-1-browser-reserved-Ada.png); [restart-after-active](screenshots/pr-9/attempt-1-browser-restart-after-active.png); [restart-after-cancelled](screenshots/pr-9/attempt-1-browser-restart-after-cancelled.png).

## PR #10 — TomislavPrsa

Commit `cb1b59ba50ee021c8e5b51208e3067c8a08122eb`; app `starter-python`. SourceId `3446b8d65937a2a958a00085bee6a49b3443fa27189b5f8d0d96b0ad3d915288`. Retained ZIP SHA-256 `8037a1892f248e5cd3e100a1f76a8b689743e46b37b22e895ae0aba3d515859a`. Review/execution interval: 2026-11-18T22:17:36.731830+00:00 to 2026-11-18T23:11:04.872378+00:00.

Ordinary server-rendered POST/redirect forms exercised. Harness assigned fixture K1/K2 into generated hidden key inputs for correlation; source unchanged and ordinary form submission retained. No distinct optional feature/extra verification claimed.

Proposed A 40/40, B 30/30, D 0/10 = **70/80**; C deferred; final human decision pending.

| Row | Result / class | Proposed | Expected → actual; raw receipt |
| --- | --- | ---: | --- |
| A1 | PASS / EXECUTED | 5 | Cold documented start and visible usable UI. → Both seeded sessions and usable reserve/cancel controls observed. Receipt: `browser/pr-10/attempt-1/results.json`. |
| A2 | PASS / EXECUTED | 5 | Exact seeded IDs/titles, capacity/active/remaining counts, UI agrees. → CT-101: 2/0/2; CT-102: 3/0/3; independent store and visible counts agree. Receipt: `core/pr-10/shared-api/report.json; browser/pr-10/attempt-1/results.json`. |
| A3 | PASS / EXECUTED | 5 | Valid reservation, stable ID, independent GET/store, remaining 1 and UI. → Ada/CT-101/K1 creates one active record; GET/store/UI agree. Receipt: `core/pr-10/deep-api-sql/report.json; browser/pr-10/attempt-1/results.json`. |
| A4 | PASS / EXECUTED | 5 | Sequential full rejection and ten batches × ten simultaneous distinct attempts. → Sequential third create rejects; every one-seat batch has exactly one create, nine rejections, two stored active rows. Receipt: `core/pr-10/shared-api/report.json; core/pr-10/shared-store-readback.json`. |
| A5 | PASS / EXECUTED | 5 | Same-key/trimmed-alias replay; globally conflicting alias/session reject. → Original ID/status returned without extra row/seat; both conflicts reject; extra identical/conflicting-key races also pass. Receipt: `core/pr-10/deep-api-sql/report.json`. |
| A6 | PASS / EXECUTED | 5 | Cancel once, repeat cancel, replay cancelled original without reactivation. → Exactly one seat released; repeated cancel and original-key replay retain cancelled ID and unchanged store. Receipt: `core/pr-10/deep-api-sql/report.json; browser/pr-10/attempt-1/results.json`. |
| A7 | PASS / EXECUTED | 5 | Real stop/start without reset; same active/cancelled IDs/statuses/counts through HTTP/store/UI. → Different process PIDs, same store, fresh HTTP and ordinary UI readback preserve both original records. Receipt: `core/pr-10/deep-api-sql/report.json; browser/pr-10/attempt-1/results.json`. |
| A8 | PASS / EXECUTED | 5 | All five invalid requests reject clearly, no store/count change, process remains available. → Unknown session, blank alias, missing key, malformed JSON and unknown cancel reject; entire populated store unchanged. Receipt: `integrity/integrity-evidence/pr-10/report.json; core/pr-10/shared-api/report.json`. |
| B1 | PASS / EXECUTED | 5 | Exact immutable source and receipt binding. → Retained commit/app/sourceId/archive verified; executed baseline hashes unchanged; deliberate mutation isolated. Receipt: `snapshot-rechecks/pr-10.json; core/pr-10/execution-summary.json`. |
| B2 | PASS / EXECUTED | 5 | Independently reproduce documented run/reset/test procedures. → Cold app start, isolated reset, native documented test command completed; exact argv/runtime recorded. Receipt: `core/pr-10/unit-command.json; browser/pr-10/attempt-1/results.json`. |
| B3 | PASS / EXECUTED | 5 | Fresh raw test counts, failures, skips, exit status. → Primary: 30 collected, 30 passed, 0 skipped, exit 0. Supplements/initial failures are preserved below. Receipt: `core/pr-10/unit-stdout.txt; core/pr-10/unit-stderr.txt; core/pr-10/unit-command.json`. |
| B4 | PASS / EXECUTED | 5 | Readable state before/after actual same-store process restart. → Raw process PIDs, full records and counts before/after restart retained; evaluated independently of A7. Receipt: `core/pr-10/deep-api-sql/report.json; browser/pr-10/attempt-1/results.json`. |
| B5 | PASS / EXECUTED | 5 | Meaningful behavioral negative control in separate copy, restored afterward. → Provided capacity assertion: baseline exit 0; behavioral mutant exit 1 with assertion failure; restored exit 0; baseline bytes unchanged. Receipt: `core/pr-10/negative-*-command.json; core/pr-10/negative-control.diff`. |
| B6 | PASS / STATIC | 5 | Delivered builder manifest separates claims, results, FAIL and NOT RUN. → Delivered comment maps claims to raw paths and limits; unverified AQE/coverage claims are not scored. Receipt: `PR comment 6992079565; pr-10/comments.json`. |
| C1 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C2 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C3 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C4 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| D1 | NOT RUN / STATIC | 0 | Demonstrated concrete optional user benefit. → No distinct optional user improvement demonstrated; native forms, labels and generated keys are basic UI. Receipt: `browser/pr-10/attempt-1/results.json`. |
| D2 | NOT RUN / STATIC | 0 | Demonstrated provided additional verification technique beyond mandatory checks. → No demonstrated distinct additional technique. AQE labels and an unsupported coverage/security summary do not establish execution. Receipt: `pr-10/comments.json`. |

Screenshots: [fresh-usable-ui](screenshots/pr-10/attempt-1-browser-fresh-usable-ui.png); [reserved-Ada](screenshots/pr-10/attempt-1-browser-reserved-Ada.png); [restart-after-active](screenshots/pr-10/attempt-1-browser-restart-after-active.png); [restart-after-cancelled](screenshots/pr-10/attempt-1-browser-restart-after-cancelled.png).

## PR #11 — Team Claude — AI rehearsal

Commit `65d3754b5fa1b7a6d8a0f5214795693b1aa93f7b`; app `starter-python`. SourceId `2717dc28358ece7371574920d1050ee183f099d2d5ab2e2e06ef82d377172f3c`. Retained ZIP SHA-256 `423650ab43c12d38b7525a977018d8221efe66327195ee1ffbc1a5165875ea67`. Review/execution interval: 2026-11-18T22:09:18.106195+00:00 to 2026-11-18T23:11:04.872378+00:00.

Explicit AI-built organizer rehearsal; excluded from human-participant comparison. Its source and functionality were executed under the same oracles. Known whitespace-key mismatch was already disclosed in its README.

Proposed A 35/40, B 30/30, D 5/10 = **70/80**; C deferred; final human decision pending.

| Row | Result / class | Proposed | Expected → actual; raw receipt |
| --- | --- | ---: | --- |
| A1 | PASS / EXECUTED | 5 | Cold documented start and visible usable UI. → Both seeded sessions and usable reserve/cancel controls observed. Receipt: `browser/pr-11/attempt-1/results.json`. |
| A2 | PASS / EXECUTED | 5 | Exact seeded IDs/titles, capacity/active/remaining counts, UI agrees. → CT-101: 2/0/2; CT-102: 3/0/3; independent store and visible counts agree. Receipt: `core/pr-11/shared-api/report.json; browser/pr-11/attempt-1/results.json`. |
| A3 | FAIL / EXECUTED | 0 | Valid reservation, stable ID, independent GET/store, remaining 1 and UI. → Ada/CT-101/K1 creates one active record; GET/store/UI agree. Contract counterexample: nonempty key "   " returns HTTP 400. Strict A3 proposal is disputed; canonical K1 flow PASS; alternative +5 requires uniform human ruling. Receipt: `core/pr-11/deep-api-sql/report.json; browser/pr-11/attempt-1/results.json`. |
| A4 | PASS / EXECUTED | 5 | Sequential full rejection and ten batches × ten simultaneous distinct attempts. → Sequential third create rejects; every one-seat batch has exactly one create, nine rejections, two stored active rows. Receipt: `core/pr-11/shared-api/report.json; core/pr-11/shared-store-readback.json`. |
| A5 | PASS / EXECUTED | 5 | Same-key/trimmed-alias replay; globally conflicting alias/session reject. → Original ID/status returned without extra row/seat; both conflicts reject; extra identical/conflicting-key races also pass. Receipt: `core/pr-11/deep-api-sql/report.json`. |
| A6 | PASS / EXECUTED | 5 | Cancel once, repeat cancel, replay cancelled original without reactivation. → Exactly one seat released; repeated cancel and original-key replay retain cancelled ID and unchanged store. Receipt: `core/pr-11/deep-api-sql/report.json; browser/pr-11/attempt-1/results.json`. |
| A7 | PASS / EXECUTED | 5 | Real stop/start without reset; same active/cancelled IDs/statuses/counts through HTTP/store/UI. → Different process PIDs, same store, fresh HTTP and ordinary UI readback preserve both original records. Receipt: `core/pr-11/deep-api-sql/report.json; browser/pr-11/attempt-1/results.json`. |
| A8 | PASS / EXECUTED | 5 | All five invalid requests reject clearly, no store/count change, process remains available. → Unknown session, blank alias, missing key, malformed JSON and unknown cancel reject; entire populated store unchanged. Receipt: `integrity/integrity-evidence/pr-11/report.json; core/pr-11/shared-api/report.json`. |
| B1 | PASS / EXECUTED | 5 | Exact immutable source and receipt binding. → Retained commit/app/sourceId/archive verified; executed baseline hashes unchanged; deliberate mutation isolated. Receipt: `snapshot-rechecks/pr-11.json; core/pr-11/execution-summary.json`. |
| B2 | PASS / EXECUTED | 5 | Independently reproduce documented run/reset/test procedures. → Cold app start, isolated reset, native documented test command completed; exact argv/runtime recorded. Receipt: `core/pr-11/unit-command.json; browser/pr-11/attempt-1/results.json`. |
| B3 | PASS / EXECUTED | 5 | Fresh raw test counts, failures, skips, exit status. → Primary: 16 collected, 16 passed, 0 skipped, exit 0. Supplements/initial failures are preserved below. Receipt: `core/pr-11/unit-stdout.txt; core/pr-11/unit-stderr.txt; core/pr-11/unit-command.json`. |
| B4 | PASS / EXECUTED | 5 | Readable state before/after actual same-store process restart. → Raw process PIDs, full records and counts before/after restart retained; evaluated independently of A7. Receipt: `core/pr-11/deep-api-sql/report.json; browser/pr-11/attempt-1/results.json`. |
| B5 | PASS / EXECUTED | 5 | Meaningful behavioral negative control in separate copy, restored afterward. → Provided capacity assertion: baseline exit 0; behavioral mutant exit 1 with assertion failure; restored exit 0; baseline bytes unchanged. Receipt: `core/pr-11/negative-*-command.json; core/pr-11/negative-control.diff`. |
| B6 | PASS / STATIC | 5 | Delivered builder manifest separates claims, results, FAIL and NOT RUN. → Concise delivered text matrix identifies known gaps; tentatively accepted as a manifest for rehearsal only. Earlier raw browser/axe logs remain undelivered. Receipt: `PR #11 body check/result/NOT RUN matrix; pr-11/metadata.json`. |
| C1 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C2 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C3 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C4 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| D1 | PASS / EXECUTED | 5 | Demonstrated concrete optional user benefit. → Attendee search and offline/stale-state warning with recovery demonstrated on current source; rehearsal only. Receipt: `browser/pr-11/attempt-1/results.json`. |
| D2 | NOT RUN / STATIC | 0 | Demonstrated provided additional verification technique beyond mandatory checks. → Builder multi-state axe claim lacks delivered matching raw receipts. Fresh judge-authored scan is not builder creativity credit. Receipt: `pr-11/metadata.json`. |

Screenshots: [fresh-usable-ui](screenshots/pr-11/attempt-1-browser-fresh-usable-ui.png); [reserved-Ada](screenshots/pr-11/attempt-1-browser-reserved-Ada.png); [restart-after-active](screenshots/pr-11/attempt-1-browser-restart-after-active.png); [restart-after-cancelled](screenshots/pr-11/attempt-1-browser-restart-after-cancelled.png); [D1-live-recovered](screenshots/pr-11/attempt-1-browser-D1-live-recovered.png); [D1-offline-stale-warning](screenshots/pr-11/attempt-1-browser-D1-offline-stale-warning.png); [D1-search](screenshots/pr-11/attempt-1-browser-D1-search.png).

## PR #12 — workroomprds

Commit `3c35e334d0eb57d034e732f4f4aac11efda42277`; app `starter-python`. SourceId `8bcea4aa69b7561f28ab2a48c82a17d568892088b9a1d9642958e72f9e6c3ca9`. Retained ZIP SHA-256 `539d185d3da65ca4fae0660b14d530f64e332810c466eebc7451d7adf7a07281`. Review/execution interval: 2026-11-18T22:22:55.674011+00:00 to 2026-11-18T23:11:04.872378+00:00.

JSON state.json is the actual durable store. UI shows remaining/capacity; active count is derived as capacity minus remaining rather than a separately labelled field. Default list is empty after reload; A7 passes through the separately executed normal UI replay path for both original IDs/statuses with unchanged store and counts; default empty listing is a usability limitation. Primary documented pytest/xdist workflow passed 67/67; one read-only pytest-cache warning is retained. Original freeze/deadline receipt is unestablished.

Proposed A 35/40, B 25/30, D 10/10 = **70/80**; C deferred; final human decision pending.

| Row | Result / class | Proposed | Expected → actual; raw receipt |
| --- | --- | ---: | --- |
| A1 | PASS / EXECUTED | 5 | Cold documented start and visible usable UI. → Both seeded sessions and usable reserve/cancel controls observed. Receipt: `browser/pr-12/attempt-1/results.json`. |
| A2 | PASS / EXECUTED | 5 | Exact seeded IDs/titles, capacity/active/remaining counts, UI agrees. → CT-101: 2/0/2; CT-102: 3/0/3; independent store and visible counts agree. Receipt: `core/pr-12/shared-api/report.json; browser/pr-12/attempt-1/results.json`. |
| A3 | FAIL / EXECUTED | 0 | Valid reservation, stable ID, independent GET/store, remaining 1 and UI. → Ada/CT-101/K1 creates one active record; GET/store/UI agree. Contract counterexample: nonempty key "   " returns HTTP 400. Strict A3 proposal is disputed; canonical K1 flow PASS; alternative +5 requires uniform human ruling. Receipt: `core/pr-12/deep-api-sql/report.json; browser/pr-12/attempt-1/results.json`. |
| A4 | PASS / EXECUTED | 5 | Sequential full rejection and ten batches × ten simultaneous distinct attempts. → Sequential third create rejects; every one-seat batch has exactly one create, nine rejections, two stored active rows. Receipt: `core/pr-12/shared-api/report.json; core/pr-12/shared-store-readback.json`. |
| A5 | PASS / EXECUTED | 5 | Same-key/trimmed-alias replay; globally conflicting alias/session reject. → Original ID/status returned without extra row/seat; both conflicts reject; extra identical/conflicting-key races also pass. Receipt: `core/pr-12/deep-api-sql/report.json`. |
| A6 | PASS / EXECUTED | 5 | Cancel once, repeat cancel, replay cancelled original without reactivation. → Exactly one seat released; repeated cancel and original-key replay retain cancelled ID and unchanged store. Receipt: `core/pr-12/deep-api-sql/report.json; browser/pr-12/attempt-1/results.json`. |
| A7 | PASS / EXECUTED | 5 | Real stop/start without reset; same active/cancelled IDs/statuses/counts through HTTP/store/UI. → Different process PIDs, same store, fresh HTTP and ordinary UI readback preserve both original records. Initial empty list retained as usability limitation; normal same-key form replay exposes each original active/cancelled record without any store or count change. Receipt: `core/pr-12/deep-api-sql/report.json; browser/pr-12/replay-readback-1/results.json`. |
| A8 | PASS / EXECUTED | 5 | All five invalid requests reject clearly, no store/count change, process remains available. → Unknown session, blank alias, missing key, malformed JSON and unknown cancel reject; entire populated store unchanged. Receipt: `integrity/integrity-evidence/pr-12/report.json; core/pr-12/shared-api/report.json`. |
| B1 | PASS / EXECUTED | 5 | Exact immutable source and receipt binding. → Retained commit/app/sourceId/archive verified; executed baseline hashes unchanged; deliberate mutation isolated. Receipt: `snapshot-rechecks/pr-12.json; core/pr-12/execution-summary.json`. |
| B2 | PASS / EXECUTED | 5 | Independently reproduce documented run/reset/test procedures. → Cold app start, isolated reset, native documented test command completed; exact argv/runtime recorded. Receipt: `core/pr-12/unit-command.json; browser/pr-12/attempt-1/results.json`. |
| B3 | PASS / EXECUTED | 5 | Fresh raw test counts, failures, skips, exit status. → Primary: 67 collected, 67 passed, 0 skipped, exit 0. Supplements/initial failures are preserved below. Receipt: `core/pr-12/unit-stdout.txt; core/pr-12/unit-stderr.txt; core/pr-12/unit-command.json`. |
| B4 | PASS / EXECUTED | 5 | Readable state before/after actual same-store process restart. → Raw process PIDs, full records and counts before/after restart retained; evaluated independently of A7. Receipt: `core/pr-12/deep-api-sql/report.json; browser/pr-12/replay-readback-1/results.json`. |
| B5 | PASS / EXECUTED | 5 | Meaningful behavioral negative control in separate copy, restored afterward. → Provided capacity assertion: baseline exit 0; behavioral mutant exit 1 with assertion failure; restored exit 0; baseline bytes unchanged. Receipt: `core/pr-12/negative-*-command.json; core/pr-12/negative-control.diff`. |
| B6 | NOT RUN / STATIC | 0 | Delivered builder manifest separates claims, results, FAIL and NOT RUN. → Blank PR template and no delivered executed-results/receipt manifest. README implementation claims and unfinished checklist are not substituted for that evidence. Receipt: `pr-12/comments.json; source/README.md`. |
| C1 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C2 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C3 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| C4 | NOT RUN / REPORTED | Deferred | Outgoing cross-team audit criterion. → DEFERRED BY USER; no final audit credit or failure inferred. Incoming judge work does not earn outgoing C. Receipt: `User instruction: cross-team checks later.`. |
| D1 | PASS / EXECUTED | 5 | Demonstrated concrete optional user benefit. → Provided demo_data.py loads six fictional training records (four active, two cancelled) into a new disposable fixture; API/store and visible counts agree: CT-101 active 2/remaining 0; CT-102 active 2/remaining 1. Receipt: `browser/pr-12/attempt-1/results.json`. |
| D2 | PASS / EXECUTED | 5 | Demonstrated provided additional verification technique beyond mandatory checks. → Provided storage fault injection ran: corrupt JSON produces a named error while process stays available; failed atomic replacement/serialization preserves old file and leaves no temporary files. Receipt: `core/pr-12/unit-stdout.txt`. |

Screenshots: [fresh-usable-ui](screenshots/pr-12/attempt-1-browser-fresh-usable-ui.png); [reserved-Ada](screenshots/pr-12/attempt-1-browser-reserved-Ada.png); [after-restart-both-records-read-through-ui](screenshots/pr-12/replay-readback-1-browser-after-restart-both-records-read-through-ui.png); [after-restart-default-empty-list](screenshots/pr-12/replay-readback-1-browser-after-restart-default-empty-list.png); [after-restart-replay-active](screenshots/pr-12/replay-readback-1-browser-after-restart-replay-active.png); [after-restart-replay-cancelled](screenshots/pr-12/replay-readback-1-browser-after-restart-replay-cancelled.png); [before-cancel-Grace](screenshots/pr-12/replay-readback-1-browser-before-cancel-Grace.png); [before-restart-active](screenshots/pr-12/replay-readback-1-browser-before-restart-active.png); [before-restart-cancelled](screenshots/pr-12/replay-readback-1-browser-before-restart-cancelled.png); [cancelled-Grace](screenshots/pr-12/replay-readback-1-browser-cancelled-Grace.png); [D1-provided-demo-full-and-available](screenshots/pr-12/attempt-1-browser-D1-provided-demo-full-and-available.png).

## Evidence handoff and decisions remaining

Raw evidence is retained outside the checkout at `/workspaces/hackathon-scoring-2026-11-18-1795036407012`. Paths starting `core/`, `browser/`, `additional/`, `integrity/`, `snapshot-rechecks/` or `packets/` resolve under `executed-v4/`; original `pr-N/` references resolve under the review root. Unprefixed `source/`, `source-seat-desk/` or `attachment-N/` paths resolve within the current entry’s `pr-N/` directory. The curated review bundle includes receipts, fictional fixture stores, exact source archives, trusted harness/rules, manifest material and this report/screenshots. The VM image, disposable SSH key and unrelated workspace state are excluded.

[Independent core validation](validation/independent-core-validation.json) · [Rubric interpretation evidence](validation/rubric-interpretation.json)

The full raw review bundle is retained outside Git as `completion-theater-review-v4.zip` (SHA-256 `84713d24126388b26da4c9d79fa426d7a2f2c82ae2ecb447f1d10b21e141e733`). It contains the original execution-time report; this Git version changes report navigation and evidence links only. Raw logs, fixture databases, source archives and runtime files are not part of this reports PR.

Pending human decisions: approve individual row recommendations; resolve the uniform whitespace-key and extra-technique interpretations; confirm B6 text-manifest treatment consistently; rule on disclosed pre-build/deadline/intake exceptions. Organizer review receipts establish the bytes reviewed, not original deadline delivery. Cross-team investigations, builder responses and outgoing C1–C4 will be added later. No winner or final /100 score is asserted.
