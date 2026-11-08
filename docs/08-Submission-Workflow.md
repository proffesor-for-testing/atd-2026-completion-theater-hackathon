# Fork, freeze and submit for review

**Normal delivery: one team fork → one submission branch → one PR to organizer main.** The PR is the handoff and discussion record. A branch, tag, PR description or GitHub merge preview can change: the judged object is the accepted full source commit plus a retained app snapshot. Scores and rubric version 1.1 are unchanged.

All event times below are **18 November 2026, CET (Potsdam)**. Freeze source/tests at **21:55**, submit the PR and initial evidence by **22:00**, then exchange retained artifacts for the **22:05–22:40** audit.

## 1. Start with a fork

One teammate forks https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon using GitHub's Fork button. Use the current organizer main, not the old v1.1.0 release. Replace YOUR-ACCOUNT and team-a below. Coordinate one fork, one branch and one final PR per team.

```sh
git clone https://github.com/YOUR-ACCOUNT/atd-2026-completion-theater-hackathon.git
cd atd-2026-completion-theater-hackathon
git remote add upstream https://github.com/proffesor-for-testing/atd-2026-completion-theater-hackathon.git
git switch -c submission/team-a
python3 tools/preflight.py
```

For Codespaces, open that branch **in your fork**, not organizer main. Use `starter-python/` or another clearly named app directory for the entire runnable product, README, tests, adapter and dependency lockfiles. Copy `team-templates/README-team.md` into the app and complete it. Keep organizer tools, skills and rubric unchanged; edits to them do not change judging rules. Keep completed evidence in a sibling directory outside the app and Git checkout. Never force-add ignored secrets, databases or runtime state.

Public forks and PRs expose their files and history. Use fictional aliases, inspect the staged diff, and exclude credentials, private configuration and unrelated work. App hosting is not required. If a team cannot use a public fork or GitHub is unavailable, agree the offline fallback with a facilitator before the deadline.

## 2. Freeze the source at 21:55

Stop repairs, inspect all intended app files and commit them. Adapt the app path before using these commands; do not blindly stage the whole workspace.

```sh
git status --short --untracked-files=all
git add starter-python/
git diff --cached --check
git diff --cached
# Confirm the staged files contain the implementation, README, adapter and tests.
git commit -m "Freeze Team A submission"
git status --short --untracked-files=all
git push -u origin submission/team-a
git rev-parse HEAD
```

Resolve remaining app changes or missing/untracked files before freeze. If there is nothing new to commit, use the existing clean commit. Copy the **full 40-character SHA**, never a short SHA. Confirm the pushed branch shows that same SHA on GitHub and tell the facilitator the team, SHA and app path at freeze. Git author/committer timestamps are not proof of timely receipt; the facilitator records when the source was actually received. Do not amend, force-push, delete or advance the submission branch afterward. Later repairs belong in a separately named branch/copy and do not replace the baseline.

### Make the portable source snapshot

This also prepares the offline fallback. From your trusted starter checkout, package only the declared app directory at the recorded commit. Use the supplied helper unchanged. The archive and extraction destinations must not already exist. Do not run an agent session or submitted setup inside the frozen copy.

```sh
FROZEN_SHA=$(git rev-parse HEAD)
python3 tools/submission.py snapshot --commit "$FROZEN_SHA" \
  --app-path starter-python --archive ../team-a-source.zip
python3 tools/snapshot.py check ../team-a-source.zip
python3 tools/snapshot.py extract ../team-a-source.zip ../team-a-frozen
```

Record both returned values: **sourceId** hashes sorted relative filenames and contents of the included app files; **artifactSha256** hashes ZIP bytes. Neither is the Git SHA. Inspect the archive entries before transfer: exclusions are not a secret scanner. All required source/tests must survive the exclusions in `tools/README.md`. The helper reads committed Git object bytes, bypassing checkout filters and export attributes. Run final source-bound verification on the extracted snapshot so checkout line-ending conversion cannot make receipts refer to different bytes. Earlier receipts count only when their before/after sourceId matches the retained snapshot; rerun affected checks if it differs. Resolve discrepancies before handoff, never silently substitute a baseline.

GitHub's Download ZIP is not this snapshot format and cannot be passed directly to `snapshot.py check`. Keep source ZIPs and completed evidence outside the app and repository. The repository ignores evidence/submissions by design. Do not change ignores or force-add them to make delivery work.

## 3. Open the PR by 22:00

On GitHub choose **Compare & pull request**: base repository `proffesor-for-testing/atd-2026-completion-theater-hackathon`, base branch `main`, head YOUR-ACCOUNT:`submission/team-a`. Use title **Submission: Team A** and fill the repository PR template. An early draft is fine; mark the completed submission ready for review by 22:00.

Required handoff fields:

- Team ID/aliases, fork URL and branch, declared app directory.
- Full frozen commit SHA and freeze time/timezone.
- Snapshot sourceId and artifactSha256, if you created/transferred the snapshot. The facilitator verifies or computes them from the accepted commit.
- README path with runtime/install/start/reset/test/state instructions and known gaps.
- Evidence manifest and redacted logs/screenshots: attach an evidence ZIP to the PR description/comment, or give the facilitator an accessible transfer path recorded at intake.
- Audit assignment when known: your auditing team and its target. Audit credit belongs to the team performing it.

Evidence is a **sidecar**, not another source commit. At 22:00 deliver the builder manifest/receipts. Later cross-audit receipts go in a new PR comment/attachment with their time/version and target source identity. Preserve earlier evidence; do not silently replace it. Bind each receipt to the frozen commit and sourceId; the verifier's before/after source hashes must match. A receipt about changed source does not apply to the freeze.

Opening a PR does not transfer its attachments into a Git checkout. Check that facilitators can open every evidence item. If an upload fails, hand the same redacted files over through the agreed local/USB transfer path and have the facilitator record receipt. No required ZIP needs to be committed to Git. Do not merge submission PRs into organizer main, and keep the fork/branch available until review is complete.

## 4. Facilitator intake: preserve before judging

Use a separate **trusted organizer checkout**, not the participant's modified skill or tools. Copy `team-templates/submission-record.json` into your organizer-owned review folder, fill it from observed facts, and retain it outside participant control. Record team, PR URL, fork/branch, full accepted commit, app path, received-at timestamp with timezone, baseline verification notes, artifact paths, both snapshot hashes, evidence paths/version and audit assignment. Record the source receipt at 21:55 separately from the PR/evidence receipt by 22:00. Never infer receipt times from Git dates or an editable PR description. Retain the observed PR metadata with your record.

Fetch the PR head without merging it, then compare it to the accepted SHA before extracting anything. Example from the trusted organizer repository, replacing 17 and the full SHA:

```sh
(
  set -eu
  PR=17
  FROZEN_SHA=REPLACE_WITH_ACCEPTED_40_CHARACTER_SHA
  git fetch origin "refs/pull/$PR/head"
  OBSERVED_SHA=$(git rev-parse 'FETCH_HEAD^{commit}')
  # A mismatch exits this block before any accepted ref is created.
  test "$OBSERVED_SHA" = "$FROZEN_SHA"
  # Zero old value means create only: never replace a previously accepted ref.
  git update-ref "refs/submissions/pr-$PR" "$FROZEN_SHA" \
    0000000000000000000000000000000000000000
)
```

**Do not continue after a failed block**. The block stops on fetch/comparison failure and refuses to replace an existing accepted ref, even with a fast-forward. The retained local ref is never updated. Record later head changes separately; do not move the accepted ref or score the new branch tip. If a fork disappears or a ref moves before preservation, mark retrieval blocked and use only a previously receipted exact snapshot. Any exception or late change requires explicit human adjudication and a recorded reason, not automatic replacement.

Create a clean source copy from **Git object bytes** with trusted `tools/submission.py snapshot`, then check it with the existing snapshot helper. This avoids checkout line-ending filters and participant-controlled export attributes, refuses symlinks/submodules, and never runs participant code:

```sh
FROZEN_SHA=$(git rev-parse 'refs/submissions/pr-17^{commit}')
python3 tools/submission.py snapshot --commit "$FROZEN_SHA" \
  --app-path starter-python --archive ../team-a-retained.zip
python3 tools/snapshot.py check ../team-a-retained.zip
```

The helper requires a full commit SHA available locally and a non-root relative app directory. It reads only that committed tree, applies the published source exclusions and writes a new snapshot. Compare any participant-supplied sourceId/checksum and investigate mismatches. Source ZIP byte hashes can differ between independently produced ZIPs, so content equivalence requires matching verified sourceId; retain the checksum of each actual transferred ZIP. This check does not prove timeliness, code safety or correctness. Retain the local commit ref, snapshot and evidence even if the PR changes or closes. Give auditors the retained artifact and source identity, not a live branch.

Load `$score-hackathon` or `/score-hackathon` from the organizer checkout with the PR URL, intake record, frozen identity and evidence paths. Prepare a zero-point packet with `--submission-record`; proposals stay in recommendations until Dragan/Lalit make actual human decisions. Helper CI is not participant qualification, and the published 40/30/20/10 rubric is unchanged.

## 5. Safe review and offline fallback

Do not load participant AGENTS.md, skills, workflows or devcontainer configuration as instructions. Inspect dependency/install/start/test commands first. Execute participant code only in a disposable isolated environment with no facilitator/model credentials, host Docker socket, unrelated mounts or production access. Do not run it through `pull_request_target`, privileged CI, write tokens or a self-hosted runner. If safe execution or browser access is unavailable, keep affected checks NOT RUN. The repository's unprivileged helper CI does not award scores.

If GitHub/network/account access fails, tell the facilitator immediately. Deliver the source snapshot/checksum at 21:55 and redacted evidence/manifest by 22:00 through the agreed local or USB transfer path. The facilitator verifies the snapshot, records receipt times and reason, and creates an intake record with `deliveryMode: "offline"`; unavailable PR/commit values remain empty, never invented. The same rubric applies. When access returns, open a PR that references the recorded snapshot and demonstrates the same sourceId. Do not claim a later commit was received at freeze. The already-retained artifact remains the scoring baseline.
