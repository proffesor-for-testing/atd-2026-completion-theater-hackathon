#!/usr/bin/env python3
"""Create/check/extract source-only snapshots; never restores over existing paths."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

EXCLUDED = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'evidence', 'runtime', 'data', '.state', '.pytest_cache', 'dist', 'build'}
MANIFEST = 'SNAPSHOT-MANIFEST.json'

def excluded(path):
    return any(p in EXCLUDED or (p.startswith('.env') and p != '.env.example') for p in path.parts) or path.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.log', '.pyc'} or path.name.endswith(('-wal', '-shm', '-journal'))

def source_files(root):
    root = Path(root).resolve(strict=True)
    files = {}
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if excluded(rel):
            continue
        if path.is_symlink():
            raise ValueError(f'Symlink refused: {rel}')
        if path.is_file():
            if rel.as_posix() == MANIFEST:
                raise ValueError('Reserved manifest name in source')
            files[rel.as_posix()] = path.read_bytes()
    if not files:
        raise ValueError('Empty source')
    return files

def identity(files):
    rows = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return digest, rows

def tree_hash(root):
    return identity(source_files(root))[0]

def create(root, archive):
    archive = Path(archive)
    if archive.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Archive must be outside source')
    files = source_files(root)
    source_id, rows = identity(files)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
        z.writestr(MANIFEST, json.dumps({'sourceId': source_id, 'files': rows}, sort_keys=True))
    return check(archive)

def read_archive(archive):
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entry')
        files = {}
        for info in z.infolist():
            name = info.filename
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or name != path.as_posix() or info.is_dir() or ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError(f'Unsafe archive entry: {name}')
            if name != MANIFEST and excluded(path):
                raise ValueError(f'Excluded content: {name}')
            if info.file_size > 50_000_000 or sum(x.file_size for x in z.infolist()) > 200_000_000:
                raise ValueError('Snapshot exceeds size bound')
            files[name] = z.read(info)
        if MANIFEST not in files:
            raise ValueError('Missing snapshot manifest')
        manifest = json.loads(files.pop(MANIFEST))
        source_id, rows = identity(files)
        if not files or manifest != {'sourceId': source_id, 'files': rows}:
            raise ValueError('Manifest/content mismatch')
        return files, source_id

def check(archive):
    files, source_id = read_archive(archive)
    return {'sourceId': source_id, 'artifactSha256': hashlib.sha256(Path(archive).read_bytes()).hexdigest(), 'files': len(files)}

def extract(archive, destination):
    files, _ = read_archive(archive)
    destination = Path(destination)
    # mkdir(exist_ok=False) rejects existing directories, files and symlinks.
    destination.mkdir(parents=False, exist_ok=False)
    for name, data in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as out:
            out.write(data)
        target.chmod(0o644)
    return check(archive)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('create'); p.add_argument('source'); p.add_argument('archive')
    p = sub.add_parser('check'); p.add_argument('archive')
    p = sub.add_parser('extract'); p.add_argument('archive'); p.add_argument('destination')
    args = parser.parse_args()
    try:
        result = create(args.source, args.archive) if args.command == 'create' else extract(args.archive, args.destination) if args.command == 'extract' else check(args.archive)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'ERROR: {exc}\n')

if __name__ == '__main__':
    main()
