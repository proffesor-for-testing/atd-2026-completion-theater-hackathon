---
name: git-workflow
description: How this team commits, syncs, resolves conflicts and freezes during the hackathon (one submission branch, small green commits, hard freeze at 21:55 CET). Use it whenever you are about to commit, pull, push, branch, resolve a merge conflict, or freeze and submit.
---

# Git workflow

Within a short time box, long-lived branches cost more than they protect. The team shares **one branch, `submission/<team-id>`, on the team's fork**, commits small and keeps it green so anyone can pull at any time. Full submission rules: `docs/08-Submission-Workflow.md`.

## Commit
- Commit on every green test run that adds value. Several commits per AC is normal.
- Message format: `AC-03: reserve seat and read back by id`. Use `chore: …` / `test: …` / `fix: …` for work not tied to an AC.
- The only commit allowed with a failing test is the one that adds a new AC's test: `AC-04: red — capacity acceptance test`. Don't push it on its own. Push it together with the commit that turns it green.
- Never commit `.env`, secrets, `.state/`, `*.db` or evidence files (`.gitignore` covers these, so don't force-add them).

## Sync
```bash
cd starter-python
python -m unittest discover -s tests -t . -v   # green before you push
git pull --rebase
python -m unittest discover -s tests -t . -v   # still green after teammates' changes?
git push
```
Pull at least every ~10 minutes. A small conflict is cheap and a large one is not.

## Conflicts
- `app.py` is the hotspot. Keep both behaviours, then run the full suite; the tests are the referee.
- If you can't resolve a conflict in about 3 minutes, ask the teammate who wrote the other side.
- If a teammate's push turns the branch red, tell them right away. Don't fix their AC silently.

## Freeze (21:55 CET), the "Uncommitted Illusion" check
```bash
git status                 # must be clean: nothing judged may live only on a laptop
git push
git rev-parse HEAD         # record this full 40-char SHA in the PR
```
After freeze, push nothing more to the branch. Open the PR to organizer `main` by 22:00. Evidence goes in PR comments or attachments, never as new commits.
