"""Helper tests. The HTTP fixture is deliberately incomplete, not a solution."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import snapshot
import score
import verify
import preflight

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.source=self.root/'app'; self.source.mkdir()
        (self.source/'app.py').write_text('print("hello")\n')
        self.archive=self.root/'source.zip'

    def test_exclusions_deterministic_identity_and_safe_extract(self):
        for name in ('.env','.env.production','nagual.db','app.sqlite3','trace.log','foo.db-wal'):
            (self.source/name).write_text('private')
        for name in ('.git','node_modules','evidence','data'):
            folder=self.source/name; folder.mkdir(); (folder/'secret.txt').write_text('private')
        (self.source/'.env.example').write_text('PORT=3000')
        first=snapshot.create(self.source,self.archive)
        second=snapshot.create(self.source,self.root/'second.zip')
        self.assertEqual(first['sourceId'],second['sourceId'])
        self.assertEqual(first['artifactSha256'],second['artifactSha256'])
        destination=self.root/'clean'; snapshot.extract(self.archive,destination)
        self.assertEqual(sorted(x.name for x in destination.iterdir()),['.env.example','app.py'])
        with self.assertRaises(FileExistsError): snapshot.extract(self.archive,destination)
        self.assertEqual(snapshot.tree_hash(destination),first['sourceId'])

    def test_refuses_source_symlink(self):
        (self.source/'escape').symlink_to(self.root,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Symlink'): snapshot.create(self.source,self.archive)

    def test_refuses_archive_inside_source(self):
        with self.assertRaises(ValueError): snapshot.create(self.source,self.source/'out.zip')

    def test_refuses_path_attacks_and_symlinks(self):
        for i,name in enumerate(('../escape','/tmp/escape','a/../../escape','a\\escape','C:escape','a//b')):
            path=self.root/f'attack{i}.zip'
            with zipfile.ZipFile(path,'w') as z: z.writestr(name,b'bad')
            with self.assertRaises(ValueError): snapshot.extract(path,self.root/f'out{i}')
            self.assertFalse((self.root/f'out{i}').exists())
        path=self.root/'link.zip'
        with zipfile.ZipFile(path,'w') as z:
            info=zipfile.ZipInfo('link'); info.external_attr=0o120777<<16; z.writestr(info,'/tmp')
        with self.assertRaises(ValueError): snapshot.check(path)

    def test_refuses_tampered_content(self):
        snapshot.create(self.source,self.archive)
        tamper=self.root/'tamper.zip'
        with zipfile.ZipFile(self.archive) as src, zipfile.ZipFile(tamper,'w') as dst:
            for name in src.namelist(): dst.writestr(name,b'changed' if name=='app.py' else src.read(name))
        with self.assertRaisesRegex(ValueError,'mismatch'): snapshot.check(tamper)
    def test_refuses_missing_manifest(self):
        with zipfile.ZipFile(self.archive,'w') as z: z.writestr('app.py','print("no manifest")')
        with self.assertRaisesRegex(ValueError,'Missing snapshot manifest'): snapshot.check(self.archive)

class ScoreTests(unittest.TestCase):
    def setUp(self): self.data=json.loads((Path(score.__file__).parent/'example-score.json').read_text())
    def test_unscored_is_zero(self): self.assertEqual(score.validate(self.data)['total'],0)
    def test_rejects_missing_rows_points_and_unsupported_pass(self):
        invalid=[]
        d=copy.deepcopy(self.data); del d['rows']['A8']; invalid.append(d)
        for points in (True,1,10):
            d=copy.deepcopy(self.data); d['rows']['A1']['points']=points; invalid.append(d)
        d=copy.deepcopy(self.data); d['rows']['A1']['points']=5; invalid.append(d)
        d=copy.deepcopy(self.data); d['rows']['A1'].update(points=5,status='PASS',evidence='receipt'); invalid.append(d)
        for data in invalid:
            with self.assertRaises(ValueError): score.validate(data)
    def test_human_credits_and_independence_required(self):
        for row in self.data['rows'].values(): row.update(points=5,status='PASS',evidence='receipt',adjudicator='Judge')
        with self.assertRaisesRegex(ValueError,'independent'): score.validate(self.data)
        self.data['independentAuditTeam']='Team B'
        self.data['independentAuditTeamType']='human'
        result=score.validate(self.data)
        self.assertEqual(result['categories'],{'A':40,'B':30,'C':20,'D':10}); self.assertEqual(result['total'],100)
    def test_rehearsal_ai_is_declared_and_never_event_qualification(self):
        row=self.data['rows']['C1']; row.update(points=5,status='PASS',evidence='AI receipt',adjudicator='AI reviewer',adjudicatorType='ai')
        self.data.update(independentAuditTeam='AI audit lane',independentAuditTeamType='ai')
        with self.assertRaises(ValueError): score.validate(self.data)
        self.data['mode']='rehearsal'
        result=score.validate(self.data)
        self.assertEqual(result['total'],5)
        self.assertIn('REHEARSAL ONLY',result['notice'])
    def test_missing_mode_or_adjudicator_type_rejected(self):
        data=copy.deepcopy(self.data); del data['mode']
        with self.assertRaises(ValueError): score.validate(data)
        row=self.data['rows']['A1']; row.update(points=5,status='PASS',evidence='receipt',adjudicator='Named')
        del row['adjudicatorType']
        with self.assertRaises(ValueError): score.validate(self.data)

INCOMPLETE = '''import json, os
from http.server import HTTPServer, BaseHTTPRequestHandler
assert 'ATD_TEST_PRIVATE_API_TOKEN' not in os.environ, 'Private parent environment leaked'
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200); self.end_headers(); self.wfile.write(json.dumps({"sessions":[{"id":"CT-101","capacity":2,"activeCount":0,"remainingSeats":2},{"id":"CT-102","capacity":3,"activeCount":0,"remainingSeats":3}]}).encode())
 def do_POST(self):
  self.send_response(200); self.end_headers(); self.wfile.write(b'{"error":"pretend success"}')
if __name__=="__main__": HTTPServer(("127.0.0.1",int(os.environ["PORT"])),Handler).serve_forever()
'''

class VerificationNegativeControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.source=self.root/'app'; self.source.mkdir()
        (self.source/'app.py').write_text(INCOMPLETE)
        self.adapter=self.root/'adapter.json'
        self.config={'start':['{python}','app.py'],'reset':['{python}','-c','pass']}
        self.adapter.write_text(json.dumps(self.config))
    def diagnostics(self, report, evidence):
        logs='\n'.join(f'{path.name}:\n{path.read_text(errors="replace")}' for path in sorted(evidence.glob('process-*.log')))
        return json.dumps(report['results'],indent=2)+'\n'+logs
    def test_incomplete_fixture_never_succeeds_and_keeps_raw_receipts(self):
        report=verify.execute(self.source,self.adapter,self.root/'receipts',batches=1)
        self.assertEqual(report['results']['AC02']['apiStatus'],'PASS',self.diagnostics(report,self.root/'receipts'))
        self.assertEqual(report['AC01'],'NOT RUN')
        for name in ('AC03','AC04','AC05','AC06','AC07','AC08'):
            self.assertEqual(report['results'][name]['apiStatus'],'FAIL',name)
        self.assertTrue(report['sourceUnchanged'])
        self.assertTrue(any(r['kind']=='stop' and 'exitCode' in r for r in report['receipts']))
        self.assertTrue(any(r['kind']=='http' and r['status']==200 and 'pretend success' in r['response'] for r in report['receipts']))
        result=subprocess.run([sys.executable,str(Path(verify.__file__)),'--source',str(self.source),'--adapter',str(self.adapter),'--evidence',str(self.root/'cli-receipts'),'--batches','1'],capture_output=True)
        self.assertEqual(result.returncode,1)
    def test_failed_reset_is_not_success(self):
        self.config['reset']=['{python}','-c','raise SystemExit(9)']; self.adapter.write_text(json.dumps(self.config))
        report=verify.execute(self.source,self.adapter,self.root/'receipts',batches=1)
        self.assertTrue(all(x['apiStatus']=='FAIL' for x in report['results'].values()))
        self.assertTrue(all(r['exitCode']==9 for r in report['receipts'] if r['kind']=='reset'))
    def test_existing_or_internal_evidence_path_is_refused(self):
        with self.assertRaises(ValueError): verify.execute(self.source,self.adapter,self.source/'evidence')
        with self.assertRaises(FileExistsError): verify.execute(self.source,self.adapter,self.root)
    def test_adapter_rejected_before_running(self):
        for config in (None,{}, {'start':'python app.py','reset':['x']}, {'start':['x'],'reset':['x'],'fields':{'status':None}}, {'start':['x'],'reset':['x'],'fields':{'unknown':'x'}}, {'start':['x'],'reset':['x'],'fields':{'status':'a..b'}}):
            with self.assertRaises(ValueError): verify.validate_adapter(config)
        self.assertEqual(verify.validate_adapter(self.config),self.config)
    def test_preflight_reports_runtime_not_app_pass(self):
        result=preflight.check()
        self.assertEqual(result['appStatus'],'NOT RUN')
        self.assertEqual(result['runtimePath'],sys.executable)
        self.assertTrue(result['sqliteAvailable'])
        self.assertTrue(result['loopbackAvailable'])
    def test_rejects_direct_source_commands_before_evidence_or_launch(self):
        for first in ('./start.sh','path/run','.\\start.ps1',str(self.source/'app.py'),'app.py'):
            for name in ('start','reset'):
                config=copy.deepcopy(self.config); config[name]=[first]
                self.adapter.write_text(json.dumps(config))
                evidence=self.root/'must-not-be-created'
                with self.assertRaisesRegex(ValueError,'source executable'):
                    verify.execute(self.source,self.adapter,evidence,1)
                self.assertFalse(evidence.exists())
        verify.validate_launch_commands({'start':[sys.executable,'app.py'],'reset':[sys.executable,'-c','pass']},self.source)
    def test_rejects_source_runtime_hidden_in_path(self):
        runtime_name='fake-runtime.exe' if os.name=='nt' else 'fake-runtime'
        folder=self.source/'bin';folder.mkdir(); runtime=folder/runtime_name
        runtime.write_text('#!/bin/sh\n');runtime.chmod(0o755)
        with patch.dict(os.environ,{'PATH':str(folder)+os.pathsep+os.environ.get('PATH','')}):
            with self.assertRaisesRegex(ValueError,'PATH resolves'):
                verify.validate_launch_commands({'start':[runtime_name,'app.py'],'reset':[sys.executable,'-c','pass']},self.source)
    def test_interpreter_launch_survives_cold_copy_and_private_env_is_removed(self):
        script=self.source/'app.py'; script.chmod(0o755)
        archive=self.root/'source.zip'; original=snapshot.create(self.source,archive)
        cold=self.root/'cold';snapshot.extract(archive,cold)
        if os.name=='nt':
            # Windows chmod exposes the read-only attribute, not POSIX execute bits.
            self.assertTrue(os.access(cold/'app.py',os.W_OK))
            with zipfile.ZipFile(archive) as z:
                self.assertEqual((z.getinfo('app.py').external_attr>>16)&0o777,0o644)
        else:
            self.assertEqual((cold/'app.py').stat().st_mode & 0o777,0o644)
        with patch.dict(os.environ,{'ATD_TEST_PRIVATE_API_TOKEN':'fictional-negative-control'}):
            report=verify.execute(cold,self.adapter,self.root/'cold-receipts',1)
        self.assertEqual(report['sourceIdBefore'],original['sourceId'])
        self.assertEqual(report['results']['AC02']['apiStatus'],'PASS',self.diagnostics(report,self.root/'cold-receipts'))
        self.assertEqual(report['results']['AC03']['apiStatus'],'FAIL')
        self.assertTrue(report['sourceUnchanged'])
    def test_runtime_environment_allowlist_drops_secret(self):
        with patch.dict(os.environ,{'ATD_TEST_PRIVATE_API_TOKEN':'fake','PATH':'runtime-path','HOME':'runtime-home'}):
            env=verify.runtime_environment(43210,self.root/'new-state')
        self.assertNotIn('ATD_TEST_PRIVATE_API_TOKEN',env)
        self.assertEqual(env['PATH'],'runtime-path');self.assertEqual(env['HOME'],'runtime-home')
        self.assertEqual(env['PORT'],'43210');self.assertEqual(env['DATA_DIR'],str(self.root/'new-state'))
    def test_readiness_failure_records_last_network_error_or_http_status(self):
        # Exercise a real readiness iteration without waiting ten wall-clock seconds.
        for index,probe in enumerate((urllib.error.URLError('diagnostic connection refusal'),(503,{'error':'warming'}))):
            evidence=self.root/f'diagnostic-{index}'; evidence.mkdir()
            run=verify.Run(self.source,self.config,evidence)
            run.scenario='AC02'; run.port=12345; run.state=self.root/'unused-state'; run.env={}
            child=Mock(pid=123); child.poll.return_value=None
            try:
                with patch.object(verify.subprocess,'Popen',return_value=child), patch.object(verify.time,'monotonic',side_effect=[0,0,11]), patch.object(verify.time,'sleep'), patch.object(run,'http',side_effect=probe if isinstance(probe,Exception) else None,return_value=probe):
                    with self.assertRaisesRegex(AssertionError,'Readiness timed out; lastProbe=') as raised:
                        run.start()
                receipt=next(r for r in run.receipts if r['kind']=='readinessFailure')
                if index==0:
                    self.assertIn('diagnostic connection refusal',receipt['lastException'])
                    self.assertIn('diagnostic connection refusal',str(raised.exception))
                else:
                    self.assertEqual(receipt['lastHttpStatus'],503)
                    self.assertIn('503',str(raised.exception))
            finally:
                if run.log: run.log.close()

if __name__=='__main__': unittest.main()
