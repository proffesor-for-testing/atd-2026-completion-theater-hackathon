# Cross-audit checklist and findings sheet

Auditing team: __________  Target team: __________  Facilitator: __________

Target source identity: ____________________________________________________

Audit window: 22:05–22:40. Inspect the frozen artifact in a disposable copy. The builder can explain commands but does not operate the auditor's checks. Agree to the review of this fixture app only. Never inspect unrelated directories, accounts, production systems or personal files.

## A 35-minute investigation

| Minutes | Action | Receipt |
| --- | --- | --- |
| 0–5 | Check source identity, README, dependencies and state path. Start from the supplied artifact. If blocked, spend at most 5 minutes before notifying a facilitator. | __________________ |
| 5–15 | Independently run a happy path and inspect persisted state. Compare responses, UI and restart behavior. | __________________ |
| 15–25 | Challenge capacity, concurrent reservations, request replay, cancelled-key replay or malformed input. Pick high-risk checks before cosmetic issues. | __________________ |
| 25–30 | Challenge one test with a deliberate failure in a copy, or trace a claimed metric to actual output. Record what the evidence can and cannot establish. | __________________ |
| 30–35 | Write at most two strongest findings/investigations. Share reproduction steps with the builder and facilitator. Record disagreements. | __________________ |

## Pattern prompts

- Ghost Database: did a record survive a real process restart, or just a refresh?
- Metric Theater: where did the claimed number come from, and what does it mean?
- Test Theater: can an important check actually fail when the behavior is wrong?
- False Positives: did the process fail, skip work or swallow an error while reporting success?
- Uncommitted Illusion: does the frozen artifact contain the implementation and tests being demonstrated?

Do not force every defect into a named pattern. An ordinary functional defect can be important. A suspected theater pattern becomes a finding only when evidence supports it.

## Finding or bounded clean investigation

Copy this form for each of your two strongest investigations. A clean result can earn cross-audit credit when you demonstrate a serious challenge, its oracle and its bounded conclusion. This avoids rewarding invented bugs or penalizing a team assigned a sound target.

Investigation ID: __________  Target criterion / claim: _______________________

Expected behavior / oracle: _________________________________________________

Setup and exact reproduction steps: _________________________________________

____________________________________________________________________________

Actual result, error and state readback: _____________________________________

Evidence files, timestamp and source identity: _______________________________

Classification: [ ] Confirmed mismatch [ ] Not reproduced [ ] Bounded clean result [ ] Blocked

Pattern (if supported): _____________________________________________________

Impact: [ ] Core behavior [ ] Evidence integrity [ ] Usability [ ] Other

Builder response / disagreement: ____________________________________________

Facilitator confirmation: ____________________  Follow-up: ___________________

## Fairness and scope

No edits to the frozen source. No deliberate planting of defects in the target baseline. Temporary negative controls belong only in a clearly marked disposable copy. Duplicate symptoms with one root cause are one finding. Suggestions are not defects. Unreproduced suspicions must remain labelled. Facilitators adjudicate contested results against the same PRD and source identity.

Cross-audit points belong to the auditing team. The target team's working-app score follows its acceptance results. Do not subtract extra points merely because a peer found a defect. Builders earn evidence credit for an honest FAIL, not for hiding it.
