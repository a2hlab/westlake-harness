#!/usr/bin/env python3
"""Synthetic same-shape positives plus the actual117/10/1 negative; no device calls."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'scripts/lab/lab_paths.py').is_file())
os.environ.setdefault('WORKSPACES', str(ROOT.parent))
WS = Path(os.environ['WORKSPACES']); MAIN = WS / 'westlake-harness'
spec = importlib.util.spec_from_file_location('index_compiler', HERE / 'compile_index.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
MANIFEST = MAIN / 'benchmark/2026-10-09-demo-baseline/demo-manifest.json'
INITIAL = MAIN / 'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/smoke10-r4b/install-preflight/apk-identity.json'
BOOT = '35da6f13-e7b1-4472-a36a-5c4a69d5f191'


class CompileIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='actual-apk-index-')
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name); self.out = self.dir / 'out'; self.n = 0
        self.apps = [a for a in c.read(MANIFEST)['apps'] if a.get('install') is not False]
        self.initial = c.read(INITIAL)
        self.assertEqual(self.initial['summary'], {'MATCH':117,'MISSING':10,'DRIFT':1})
        allbundles = 'ID: 100:\n' + '\n'.join(a['package'] for a in self.apps) + '\n'
        finaldoc = json.loads(json.dumps(self.initial))
        for r in finaldoc['rows']: r.update(actual=r['expected'], status='MATCH')
        finaldoc['summary'] = {'MATCH':128}
        raw = ''.join(a['apk_sha256'] + '  /data/app/el1/bundle/public/' + a['package'] + '/android/base.apk\n' for a in self.apps)
        self.req = {'schema':'verified-installed-identity-request/v1','serial':c.SERIAL,'boot_id':BOOT,
            'manifest':self.pin(MANIFEST), 'initial':{'identity':self.pin(INITIAL),
            'bundles':self.reading('bm dump -a',allbundles,1)},
            'final':{'identity':self.doc('final-identity.json',finaldoc),
                'boot_before':self.reading('cat /proc/sys/kernel/random/boot_id',BOOT,10),
                'boot_after':self.reading('cat /proc/sys/kernel/random/boot_id',BOOT,20),
                'bundles':self.reading('bm dump -a',allbundles,12),
                'apk_reads':[self.reading('sha256sum /data/app/el1/bundle/public/*/android/base.apk',raw,14)]},
            'installations':[]}
        for row in self.initial['rows']:
            if row['status']=='MATCH': continue
            output=self.dir/(row['key']+'.install.txt');output.write_text('install bundle successfully.')
            record={'key':row['key'],'package':row['package'],'serial':c.SERIAL,
                'status':'installed','install_only':True,'apk_sha256':row['expected'],
                'install':{'return_code':0,'success_text':True,'output':str(output)},
                'bms':{'queryable':True},'finished_at':6,'synthetic':True}
            self.req['installations'].append({'key':row['key'],'record':self.doc(row['key']+'.json',record),
                'output':self.pin(output), 'boot_before':self.reading('cat /proc/sys/kernel/random/boot_id',BOOT,3),
                'install_command':self.reading('bm install -r -p original.apk','install bundle successfully.',4),
                'boot_after':self.reading('cat /proc/sys/kernel/random/boot_id',BOOT,5)})

    def pin(self,p): return {'path':str(p),'sha256':c.digest(p)}
    def doc(self,name,doc):
        p=self.dir/name;c.save(p,doc);return self.pin(p)
    def reading(self,cmd,text,t):
        self.n+=1;stem='read-'+str(self.n)
        p=self.dir/(stem+'.stdout');p.write_text(text)
        e=self.dir/(stem+'.stderr');e.write_text('')
        return {'receipt':self.doc(stem+'.json',{'argv':['hdc','-t',c.SERIAL,'shell',cmd],'rc':0,'time':t}),
                'stdout':self.pin(p),'stderr':self.pin(e)}
    def change_doc(self,pin,fn):
        p=Path(pin['path']);obj=c.read(p);fn(obj);c.save(p,obj);pin['sha256']=c.digest(p)
    def run_compile(self):
        p=self.dir/'request.json';c.save(p,self.req);return c.compile_index(p,self.out)
    def reject(self,match):
        with self.assertRaisesRegex(ValueError,match): self.run_compile()
        self.assertFalse(self.out.exists())

    def test_actual_initial_117_10_1_cannot_be_final(self):
        self.req['final']['identity']=self.pin(INITIAL)
        self.reject('final missing/drift/unknown')

    def test_synthetic_full128_preserves_driver_interface(self):
        index=self.run_compile()
        self.assertEqual(len(index),128)
        self.assertEqual(sum(r['basis']=='existing-installation-observed' for r in index.values()),117)
        self.assertEqual(sum(r['basis']=='new-installation' for r in index.values()),10)
        self.assertEqual(sum(r['basis']=='upgraded-installation' for r in index.values()),1)
        for row in index.values():
            self.assertIs(row['success'],True);self.assertEqual(row['serial'],c.SERIAL)
            self.assertEqual(c.digest(row['record']),row['record_sha256'])
        dspec=importlib.util.spec_from_file_location('full128_driver',HERE.parent/'fresh128-handoff-r2/run_candidate_post_reboot.py')
        d=importlib.util.module_from_spec(dspec);dspec.loader.exec_module(d)
        proof=MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/identity-table-correction/compiled'
        with contextlib.redirect_stdout(io.StringIO()):
            config=d.prepare(MANIFEST,d.HERE/'shot-tiers.json',self.out/'install-index.json',self.dir/'driver-preview',
                'd0e1f5eb-ac35-4c39-9e1a-7c40d9251220',proof/'smoke.json',serial=c.SERIAL,
                candidate_proof=proof/'candidate-proof.json',candidate_sha='d8f13bf33e431bc8821e4e29c573161c41d1527e276828b8e725efad3e959b22')
        self.assertEqual(config['apps'],128);self.assertFalse(config['execution_enabled'])

    def test_raw_drift_despite_match_summary(self):
        raw=self.req['final']['apk_reads'][0]['stdout'];p=Path(raw['path'])
        p.write_text(p.read_text().replace(self.apps[0]['apk_sha256'],'0'*64));raw['sha256']=c.digest(p)
        self.reject('raw APK inventory differs')
    def test_missing_install_record(self):
        self.req['installations'].pop();self.reject('changed-key installation')
    def test_foreign_61b_record(self):
        self.change_doc(self.req['installations'][0]['record'],lambda d:d.update(serial='61b0657200000000000000000324012c'))
        self.reject('foreign/stale')
    def test_changed_boot(self):
        b=self.req['final']['boot_after']['stdout'];p=Path(b['path']);p.write_text('d0e1f5eb-ac35-4c39-9e1a-7c40d9251220');b['sha256']=c.digest(p)
        self.reject('boot mismatch')
    def test_bms_missing(self):
        b=self.req['final']['bundles']['stdout'];p=Path(b['path']);p.write_text('ID: 100:\norg.westlake.imehost\n');b['sha256']=c.digest(p)
        self.reject('BMS missing')
    def test_input_pin_drift(self):
        p=Path(self.req['final']['identity']['path']);p.write_text(p.read_text()+' ');self.reject('input SHA drift')
    def test_transport_rc0_error_is_not_absence(self):
        b=self.req['final']['apk_reads'][0]['stderr'];p=Path(b['path']);p.write_text('Connect server failed');b['sha256']=c.digest(p)
        self.reject('transport/command error')
    def test_final_must_follow_new_installs(self):
        self.change_doc(self.req['installations'][0]['record'],lambda d:d.update(finished_at=11))
        self.reject('between preflight and final')
    def test_missing_128_member(self):
        self.change_doc(self.req['final']['identity'],lambda d:d['rows'].pop());self.reject('unique128')
    def test_actual_bms_marker_required(self):
        b=self.req['installations'][0]['boot_before']['receipt']
        self.change_doc(b,lambda d:d['argv'].__setitem__(-1,d['argv'][-1]+'; printf __BMS_REMOTE_RC_1234__0'))
        self.reject('missing/failed remote rc marker')


if __name__=='__main__': unittest.main(verbosity=2)
