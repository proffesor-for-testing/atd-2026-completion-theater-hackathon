# Judge scoring sheet

Team: __________  Judge: __________  Source identity: _________________________

Published weights: working app 40, verification evidence 30, cross-audit catches/challenges 20, creativity 10. Total 100. Rewards remain open. Rubric version 1.1. Announce this same rubric to all teams before the build; changes after that need an equal, recorded ruling.

Every row scores either 0 or 5. Mark the observation PASS, FAIL or NOT RUN, with an evidence reference. Only EXECUTED PASS supports functional points. Missing evidence earns 0, not an inferred pass. A test that correctly rejects invalid input is a PASS.

## A. Working app: 40 points

| ID | Criterion | 0 or 5 | Evidence |
| --- | --- | --- | --- |
| A1 / AC-01 | Reproducible start and usable basic UI | ____ | __________________ |
| A2 / AC-02 | Seeded sessions, API counts and UI agreement | ____ | __________________ |
| A3 / AC-03 | Valid reservation and independent record readback | ____ | __________________ |
| A4 / AC-04 | Capacity holds sequentially AND under concurrent requests | ____ | __________________ |
| A5 / AC-05 | Same-key replay and conflicting-key rejection | ____ | __________________ |
| A6 / AC-06 | Cancellation, repeated cancellation and cancelled-key replay | ____ | __________________ |
| A7 / AC-07 | Active and cancelled state survives process restart | ____ | __________________ |
| A8 / AC-08 | All five invalid-input cases reject without state changes | ____ | __________________ |

Working-app subtotal (0–40): ______

## B. Verification evidence: 30 points

| ID | Criterion | 0 or 5 | Evidence |
| --- | --- | --- | --- |
| B1 | Frozen source hash/checksum and each receipt bound to it | ____ | __________________ |
| B2 | Run/reset/test instructions independently reproduced | ____ | __________________ |
| B3 | Fresh raw test output shows exit codes, failures and skipped work | ____ | __________________ |
| B4 | Before/after state evidence includes a real process restart | ____ | __________________ |
| B5 | A meaningful test fails under a deliberate negative control in a copy | ____ | __________________ |
| B6 | Manifest distinguishes claims, executed results, FAIL and NOT RUN | ____ | __________________ |

Evidence subtotal (0–30): ______

B3 can earn 5 even when tests fail, if the output is complete and honestly reported. B4 requires readable state evidence and a recorded observation; matching state earns AC-07 separately. B5 requires an important behavioral assertion, not just a syntax error. A known limitation must be disclosed, not fabricated to satisfy B6.

## C. Cross-audit: 20 points

Target team: ______  Investigation references: ________________________________

| ID | Criterion | 0 or 5 | Evidence |
| --- | --- | --- | --- |
| C1 | Auditor independently starts the exact frozen artifact | ____ | __________________ |
| C2 | Auditor executes a high-risk functional challenge with an explicit oracle | ____ | __________________ |
| C3 | Auditor challenges an evidence claim, test sensitivity or persistence independently | ____ | __________________ |
| C4 | Report contains a reproducible mismatch OR a bounded clean result, plus limits and builder response | ____ | __________________ |

Cross-audit subtotal (0–20): ______

Record the auditing team and target separately. Do not add points for an audit performed ON this team to its own score. A team must perform an audit to earn C points. An AI-only rehearsal is labelled rehearsal, not an independent human-team qualification.

No points per bug, no bonus for dramatic severity labels, no requirement to invent a finding. At most two investigations are considered. A blocked cold start can earn C4 with a reproducible, adjudicated report, but does not earn C1.

## D. Creativity: 10 points

| ID | Criterion | 0 or 5 | Evidence |
| --- | --- | --- | --- |
| D1 | One optional improvement solves a concrete user problem and is demonstrated | ____ | __________________ |
| D2 | One additional verification technique is demonstrated beyond the supplied checks, with a clear question and result | ____ | __________________ |

Creativity subtotal (0–10): ______

Both can earn credit in a partial app; an unsupported feature promise cannot. Repeating the mandatory capacity check is not an additional technique. Novelty is judged relative to this starter, not to the wider industry.

## Final decision

A ____ + B ____ + C ____ + D ____ = TOTAL ____ / 100

Judge and second facilitator confirm arithmetic: _____________________________

Tie-break order: higher B, then higher C, then higher A. If still tied, share the position. Do not improvise a new criterion after the build. A new disputed rule applies to everyone or is left unscored; facilitators record the decision.

No penalty for selecting a cheaper tool, not using AQE, avoiding deployment, acknowledging a failure or receiving no defects from an auditor. Unsafe activity is stopped and the affected evidence is invalidated; unrelated earned points remain unless event organizers decide otherwise.

---

# Master scoreboard

Event: 18 November 2026  Judge: ____________________

| Team | Working /40 | Evidence /30 | Audit /20 | Creativity /10 | Total /100 | Tie order / notes |
| --- | --- | --- | --- | --- | --- | --- |
| A | ____ | ____ | ____ | ____ | ____ | __________ |
| B | ____ | ____ | ____ | ____ | ____ | __________ |
| C | ____ | ____ | ____ | ____ | ____ | __________ |
| D | ____ | ____ | ____ | ____ | ____ | __________ |
| E | ____ | ____ | ____ | ____ | ____ | __________ |
| F | ____ | ____ | ____ | ____ | ____ | __________ |
| G | ____ | ____ | ____ | ____ | ____ | __________ |
| H | ____ | ____ | ____ | ____ | ____ | __________ |

Score owner: __________________  Arithmetic checked by: ______________________

Outstanding disputes: _______________________________________________________

Rewards: OPEN. Do not announce products, subscriptions, values or sponsorship commitments.
