"""Tests for the coverage tooling itself, so a wrong percentage can't pass unnoticed."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

import coverage_report

HERE = Path(__file__).resolve().parent

SOURCE = textwrap.dedent('''\
    def used(x):
        if x:
            return 1
        return 2


    def never_called():
        return 3


    print(used(True))
''')


class CoverageToolTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.script = self.tmp / 'sample.py'
        self.script.write_text(SOURCE)

    def trace(self, *extra_env):
        data = self.tmp / 'data'
        data.mkdir()
        subprocess.run([sys.executable, str(HERE / 'covtrace.py'), str(self.script)],
                       env=dict(os.environ, COVERAGE_DIR=str(data)), check=True,
                       capture_output=True, timeout=30)
        return data

    def test_executable_lines_cover_nested_functions(self):
        lines = coverage_report.executable_lines(self.script)
        self.assertEqual(lines, {1, 2, 3, 4, 7, 8, 11})

    def test_traced_run_reports_exact_missed_lines(self):
        executed, files = coverage_report.executed_lines(self.trace(), self.script.resolve())
        self.assertEqual(files, 1)
        missed = coverage_report.executable_lines(self.script) - executed
        self.assertEqual(missed, {4, 8})  # `return 2` and the body of never_called

    def test_other_files_are_ignored_and_empty_data_is_detected(self):
        executed, files = coverage_report.executed_lines(self.trace(), self.tmp / 'other.py')
        self.assertEqual((executed, files), (set(), 0))

    def test_ranges_format(self):
        self.assertEqual(coverage_report.ranges({1, 2, 3, 7, 9, 10}), '1-3, 7, 9-10')
        self.assertEqual(coverage_report.ranges(set()), '')

    def test_report_fails_when_below_threshold_and_writes_json(self):
        out = self.tmp / 'cov.json'
        result = subprocess.run([sys.executable, str(HERE / 'coverage_report.py'), '--fail-under', '101',
                                 '--json', str(out), 'test_app.StartupSafety'],
                                cwd=HERE, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('below --fail-under', result.stderr)
        data = json.loads(out.read_text())
        self.assertIsNone(data['branchCoverage'])
        self.assertLess(data['percent'], 101)

    def test_report_propagates_test_failure(self):
        result = subprocess.run([sys.executable, str(HERE / 'coverage_report.py'), 'test_nonexistent_module'],
                                cwd=HERE, capture_output=True, text=True, timeout=120)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
