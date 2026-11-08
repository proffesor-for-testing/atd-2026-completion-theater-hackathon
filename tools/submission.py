#!/usr/bin/env python3
"""Snapshot committed app bytes without checkout filters or executing submitted code."""
import argparse
from pathlib import Path, PurePosixPath
import re
import subprocess

import snapshot


def git(repository, *args):
    return subprocess.run(['git', '-C', str(repository), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def create(repository, commit, app_path, archive):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Use the full lowercase 40-character frozen commit SHA')
    app = PurePosixPath(app_path)
    if (not app_path or app_path in {'.', '..'} or app.is_absolute()
            or '..' in app.parts or '\\' in app_path or ':' in app_path
            or app.as_posix() != app_path):
        raise ValueError('App path must be a non-root relative POSIX directory')
    if Path(archive).resolve().is_relative_to((Path(repository) / app_path).resolve()):
        raise ValueError('Archive must be outside the declared app directory')
    resolved = git(repository, 'rev-parse', '--verify', commit + '^{commit}').decode().strip()
    if resolved != commit:
        raise ValueError('Submitted object is not the specified commit')
    entries = git(repository, 'ls-tree', '-r', '-z', commit, '--', ':(literal)' + app_path + '/')
    total = 0
    files = {}
    for entry in entries.split(b'\0'):
        if not entry:
            continue
        header, filename = entry.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split()
        name = filename.decode('utf-8')
        prefix = app_path + '/'
        if not name.startswith(prefix):
            raise ValueError('Git returned a path outside the declared app directory')
        rel = PurePosixPath(name[len(prefix):])
        if (rel.is_absolute() or '..' in rel.parts or '\\' in str(rel)
                or ':' in str(rel) or str(rel) != name[len(prefix):]):
            raise ValueError('Unsafe committed source path')
        if snapshot.excluded(rel):
            continue
        if mode not in {'100644', '100755'} or kind != 'blob':
            raise ValueError(f'Symlink/submodule or unsupported entry refused: {rel}')
        if str(rel) == snapshot.MANIFEST:
            raise ValueError('Reserved manifest name in source')
        size = int(git(repository, 'cat-file', '-s', oid).strip())
        total += size
        if size > 50_000_000 or total > 200_000_000:
            raise ValueError('Snapshot exceeds size bound')
        files[rel.as_posix()] = git(repository, 'cat-file', 'blob', oid)
    result = snapshot.write_archive(files, archive)
    return dict(result, commit=commit, appPath=app_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('snapshot', help='Package the declared directory at an exact local commit')
    p.add_argument('--commit', required=True)
    p.add_argument('--app-path', required=True)
    p.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    try:
        import json
        print(json.dumps(create(Path(__file__).resolve().parents[1], args.commit,
                                args.app_path, args.archive), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
