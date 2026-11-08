#!/usr/bin/env python3
"""Prepare unscored judging packets or rank declared scores; never infer evidence."""
import argparse
import json
import datetime
import re
from urllib.parse import urlparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
from score import validate  # noqa: E402


def validate_submission(record, team, source_id):
    """Validate declared provenance shape only; never attest GitHub, timing or bytes."""
    if not isinstance(record, dict):
        raise ValueError('Submission record must be an object')
    required = ('deliveryMode', 'team', 'prUrl', 'forkUrl', 'branch', 'commit',
                'appPath', 'sourceReceivedAt', 'receivedAt', 'sourceId',
                'artifactSha256', 'archivePath', 'evidencePath', 'evidenceVersion',
                'verificationNotes')
    if any(not isinstance(record.get(k), str) for k in required):
        raise ValueError('Submission record fields must be strings')
    if record['team'].strip() != team.strip() or record['sourceId'] != source_id.strip():
        raise ValueError('Submission team/sourceId must match the judging packet')
    if record['deliveryMode'] not in {'pr', 'offline'}:
        raise ValueError('deliveryMode must be pr or offline')
    for field in ('sourceId', 'artifactSha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', record[field]):
            raise ValueError(f'{field} must be a full lowercase SHA-256')
    if record['commit'] and not re.fullmatch(r'[0-9a-f]{40}', record['commit']):
        raise ValueError('commit must be a full lowercase 40-character SHA')
    if record['prUrl'] and not re.fullmatch(
            r'https://github\.com/proffesor-for-testing/atd-2026-completion-theater-hackathon/pull/[1-9][0-9]*', record['prUrl']):
        raise ValueError('prUrl must identify a submission PR in the organizer repository')
    if record['deliveryMode'] == 'pr':
        if not record['commit'] or not record['prUrl'] or not record['branch'].strip():
            raise ValueError('PR intake requires commit, prUrl and branch')
        fork = urlparse(record['forkUrl'])
        if fork.scheme != 'https' or fork.netloc != 'github.com' or len(fork.path.strip('/').split('/')) != 2 or fork.query or fork.fragment:
            raise ValueError('forkUrl must be an HTTPS GitHub repository URL')
    path = Path(record['appPath'])
    if (not record['appPath'] or path.is_absolute() or '..' in path.parts
            or record['appPath'] == '.' or '\\' in record['appPath'] or ':' in record['appPath']):
        raise ValueError('appPath must be a non-root relative directory')
    for field in ('sourceReceivedAt', 'receivedAt'):
        try:
            observed = datetime.datetime.fromisoformat(record[field].replace('Z', '+00:00'))
            if observed.tzinfo is None:
                raise ValueError('timezone required')
        except ValueError as exc:
            raise ValueError(f'{field} must be an actual ISO timestamp with timezone') from exc
    for field in ('archivePath', 'evidencePath', 'evidenceVersion', 'verificationNotes'):
        if not record[field].strip():
            raise ValueError(f'{field} must be recorded')
    return record


def prepare(team, source_id, output, submission_record=None):
    if not team.strip() or not source_id.strip():
        raise ValueError('Team and frozen source identity must be non-empty')
    record = None
    if submission_record is not None:
        record = validate_submission(json.loads(Path(submission_record).read_text()), team, source_id)
    data = json.loads((ROOT / 'tools/example-score.json').read_text())
    data.update(team=team.strip(), sourceId=source_id.strip(), auditTargetTeam='')
    validate(data)
    output = Path(output)
    output.mkdir(exist_ok=False)
    if record is not None:
        (output / 'submission.json').write_text(json.dumps(record, indent=2) + '\n')
    (output / 'score.json').write_text(json.dumps(data, indent=2) + '\n')
    lines = [f'# Provisional recommendations: {data["team"]}',
             f'Frozen source: {data["sourceId"]}',
             'AI assistance only. No event points awarded. Human decisions remain pending.',
             'Intake provenance: submission.json (declared metadata, not independently verified).' if record else 'Intake provenance: not supplied; event PR review requires organizer intake.',
             '', '| Row | Status / evidence class | Source-bound receipt and expected vs actual | Proposed 0/5 and reason | Human decision |',
             '| --- | --- | --- | --- | --- |']
    lines.extend(f'| {row} | NOT RUN | | 0: not evaluated | Pending |' for row in data['rows'])
    lines.extend(['', 'Auditing team: PENDING', 'Audit target team: PENDING',
                  'Investigations considered (maximum two): PENDING',
                  'Disputes, unavailable checks and limits: PENDING',
                  'Second facilitator arithmetic check: PENDING', 'Rewards: OPEN', ''])
    (output / 'recommendations.md').write_text('\n'.join(lines))
    return {'packet': str(output), 'team': data['team'], 'total': 0,
            'notice': 'Unscored packet. No checks executed and no human decisions recorded.'}


def scoreboard(paths):
    results, teams = [], set()
    for path in paths:
        data = json.loads(Path(path).read_text())
        result = validate(data)
        team, source_id = data.get('team'), data.get('sourceId')
        if not isinstance(team, str) or not team.strip() or not isinstance(source_id, str) or not source_id.strip():
            raise ValueError(f'{path}: non-empty team and sourceId required')
        if data['mode'] != 'event':
            raise ValueError(f'{path}: rehearsal scores do not belong on the event scoreboard')
        identity = team.strip().casefold()
        if identity in teams:
            raise ValueError(f'Duplicate team: {team}; choose one adjudicated score per team')
        teams.add(identity)
        results.append(dict(team=team.strip(), sourceId=source_id, scoreFile=str(path),
                            categories=result['categories'], total=result['total']))
    def ordering(row):
        c = row['categories']
        return row['total'], c['B'], c['C'], c['A']
    results.sort(key=ordering, reverse=True)
    previous, rank = None, 0
    for position, row in enumerate(results, 1):
        key = ordering(row)
        if key != previous:
            rank = position
        row['position'] = rank
        previous = key
    return {'scores': results, 'notice': 'Declared event scores only; humans must verify evidence and identities. Remaining ties share a position. Rewards OPEN.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    create = sub.add_parser('prepare', help='Create a new zero-point packet without overwriting')
    create.add_argument('--team', required=True)
    create.add_argument('--source-id', required=True)
    create.add_argument('--output', type=Path, required=True)
    create.add_argument('--submission-record', type=Path, help='Organizer intake JSON; checks metadata shape only')
    board = sub.add_parser('scoreboard', help='Rank human-adjudicated event score files')
    board.add_argument('score_json', nargs='+', type=Path)
    args = parser.parse_args()
    try:
        result = prepare(args.team, args.source_id, args.output, args.submission_record) if args.action == 'prepare' else scoreboard(args.score_json)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
