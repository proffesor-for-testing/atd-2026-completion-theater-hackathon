# Facilitator notes

Completion Theater Hackathon: Build It, Prove It, Smash It

Wednesday 18 November 2026, 20:15–23:15, Room E2+E3, Potsdam local time (CET).

Facilitators: Dragan Spiridonov and Lalitkumar Bhamare. The responsibilities below are a proposed division to agree together. Rewards are OPEN; no product, subscription, value or sponsor commitment is included.

## Purpose

Participants build with AI agents, then independently investigate whether the delivered behavior and evidence support the completion claims. Reuse the HUSTEF five-pattern field guide, the empty-tests example and independent-verification material. Keep the opening short. The primary learning comes from executing and auditing, not from another full conference talk.

Use rules/rubric version 1.1 consistently. The frozen source is the judged object. Honest failures still earn evidence credit. No team needs to use AQE or a particular vendor. Tool spend, agent count, coverage percentage and polish do not substitute for evidence.

## Exact 180-minute run of show

| Time (CET) | Minutes | Activity | Lead / output |
| --- | --- | --- | --- |
| 20:15–20:30 | 15 | Opening: empty-tests example, five patterns, verification reflex, rules | Dragan; common vocabulary |
| 20:30–20:40 | 10 | Teams, PRD, roles and published scoring rubric | Lalit; one bounded plan per team |
| 20:40–21:40 | 60 | Build with chosen AI tools | Both circulate; a runnable vertical slice |
| 21:40–22:00 | 20 | Self-verification, repairs until 21:55, source freeze and evidence packaging | Dragan on evidence, Lalit on flow |
| 22:00–22:05 | 5 | Short break and artifact handoff | Lalit assigns audit ring |
| 22:05–22:40 | 35 | Independent cross-audit | Both; two strongest investigations per team |
| 22:40–23:00 | 20 | Short demos, findings and contested-result checks | Dragan hosts, Lalit records provisional scores |
| 23:00–23:10 | 10 | Finish arithmetic and discuss lessons | Both; confirmed scoreboard |
| 23:10–23:15 | 5 | Close and personal takeaway | Both; one practice to take back |

Total: 180 minutes. The build remains the advertised 60 minutes. No extra four-hour agenda is implied. Show the current phase and next deadline on the projector. Announce five-minute and one-minute warnings.

## Before the day

- Agree roles with Lalit and check the live session slot and room with organizers.
- Plan for 3–8 teams, normally 4–6 people each. This is a planning range, not a registration count. At 49–50 attendees, use eight teams with two groups of seven if needed and redistribute roles. Do not promise unlimited facilitation capacity.
- Ask participants to arrive with a laptop, charger, working coding agent, available model access/credits, Git or an archive tool, and one local runtime they know. They can use a local model. No specific subscription is required.
- Bring the deck as PPTX and PDF, participant PDFs, editable Markdown templates, a timer, USB/offline transfer media, paper and pens. Avoid relying on a single download link.
- Arrange power, projector/HDMI adapter, room Wi-Fi and a local transfer method. Check whether venue networking prevents peer transfer.
- Print one PRD and pattern card per team, one builder and audit checklist per team, one scoring sheet per team, and one master scoreboard for facilitators.
- Rehearse artifact transfer, source identity, cold start and a restart readback with a small local fixture before the event. An AI-assisted build and independent AI review have been executed on macOS; the public dry-run report gives scope and receipts. A mixed human-team and venue rehearsal still has not run.
- Calibrate the rubric together: score a complete example, an honest broken app and a convincing agent summary with no executable receipts. The third example cannot receive functional points.

## Team roles and setup

Suggested roles: product/question owner, agent operator, implementer/integrator, verifier and evidence recorder. Combine roles in a small team and rotate after the build. Choose an audit lead who did not operate the target build. Different team ownership provides the independent perspective; using a different model alone does not guarantee it.

At 20:30 distribute 01–04, 06 and team-templates. Ask each team to name itself A–H, choose a known runtime, declare a local port and state directory, and read the eight acceptance criteria. Resolve questions publicly so all teams receive the same rule. A simple UI plus API and durable local state is enough. Discourage authentication, payment integrations and deployment.

Each team uses a fresh disposable directory. Do not borrow a participant's production database, private repository or existing project memory store. Use fictional aliases. No credential sharing. Agents must stay inside the team workspace and must not send messages or publish anything on behalf of participants. Reviewing another team's supplied code does not authorize running arbitrary destructive scripts; inspect commands, dependency scripts and paths first and stop if a command escapes the fixture boundary.

## Opening script and HUSTEF reuse

1. Welcome and show the confident claim next to the empty tests directory. Introduce it as an illustrative example of a mismatch, not a measured result from tonight.
2. Walk the five HUSTEF patterns. Spend about one minute per pattern with an example of an observable check.
3. Explain that another team will execute checks against the exact delivered snapshot. An agent summary, a coverage badge or a persuasive demo alone cannot establish a pass.
4. Explain the timeline, source freeze, scope and reward status. Say only: 'Rewards have not been decided. Tonight's scoring follows the published rubric.'

Do not reuse the HUSTEF numerical research claims, tool-cost claims or product statistics for this opening. They are unnecessary for the exercise and would require separate current source verification. The original HUSTEF deck remains unchanged.

## Build checkpoints

- 20:40: start. Each team writes the smallest plan in team-plan.md and assigns a verifier.
- 20:50: look for a running skeleton. If none, narrow the stack and provide human setup help.
- 21:10: ask to see one reservation response and a stored record. Ask which assumption could make that response misleading.
- 21:25: remind teams to prioritize capacity, replay and restart. Optional features come later.
- 21:35: five-minute warning. Ask teams to locate README, tests and the state path.
- 21:40: stop adding features. Verification begins. Repairs are allowed only until 21:55.
- 21:55: freeze source and tests. Record a checksum or clean commit. No late source replacement.
- 22:00: evidence manifest and transfer artifact ready. Mark incomplete work explicitly.

Explain 'Uncommitted Illusion' as missing delivered work. A clean commit is one option, not a compulsory Git ceremony. A checksummed source archive that contains all intended work is equally valid. An uncommitted file outside that artifact cannot support a claim about it.

## Audit pairing and blocked targets

Use a directed ring: A audits B, B audits C, and the last team audits A. This gives every team one target even with an odd number of teams. For two teams, swap. With one team, facilitators audit and the team investigates a facilitator-approved copy; label the reduced independence.

Give the auditor the snapshot, not the builder's working directory. Builders can explain run instructions, but auditors perform the checks. Audit evidence stays in a separate sidecar folder bound to the target source identity.

If a target cannot start after five minutes, record the exact failure and request a facilitator. The auditor may still inspect the target and report the blocked start. If enough time remains, assign a second reachable artifact and record its identity separately. Never present that second target as evidence about the first. Judge C2–C3 against the named target actually investigated. C1 requires a successful independent start. C4 can reward a well-evidenced blocked result. Do not reduce a sound target's score because peers found no bugs.

No repair to the frozen target during audit. A fix can be tried in a separately labelled copy, but scores still refer to the frozen baseline. This prevents a moving target and protects reproducibility.

## Demos, scoring and debrief

With up to eight teams, allow two minutes per team plus four minutes total for transitions/adjudication. Each team gets 45 seconds of product behavior, 45 seconds for its strongest audit investigation, and 30 seconds for a lesson or limitation. For nine or more teams, use 90 seconds per team; do not extend the end time. No live install during demos. Prefer short replay of collected evidence plus a targeted rerun where possible.

Facilitators collect provisional AC results while circulating. The 20-minute demo round is not enough to rerun every criterion for every team; a functional score needs observed execution or a confirmed independent audit receipt. NOT RUN stays 0. Cross-check contested claims against their source identity and the PRD. Keep a decision log and apply clarifications equally.

Use the fixed 40/30/20/10 rubric. Each row is 0 or 5. Have the other facilitator check totals. Ties resolve by evidence, then audit, then app; share positions if still tied. Awards, prizes and sponsorships are not part of the calculation.

Debrief prompts: Which claim looked convincing until you investigated it? Which negative control changed your confidence? What did another team notice that you missed? Did any test validate the wrong requirement? What would you add to a daily handoff? Ask teams to state one practice, not one tool, they will take home.

## Contingencies

| Situation | Response |
| --- | --- |
| Ten-minute late start | Opening 10 minutes and team planning 5 minutes recover 10. Keep the 60-minute build, verification and audit. If lost time occurs later, reduce demos from 20 to 10. Finish at 23:15. |
| Wi-Fi or model outage | Continue with available local tools and manual work. No penalty for tool choice. Logs must label what actually ran. If building is impossible, switch to a documented paper review of the PRD and available source; score unexecuted functional rows 0 and report the mode honestly. |
| One team blocked by setup | Merge into a functioning team before build minute 20 or offer a verifier/evidence role. Avoid burning the whole session on installation. |
| No defects found | Require a documented challenge and bounded clean conclusion. Audit credit does not depend on finding a bug. |
| Dangerous command, real data or exposed secret | Stop the affected activity, isolate the fixture and ask its owner to handle the sensitive step. Do not project or copy the secret. Resume within scope. |
| Scoring dispute | Freeze the relevant receipt, ask for reproduction, record the ruling. No retroactive rubric inventions. |

## After the event

Return the team's evidence and score sheet. Share only materials teams authorize for sharing. Do not upload participant code, logs, identities or recordings automatically. Capture durable lessons without private data. Any later rewards decision is a separate organizer action.

## Sources and preparation boundary

Program and scoring weights: https://agiletestingdays.com/2026/session/completion-theater-hackathon-build-it-prove-it-smash-it/

Opening examples and five-pattern field guide adapted from Dragan Spiridonov’s HUSTEF 2026 Completion Theater material. The original talk remains unchanged. The public dry-run report distinguishes executed technical evidence from untested human-team and venue assumptions.
