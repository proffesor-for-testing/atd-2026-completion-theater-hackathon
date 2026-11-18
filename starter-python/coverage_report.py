"""Measured line coverage of app.py while the test suite runs (stdlib only).

    python3 coverage_report.py [--fail-under PERCENT] [--json FILE] [unittest args]

Runs `python -m unittest test_app test_spec_gaps` with COVERAGE_DIR set; test_app then starts the
app under covtrace.py. Executable lines come from the compiled code (dis); executed
lines come from the traced app processes. Line coverage only: no branch coverage.
The exit status is non-zero if tests fail, no data was recorded, or the threshold is missed.
"""
import argparse
import dis
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types

HERE = Path(__file__).resolve().parent
TARGET = HERE / 'app.py'


def executable_lines(path):
    stack = [compile(Path(path).read_text(encoding='utf-8'), str(path), 'exec')]
    lines = set()
    while stack:
        code = stack.pop()
        lines.update(line for _, line in dis.findlinestarts(code) if line)
        stack.extend(c for c in code.co_consts if isinstance(c, types.CodeType))
    return lines


def executed_lines(data_dir, target):
    """Union of lines recorded for target by every traced process; (lines, files seen)."""
    lines, files = set(), 0
    for data in Path(data_dir).glob('*.json'):
        record = json.loads(data.read_text())
        if record['file'] == str(target):
            lines.update(record['lines'])
            files += 1
    return lines, files


def ranges(lines):
    out, run = [], []
    for n in sorted(lines):
        if run and n == run[-1] + 1:
            run.append(n)
        else:
            if run:
                out.append(run)
            run = [n]
    if run:
        out.append(run)
    return ', '.join(str(r[0]) if len(r) == 1 else '%d-%d' % (r[0], r[-1]) for r in out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--fail-under', type=float, default=None, help='exit non-zero below this percent')
    parser.add_argument('--json', help='also write the result to this file (keep it outside the app directory)')
    args, unittest_args = parser.parse_known_args(argv)
    with tempfile.TemporaryDirectory() as data_dir:
        env = dict(os.environ, COVERAGE_DIR=data_dir)
        tests = subprocess.run([sys.executable, '-m', 'unittest'] + (unittest_args or ['test_app', 'test_spec_gaps']),
                               cwd=HERE, env=env)
        executed, files = executed_lines(data_dir, TARGET)
    if files == 0:
        print('NO COVERAGE DATA: the app was never run under covtrace.py', file=sys.stderr)
        return 3
    possible = executable_lines(TARGET)
    hit = executed & possible
    missed = possible - hit
    percent = 100.0 * len(hit) / len(possible)
    print('\napp.py line coverage (measured, %d traced process(es)): %d/%d lines = %.1f%%'
          % (files, len(hit), len(possible), percent))
    print('missed lines:', ranges(missed) or 'none')
    if args.json:
        Path(args.json).write_text(json.dumps({
            'file': 'app.py', 'executableLines': len(possible), 'coveredLines': len(hit),
            'percent': round(percent, 2), 'missedLines': sorted(missed), 'testsExitCode': tests.returncode,
            'branchCoverage': None}, indent=2))
    if tests.returncode:
        print('TESTS FAILED (exit %d): coverage above is not meaningful' % tests.returncode, file=sys.stderr)
        return tests.returncode
    if args.fail_under is not None and percent < args.fail_under:
        print('COVERAGE %.1f%% is below --fail-under %.1f%%' % (percent, args.fail_under), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
