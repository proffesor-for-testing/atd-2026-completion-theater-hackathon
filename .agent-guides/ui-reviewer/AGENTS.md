# UI reviewer instructions

Agent ID: `/root/ui_reviewer`

Required independent review/reporting relationship: Coordinator receives your independent review; you review UI builder.

Read the repository AGENTS.md and starter-python/AGENTS.md before work. The shared evidence/review contract is mandatory; this role guide narrows it.

## Assigned scope

Read-only static UI source/diff and recorded browser/syntax receipts; no writes/mutation.

## Requirement and acceptance traceability

Same UI requirements/AC contributions as ui-builder. These ACs are contribution mappings, not permission to claim the entire criterion PASS without UI/store/process/frozen-source evidence.

## Work and proof

Independently check API field/path assumptions, state refresh/races, key replay/cancel semantics, accessible labels/focus/status/error feedback, safe rendering/local assets and responsive behavior. Include actual file hashes and source lines. Separate static assessment from browser/platform execution.

## Handoff gate

Provide the structured builder/reviewer report required by starter-python/AGENTS.md, including exact IDs, actual source/file hashes, named checks, expected/observed, evidence class, commands/status/exits/timestamps/raw paths, findings disposition, gaps and explicit ownership release. Missing execution stays NOT RUN. Only the current editing owner persists reports; read-only reviewers send them to the coordinator.

Plan/RTM: /Users/ukusaviauk/.codex/visualizations/2026/11/18/01a1f035-38c6-7383-a762-e8c24601e9cb/session-seat-desk-plan/requirements-matrix.json (external build planning artifact, not an app runtime dependency).

