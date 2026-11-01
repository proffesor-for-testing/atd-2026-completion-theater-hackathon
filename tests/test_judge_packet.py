"""Judging helpers preserve zero defaults, final-score boundaries and published ties."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('judge_packet', ROOT / '.agents/skills/score-hackathon/scripts/judge_packet.py')
packet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packet)


class JudgePacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write_score(self, team, awarded=(), mode='event'):
        path = self.root / (team + '.json')
        data = json.loads((ROOT / 'tools/example-score.json').read_text())
        data.update(team=team, sourceId='frozen-source-' + team, mode=mode,
                    independentAuditTeam='Auditing team', independentAuditTeamType='human')
        for key in awarded:
            data['rows'][key].update(points=5, status='PASS', evidence='receipt.json#' + key,
                                     adjudicator='Human judge', adjudicatorType='human')
        path.write_text(json.dumps(data))
        return path

    def test_packet_is_unscored_and_never_overwrites(self):
        out = self.root / 'team-a'
        packet.prepare('Team A', 'source:abc', out)
        data = json.loads((out / 'score.json').read_text())
        self.assertEqual(packet.validate(data)['total'], 0)
        self.assertTrue(all(r['status'] == 'NOT RUN' and not r['adjudicator'] for r in data['rows'].values()))
        with self.assertRaises(FileExistsError):
            packet.prepare('Other', 'source:def', out)
        self.assertEqual(json.loads((out / 'score.json').read_text())['team'], 'Team A')

    def test_published_ties_use_b_then_c_then_a_and_share_remaining_tie(self):
        paths = [self.write_score('App', ['A1']), self.write_score('Evidence', ['B1']),
                 self.write_score('Audit', ['C1']), self.write_score('Creative', ['D1']),
                 self.write_score('Same', ['B2'])]
        result = packet.scoreboard(paths)['scores']
        self.assertEqual([r['team'] for r in result], ['Evidence', 'Same', 'Audit', 'App', 'Creative'])
        self.assertEqual([r['position'] for r in result], [1, 1, 3, 4, 5])

    def test_rejects_ai_event_credit_rehearsals_and_duplicate_teams(self):
        p = self.write_score('Team', ['A1'])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            packet.scoreboard([p, p])
        data = json.loads(p.read_text()); data['rows']['A1']['adjudicatorType'] = 'ai'
        p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            packet.scoreboard([p])
        with self.assertRaisesRegex(ValueError, 'rehearsal'):
            packet.scoreboard([self.write_score('Trial', mode='rehearsal')])


if __name__ == '__main__':
    unittest.main()
