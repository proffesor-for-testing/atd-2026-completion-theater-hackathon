#!/usr/bin/env python3
"""Check helper runtime and loopback availability; does not qualify the app."""
import argparse
import json
import socket
import sqlite3
import sys

def check():
    results = {'python': sys.version.split()[0], 'runtimePath': sys.executable,
               'python311OrNewer': sys.version_info >= (3, 11),
               'sqliteVersion': sqlite3.sqlite_version, 'appStatus': 'NOT RUN'}
    try:
        with sqlite3.connect(':memory:') as db:
            results['sqliteAvailable'] = db.execute('select 1').fetchone() == (1,)
    except sqlite3.Error as exc:
        results['sqliteAvailable'] = False; results['sqliteError'] = str(exc)
    try:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            results['loopbackAvailable'] = True
    except OSError as exc:
        results['loopbackAvailable'] = False; results['loopbackError'] = str(exc)
    results['helperReady'] = all(results[k] for k in ('python311OrNewer','sqliteAvailable','loopbackAvailable'))
    return results

def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    result=check(); print(json.dumps(result,indent=2))
    return 0 if result['helperReady'] else 1

if __name__=='__main__': sys.exit(main())
