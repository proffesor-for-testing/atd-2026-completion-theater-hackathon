#!/usr/bin/env python3
"""Prepare unscored judging packets or rank declared scores; never infer evidence."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
from score import validate  # noqa: E402


def prepare(team, source_id, output):
    if not team.strip() or not source_id.strip():
        raise ValueError('Team and frozen source identity must be non-empty')
    data = json.loads((ROOT / 'tools/example-score.json').read_text())
    data.update(team=team.strip(), sourceId=source_id.strip(), auditTargetTeam='')
    validate(data)
    output = Path(output)
    output.mkdir(exist_ok=False)
    (output / 'score.json').write_text(json.dumps(data, indent=2) + '\n')
    lines = [f'# Provisional recommendations: {data["team"]}',
             f'Frozen source: {data["sourceId"]}',
             'AI assistance only. No event points awarded. Human decisions remain pending.',
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
    board = sub.add_parser('scoreboard', help='Rank human-adjudicated event score files')
    board.add_argument('score_json', nargs='+', type=Path)
    args = parser.parse_args()
    try:
        result = prepare(args.team, args.source_id, args.output) if args.action == 'prepare' else scoreboard(args.score_json)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
