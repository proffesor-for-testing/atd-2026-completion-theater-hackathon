#!/usr/bin/env python3
"""Bounded loopback API challenges. API PASS is not a full AC PASS or a score.

Starts only owned child processes. Each scenario gets NEW disposable DATA_DIR;
restart alone reuses that scenario's data. Evidence directory must be new and
outside source. Adapter commands run as argv arrays (never through a shell).
Run untrusted submissions in your own isolated OS/container environment.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import shutil
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from snapshot import tree_hash

DEFAULTS = json.loads(Path(__file__).with_name('adapter.example.json').read_text())['fields']
RUNTIME_ENV = {'PATH', 'SystemRoot', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TMP', 'TEMP', 'TMPDIR', 'LANG', 'LC_ALL', 'PYTHONUTF8', 'PYTHONIOENCODING', 'HOME', 'USERPROFILE'}

def validate_adapter(config):
    if not isinstance(config, dict) or set(config) - {'start', 'reset', 'fields'}:
        raise ValueError('Adapter must be an object with start, reset and optional fields')
    for name in ('start', 'reset'):
        cmd = config.get(name)
        if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x and '\x00' not in x for x in cmd):
            raise ValueError(f'{name} must be a non-empty argv string array')
    fields = config.get('fields', {})
    if not isinstance(fields, dict) or set(fields) - set(DEFAULTS):
        raise ValueError('Unknown response field mapping')
    for name, path in fields.items():
        if not isinstance(path, str) or (not path and name not in ('reservation', 'sessions')) or (path and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*', path)):
            raise ValueError(f'Invalid response object field path: {name}')
    return config

def runtime_environment(port, state):
    env = {key: value for key, value in os.environ.items() if key in RUNTIME_ENV}
    env.update(PORT=str(port), DATA_DIR=str(state))
    return env

def validate_launch_commands(config, source):
    """Snapshot file modes normalize to 0644: launch via installed interpreters."""
    source = Path(source).resolve(strict=True)
    for name in ('start', 'reset'):
        first = config[name][0].replace('{python}', sys.executable)
        if '{port}' in first or '{state_dir}' in first:
            raise ValueError(f'{name}: runtime executable cannot depend on fixture placeholders')
        # Treat both separators as paths even when auditing another OS's adapter.
        normalized = first.replace('\\', '/')
        candidate = Path(normalized)
        resolved = (candidate if candidate.is_absolute() else source / candidate).resolve()
        if resolved.is_relative_to(source) and (candidate.is_absolute() or '/' in normalized or resolved.is_file()):
            raise ValueError(f'{name}: direct source executable refused; invoke an installed interpreter with the source script as its next argument')
        located = shutil.which(first, path=os.environ.get('PATH', os.defpath))
        if located and Path(located).resolve().is_relative_to(source):
            raise ValueError(f'{name}: PATH resolves to a source executable; invoke an installed interpreter')

def field(value, path):
    for part in path.split('.') if path else []:
        value = value[part]
    return value

class Run:
    def __init__(self, source, config, evidence):
        self.source, self.config, self.evidence = source, config, evidence
        self.fields = DEFAULTS | config.get('fields', {})
        self.lock = threading.Lock(); self.process = None; self.log = None
        self.receipts = []; self.generation = 0; self.source_id = tree_hash(source)

    def command(self, name):
        cmd = self.config[name]
        if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x for x in cmd):
            raise ValueError(f'{name} must be a non-empty argv string array')
        return [x.replace('{port}', str(self.port)).replace('{state_dir}', str(self.state)).replace('{python}', sys.executable) for x in cmd]

    def event(self, **data):
        with self.lock:
            self.receipts.append({'time': time.time(), 'scenario': self.scenario, 'sourceId': self.source_id, **data})

    def fresh(self, name):
        self.stop(); self.scenario = name
        self.state = self.evidence / ('state-' + name); self.state.mkdir()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); self.port = sock.getsockname()[1]
        self.env = runtime_environment(self.port, self.state)
        cmd = self.command('reset')
        reset = subprocess.run(cmd, cwd=self.source, env=self.env, capture_output=True, timeout=20, shell=False)
        self.event(kind='reset', argv=cmd, exitCode=reset.returncode, stdout=reset.stdout.decode(errors='replace'), stderr=reset.stderr.decode(errors='replace'))
        if reset.returncode:
            raise AssertionError('Reset command failed')
        self.start()

    def start(self):
        self.generation += 1
        self.log = (self.evidence / f'process-{self.scenario}-{self.generation}.log').open('wb')
        cmd = self.command('start')
        self.process = subprocess.Popen(cmd, cwd=self.source, env=self.env, stdout=self.log, stderr=subprocess.STDOUT, shell=False)
        self.event(kind='start', argv=cmd, pid=self.process.pid, port=self.port, stateDir=str(self.state))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError('App exited before readiness')
            try:
                if self.http('GET', '/sessions')[0] == 200:
                    return
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(.1)
        raise AssertionError('Readiness timed out')

    def stop(self):
        if self.process:
            process = self.process
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
            self.event(kind='stop', pid=process.pid, exitCode=process.returncode)
            self.process = None
        if self.log:
            self.log.close(); self.log = None

    def http(self, method, path, payload=None, raw=None):
        body = raw if raw is not None else json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=body, method=method, headers={'Content-Type':'application/json'})
        # Disable redirects: an app must not move a probe outside loopback.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs): return None
        try:
            response = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect).open(request, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            status = response.code; text = response.read(1_000_001).decode(errors='replace')
        self.event(kind='http', method=method, path=path, request=body.decode(errors='replace') if body else None, status=status, response=text)
        if len(text) > 1_000_000: raise AssertionError('Response too large')
        return status, json.loads(text)

    def record(self, result):
        assert 200 <= result[0] < 300, f'Expected 2xx, got {result[0]}'
        row = field(result[1], self.fields['reservation'])
        normalized = {key: field(row, self.fields[key]) for key in ('reservationId','sessionId','attendeeAlias','requestKey','status')}
        assert isinstance(normalized['reservationId'], str) and normalized['reservationId'], 'Stable nonempty string ID required'
        return normalized

    def reserve(self, key, alias='Ada', session='CT-101'):
        return self.http('POST', '/reservations', {'sessionId':session,'attendeeAlias':alias,'requestKey':key})

    def sessions(self):
        code, payload = self.http('GET', '/sessions'); assert code == 200
        rows = field(payload, self.fields['sessions'])
        assert len(rows) == 2
        result = {field(row,self.fields['sessionRecordId']): {k:field(row,self.fields[k]) for k in ('capacity','activeCount','remainingSeats')} for row in rows}
        assert set(result) == {'CT-101','CT-102'}
        for key, cap in [('CT-101',2),('CT-102',3)]:
            r = result[key]
            assert all(type(r[k]) is int for k in r), 'Counts must be integers'
            assert r['capacity'] == cap and 0 <= r['activeCount'] <= cap and r['remainingSeats'] == cap-r['activeCount']
        return result

    def rejected(self, result):
        assert 400 <= result[0] < 500, f'Expected 4xx, got {result[0]}'
        assert isinstance(result[1],dict) and result[1].get('error'), 'Clear JSON error required'

    def challenge(self, name, batches):
        self.fresh(name)
        initial = self.sessions()
        assert [initial[x]['activeCount'] for x in ('CT-101','CT-102')] == [0,0]
        if name == 'AC02': return
        if name == 'AC03':
            r = self.record(self.reserve('K1')); assert r == {'reservationId':r['reservationId'],'sessionId':'CT-101','attendeeAlias':'Ada','requestKey':'K1','status':'active'}
            assert self.record(self.http('GET','/reservations/'+r['reservationId'])) == r
            assert self.sessions()['CT-101']['remainingSeats'] == 1
        elif name == 'AC04':
            self.record(self.reserve('K1')); self.record(self.reserve('K2','Bob'))
            before = self.sessions(); self.rejected(self.reserve('K3','Cy')); assert self.sessions()==before
            for i in range(batches):
                self.fresh(f'AC04-batch-{i+1}'); self.record(self.reserve('seed'))
                barrier = threading.Barrier(10)
                def attempt(j):
                    barrier.wait(timeout=5); return self.reserve(f'race-{j}',f'Alias-{j}')
                with ThreadPoolExecutor(max_workers=10) as pool: responses = list(pool.map(attempt,range(10)))
                successes = [r for r in responses if 200<=r[0]<300]
                assert len(successes)==1, f'One remaining seat: got {len(successes)} successes'
                for r in responses:
                    if r not in successes: self.rejected(r)
                assert self.sessions()['CT-101']['activeCount']==2
        elif name == 'AC05':
            first = self.record(self.reserve('K1')); before=self.sessions()
            assert self.record(self.reserve('K1',' Ada '))==first
            self.rejected(self.reserve('K1','Bob')); self.rejected(self.reserve('K1',session='CT-102'))
            assert self.sessions()==before
        elif name in ('AC06','AC07'):
            active=self.record(self.reserve('K1')); cancelled=self.record(self.reserve('K2','Bob'))
            path='/reservations/'+cancelled['reservationId']; cancellation=self.record(self.http('POST',path+'/cancel',{}))
            assert cancellation == cancelled | {'status':'cancelled'}
            before=self.sessions(); assert before['CT-101']['activeCount']==1
            assert self.record(self.http('POST',path+'/cancel',{}))==cancellation
            assert self.record(self.reserve('K2','Bob'))==cancellation
            assert self.sessions()==before
            if name=='AC07':
                self.stop(); self.start()
                assert self.record(self.http('GET','/reservations/'+active['reservationId']))==active
                assert self.record(self.http('GET',path))==cancellation
                assert self.sessions()==before
        elif name == 'AC08':
            baseline=self.sessions()
            probes=[lambda:self.reserve('K1',session='UNKNOWN'), lambda:self.reserve('K2','   '), lambda:self.http('POST','/reservations',{'sessionId':'CT-101','attendeeAlias':'Ada'}), lambda:self.http('POST','/reservations',raw=b'{broken'), lambda:self.http('POST','/reservations/not-a-real-id/cancel',{})]
            for probe in probes:
                self.rejected(probe()); assert self.sessions()==baseline

def execute(source, adapter, evidence, batches=10):
    source=Path(source).resolve(strict=True); evidence=Path(evidence).absolute()
    if evidence.resolve().is_relative_to(source): raise ValueError('Evidence must be outside app source')
    if not 1<=batches<=10: raise ValueError('Batches must be 1-10')
    config=validate_adapter(json.loads(Path(adapter).read_text()))
    validate_launch_commands(config, source)
    before=tree_hash(source)
    evidence.mkdir(exist_ok=False)
    run=Run(source,config,evidence); results={}
    try:
        for name in ('AC02','AC03','AC04','AC05','AC06','AC07','AC08'):
            try:
                run.challenge(name,batches); results[name]={'apiStatus':'PASS'}
            except Exception as exc:
                results[name]={'apiStatus':'FAIL','error':f'{type(exc).__name__}: {exc}'}
            finally: run.stop()
    finally:
        run.stop()
        try: after=tree_hash(source)
        except Exception as exc: after=f'ERROR: {exc}'
        report={'sourceIdBefore':before,'sourceIdAfter':after,'sourceUnchanged':before==after,'results':results,'AC01':'NOT RUN','manualChecks':'UI agreement AC02/03/07 and independent audit NOT RUN. No automatic points.','concurrency':{'batches':batches,'attemptsPerBatch':10},'receipts':run.receipts}
        (evidence/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path); p.add_argument('--adapter',required=True,type=Path)
    p.add_argument('--evidence',required=True,type=Path); p.add_argument('--batches',type=int,default=10,help='1-10 concurrent batches, each with ten attempts')
    args=p.parse_args()
    try:
        r=execute(args.source,args.adapter,args.evidence,args.batches)
        print(json.dumps({k:v for k,v in r.items() if k!='receipts'},indent=2))
        return 0 if len(r['results'])==7 and r['sourceUnchanged'] and all(x['apiStatus']=='PASS' for x in r['results'].values()) else 1
    except Exception as exc:
        p.exit(1,f'ERROR: {type(exc).__name__}: {exc}\n')

if __name__=='__main__':
    sys.exit(main())
