#!/usr/bin/env python3
"""Validate a human adjudicated score JSON. Never infer points from API checks."""
import argparse
import json
from pathlib import Path

ROWS = {f'{category}{i}' for category, count in [('A', 8), ('B', 6), ('C', 4), ('D', 2)] for i in range(1, count + 1)}

def validate(data):
    mode = data.get('mode')
    if mode not in ('event', 'rehearsal'):
        raise ValueError('mode must be event or rehearsal')
    rows = data['rows']
    if set(rows) != ROWS:
        raise ValueError('Exactly A1-A8, B1-B6, C1-C4, D1-D2 required')
    totals = dict.fromkeys('ABCD', 0)
    for key, row in rows.items():
        points = row.get('points')
        status = row.get('status')
        if type(points) is not int or points not in (0, 5) or status not in ('PASS', 'FAIL', 'NOT RUN'):
            raise ValueError(f'{key}: points must be 0/5; status PASS/FAIL/NOT RUN')
        if points == 5 and (status != 'PASS' or not isinstance(row.get('evidence'), str) or not row['evidence'].strip() or not isinstance(row.get('adjudicator'), str) or not row['adjudicator'].strip()):
            raise ValueError(f'{key}: 5 needs PASS, evidence and named adjudicator')
        if points == 5:
            kind = row.get('adjudicatorType', data.get('adjudicatorType'))
            if kind not in ('human', 'ai') or (mode == 'event' and kind != 'human'):
                raise ValueError(f'{key}: event points require adjudicatorType=human; rehearsal permits human or ai')
        if key.startswith('C') and points == 5 and not data.get('independentAuditTeam', '').strip():
            raise ValueError('C points require named independent audit team')
        if key.startswith('C') and points == 5 and data.get('independentAuditTeamType') not in (('human',) if mode == 'event' else ('human', 'ai')):
            raise ValueError('C points require independentAuditTeamType; event requires human')
        totals[key[0]] += points
    notice = 'Valid arithmetic/schema only; declared identities and evidence require human verification.'
    if mode == 'rehearsal':
        notice += ' REHEARSAL ONLY: does not qualify a human team or establish independent human cross-audit.'
    return {'mode': mode, 'categories': totals, 'total': sum(totals.values()), 'maximum': 100, 'notice': notice}

def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('score_json', type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(validate(json.loads(args.score_json.read_text())), indent=2))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        p.exit(1, f'ERROR: {exc}\n')

if __name__ == '__main__':
    main()
