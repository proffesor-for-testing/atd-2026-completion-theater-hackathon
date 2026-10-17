# Technical dry run, 17 October 2026

## What ran

One AI builder received the original starter PRD and implemented a plain HTML/JavaScript UI, Python standard-library HTTP API and SQLite store from scratch. A separate AI reviewer received only the frozen five-file submission and performed a cold-copy audit. These are distinct AI roles, not independent human teams and not evidence of provider diversity.

The build ran from 16:20:44 to 16:24:59.656 UTC: **4 minutes 15.7 seconds**, within the 60-minute ceiling. The timer includes implementation and builder checks, not the later independent audit or participant-tool development. This is a familiar-stack feasibility example, not a forecast for novice or mixed human teams. The complete solution is deliberately withheld from this participant repo.

## Executed evidence

- Reviewer cold copy matched all five frozen file hashes and remained unchanged after execution.
- Builder's nine tests passed. The reviewer independently reran them: nine passed, exit 0, no listed skips. Coverage was not measured.
- Separate API probes exercised seed counts, reservation readback, whitespace-trimmed replay, globally conflicting keys, sequential capacity, concurrent last-seat requests, cancellation/repeated cancellation/cancelled-key replay, all five invalid-input cases and unchanged counts.
- Actual browser form actions created a fictional booking, read its stored ID and cancelled it. UI seat counts agreed with API state.
- The reviewer stopped and restarted the real process without reset. Independent SQLite rows, fresh HTTP responses and browser lookup preserved active and cancelled records and counts.
- In a separate copy, bypassing the capacity guard caused an existing behavioral test to fail (201 instead of expected409), exit 1. The frozen baseline stayed unchanged.
- The shared verifier was separately exercised against the reference implementation through a declared fixture-state launcher adapter: seven API groups passed, including ten fresh batches of ten simultaneous requests for one remaining seat, and source hashes before/after matched. This adapter work occurred after the timed build. API results do not award UI or scoring points.
- Public helper tests exercise snapshot tampering/path attacks/exclusions, scoring rejection paths, incomplete apps, failed reset, source mutation, explicit interpreter launch and private-environment exclusion. CI reports platform-specific execution separately.

## Gaps found and fixed

| Gap | Revision |
| --- | --- |
| Cancellation checklist reset state but did not recreate its target booking | Each scenario now states its own setup. |
| Flexible response names consumed audit time | Shared JSON examples, response mappings and a tested adapter format. |
| A single race trial could pass a broken implementation by luck | Ten bounded batches, with a clear limit on the conclusion. |
| Late repair could invalidate earlier logs | Source content hashes before/after; earlier receipts must match the final freeze. |
| Transport changed a script from0755 to0644 and direct execution failed | Normalized-file protocol is explicit and interpreter-only launch is enforced before execution. Cold-copy interpreter launch was tested. |
| Adapter processes inherited private environment variables | Runtime allowlist removes inherited tokens; a fictional secret canary was absent in an executed check. This is not an OS sandbox. |
| Score totals could credit a team for somebody else's audit of it | Builder A/B and reviewer C are attributed separately. Event scoring needs actual human adjudication and a named independent team. |
| Health checks or helper CI could masquerade as product success | Incomplete scaffold is explicit, starter test begins red, API/manual boundaries remain NOT RUN until observed. |

The Agentic QE requirements parser was invoked first but extracted one item and zero testable criteria from the table-oriented PRD. It did not provide meaningful semantic validation. The conclusions above come from executed build/audit work and manual criterion review, not that parser's completion label.

## Scoring rehearsal

The builder demonstrated A40/40 and B30/30 when the complete source-bound evidence bundle and limits were submitted. It did not audit a second target, so its C is0/20, not the reviewer's20. No optional improvement or additional technique beyond the supplied checks was demonstrated, so D is0/10. **Builder rehearsal total:70/100.**

The separate reviewer demonstrated C20/20 after the builder acknowledged the bounded clean investigation. Those20 points belong to the reviewing role and cannot be added to the builder's total. Neither result qualifies a human team or grants any reward.

## Practical decision

Keep the core PRD for a prepared, AI-assisted team using a familiar stack. Supply preflight, scaffold, shared probes, API mapping, freeze and score helpers before the event. At minute10, help any team without a running skeleton narrow its approach. At minute30, require one stored reservation. Prioritize the core checks over optional features.

Still unverified: mixed human-team timing, venue network/power/projector, participant model access, all language stacks and independent real teams swapping artifacts. The CI matrix checks the helper kit, not those event conditions. Run a short rehearsal with Lalit before the event. Rewards remain open.

Source identification for the private rehearsal: SHA-256 of the builder's file-hash manifest was `75a5dc2b68b955241c315056d8d1357c5bc2adb5e20143e60ce859ad2286d9e8`. It is a manifest checksum, not a source archive hash. Private source and full local receipts are retained by the organizer; they are not bundled as an answer key.
