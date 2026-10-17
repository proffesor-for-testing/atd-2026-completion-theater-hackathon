# Changes

## 1.1.0 — rehearsal revision, 17 October 2026

- Added a public, dependency-free participant kit with preflight, optional incomplete scaffold, source snapshot, black-box API challenges and explicit scoring validation.
- Made each verification scenario self-contained: the cancellation check now creates the reservation it cancels after reset.
- Documented JSON response mappings and configurable port/state launchers so cold audit does not depend on the builder's computer or undocumented schema.
- Bound receipts to source content hashes before and after execution. Earlier receipts only count if they identify the same frozen source.
- Added ten bounded concurrent batches and retained the limit: this is tested evidence, not a proof of atomicity.
- Kept UI/store inspection, meaningful test controls and human judgement separate from API checks.
- Clarified that audit points belong to the auditing team, not the team being audited. AI-only rehearsal scores do not qualify human teams.
- Defined normalized snapshot permissions and interpreter-based launch commands; added safe exclusions, tamper/path checks and no-overwrite extraction.
- Kept rewards undecided. The complete rehearsal app and private evidence remain outside this repository.
