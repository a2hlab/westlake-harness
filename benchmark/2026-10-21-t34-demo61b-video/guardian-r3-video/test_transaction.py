#!/usr/bin/env python3
"""Execute derived transaction branches with fake reads and real local guard shells."""
import ast
import copy
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

D=Path(__file__).resolve().parent
sys.path.insert(0,str(D/'deployment'))
import derive
import prepare_data
MAIN=Path(os.environ.get('T34_MAIN',str(D.parents[2])))
S=(D/'deployment/executor61b.py').read_text();TREE=ast.parse(S)
sha=lambda b:hashlib.sha256(b).hexdigest()
sf=lambda p:sha(Path(p).read_bytes())
q=shlex.quote
RT=prepare_data.RT
SERIAL=prepare_data.SERIAL
META='644:20011206:20011206';LABEL='u:object_r:appdat:s0'
BOOT='12345678-1234-1234-1234-123456789abc'
BT=b'fixture exact original\nexport WL_PARENT_ID=30\n'
AT=b'fixture exact candidate\nexport WL_PARENT_ID=30\n'
FUNCS=[n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name in ('normalize_wid','pathguard','fg','swap','directory_guard')]
BLOCK=S[S.index('expected=sha(before)'):S.index('physical_guard=')]
BACKUP=next(n for n in TREE.body if isinstance(n,ast.If) and ast.unparse(n.test)=="a.mode == 'rollback'" and any(isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id=='backup' for y in x.targets) for x in n.body))
HOST=next(n for n in TREE.body if isinstance(n,ast.If) and ast.unparse(n.test)=="not a.recovery_no_parent" and any(isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id=='host' for y in x.targets) for x in n.body))
SCRIPT=S[S.index('script=pre'):S.index("(a.out/'swap.sh')")]
COUNTS={'known_states':0,'cutpoints':0,'foreign_states':0,'local_shell_cases':0}

class Checks(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory(prefix='t34-offline-');self.addCleanup(self.tmp.cleanup)
    self.root=Path(self.tmp.name).resolve();self.ap=self.root/'plan.json'
 def env(self,bits=(1,1,1,1,1,1),missing=None,no_parent=True):
    p=json.loads((MAIN/'benchmark/2026-10-20-t31-demo-retain/fixtures/historical-t30-plan.json').read_text())
    holder='inner(cc-video) 12345 2026-10-21T01:00:00+08:00'
    p.update(executor_sha256=sf(D/'deployment/executor61b.py'),holder=holder,start=1792515600,
             boot=BOOT,serial=SERIAL,uid=20011206,wid='30',deployment_scope='T34_61B_VIDEO',
             before_sha=sha(BT),after_sha=sha(AT),cfg_sha=prepare_data.CFG,
             parameters_sha256='e'*64,run_metadata='755:20011206:20011206',
             media_metadata=META,player_metadata=META,bridge_metadata=META,shim_metadata='755:20011206:20011206')
    p['compat_absence_marker']=RT+'/libopensles_android_compat.so.t34-61b-before-'+BOOT[:8]+'.absent'
    dirs={path:'66352:'+str(i+200) for i,path in enumerate((RT,RT+'/lib',RT+'/lib/arm64-v8a',RT+'/webview-t-lib'))}
    p['directory_identities']=dirs
    p['bridge_candidate_sha256']=sf(D/'deployment/bridge-candidate.json');p['shim_candidate_sha256']=sf(D/'deployment/shim-candidate.json')
    self.ap.write_text(json.dumps(p))
    def sha_file(path):
        if Path(path).name=='parameters.json':return 'e'*64
        return sf(path)
    ad={'directory_identities':dirs,'protected_directories':{'/system/lib64':'10:11','/data/local/tmp/asx':None,'/data/local/tmp/asx/lib':None,'/data/local/tmp/asx/lib/arm64-v8a':None,'/data/local/tmp/asx/webview-t-lib':None},
        'recovery_wid':30,'recovery_run_sha256':sha(AT if bits[0] else BT)}
    e=dict(sha=sha,sha_file=sha_file,q=q,re=re,json=json,Path=Path,REFERENCE_WID=30,__file__=str(D/'deployment/executor61b.py'))
    e.update(a=SimpleNamespace(mode='rollback',apply_plan=self.ap,boot='87654321-1234-1234-1234-123456789abc',parent=None,birth=None,holder=holder,start=p['start'],out=self.root/'out',recovery_no_parent=no_parent),
             here=D/'deployment',ad=ad,before=BT,after=AT,before_template=BT,after_template=AT,wid='30',
             current_wid=30,normalized=AT if bits[0] else BT,actual=sha(AT if bits[0] else BT),
             meta=p['run_metadata'],label=LABEL,dlabel=LABEL,MEDIA='lib/arm64-v8a/libmffmpeg.so',
             PLAYER=p['player_path'],BRIDGE=p['bridge_path'],SHIM=p['shim_path'],SHIM_INPUT='libwebview_bionic_shim.so',DSO='libopensles_android_compat.so',
             DSHA=p['dso_sha'],CSHA=prepare_data.CFG,RT=RT,pre='',parent_guard='',stage='/data/local/tmp/t34-offline',new=BT)
    for role,short,idx in [('media','m',1),('player','p',2),('bridge','b',3),('shim','s',4)]:
        cap={'media':'M','player':'P','bridge':'B','shim':'S'}[role]
        e[cap+'BEFORE']=p[role+'_before_sha'];e[cap+'AFTER']=p[role+'_after_sha']
        e[short+'actual']=p[role+('_after_sha' if bits[idx] else '_before_sha')]
        e[short+'meta']=p[role+'_metadata'];e[short+'label']=LABEL
    def read(cmd):
        if '.t34-61b-before-' in cmd:return 'no' if missing and missing in cmd else 'yes'
        return 'yes' if bits[5] else 'no'
    e['read']=read
    for f in FUNCS:exec(compile(ast.Module(body=[f],type_ignores=[]),'actual-derived-functions','exec'),e)
    return e
 def transaction(self,e):
    exec(BLOCK,e);exec(compile(ast.Module(body=[BACKUP],type_ignores=[]),'actual-backup-block','exec'),e);exec(SCRIPT,e)
    return e['script']
 def test_reproducible_derivation(self):
    old=(MAIN/derive.ORIGIN/'executor.py').read_text()
    self.assertEqual(derive.derive(old),S)
    for bad in ('20011300','restore-v1-5cd','t21-5cd',"'29'",'5cd1e3dd'):
        self.assertNotIn(bad,S)
 def test_cli_preview_and_preapproval_refusal(self):
    for mode in ('preflight','apply','rollback'):
        r=subprocess.run([sys.executable,str(D/'deployment/executor61b.py'),mode],capture_output=True)
        self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['device_calls'],0)
    for args in (['apply','--execute'],['apply','--recovery-no-parent'],['rollback','--execute']):
        r=subprocess.run([sys.executable,str(D/'deployment/executor61b.py'),*args],capture_output=True)
        self.assertNotEqual(r.returncode,0);self.assertNotIn(b'bms_batch',r.stderr)
 def test_all_64_actual_rollback_branches(self):
    for bits in itertools.product((0,1),repeat=6):
        e=self.env(bits);self.transaction(e);COUNTS['known_states']+=1
 def test_six_cuts_backups_before_swap_and_exact_cas(self):
    bits=[1]*6
    for cut,idx in enumerate((4,3,1,2,0,5)):
        e=self.env(tuple(bits));s=self.transaction(e)
        first=min(x for x in (s.find('\nmv '),s.find('\nrm ')) if x>=0)
        for key in ('backup','media_backup','player_backup','bridge_backup','shim_backup'):
            self.assertIn(e[key],s[:first])
        self.assertIn(sha(b'ABSENT\n'),s[:first])
        for path,pre,meta in [(e['SHIM'],e['sactual'],e['smeta']),(e['BRIDGE'],e['bactual'],e['bmeta']),
                             (e['MEDIA'],e['mactual'],e['mmeta']),(e['PLAYER'],e['pactual'],e['pmeta']),('run.sh',e['actual'],e['meta'])]:
            dst=RT+'/'+path;tmp=dst+'.ttvideo-'+e['a'].boot[:8]+'-'+sha(str(e['a'].out).encode())[:8]+'.tmp'
            if '\nmv '+q(tmp) in s:self.assertIn(e['fg'](dst,pre,meta,LABEL)+'mv '+q(tmp)+' '+q(dst)+'\n',s)
        bits[idx]=0;COUNTS['cutpoints']+=1
 def test_apply_all_five_backups_absent_before_first_swap(self):
    e=self.env((0,0,0,0,0,0));e['a'].mode='apply';e['plan']=json.loads(self.ap.read_text());e['new']=AT
    exec(BLOCK,e);exec(SCRIPT,e);s=e['script'];first=s.index('\nmv ')
    for key in ('backup','media_backup','player_backup','bridge_backup','shim_backup'):
        self.assertIn('cp -p ',s[:first]);self.assertIn(e[key],s[:first])
    self.assertIn('ABSENT\\n',s[:first]);self.assertIn(sha(b'ABSENT\n'),s[:first])
 def test_foreign_and_any_missing_backup_rejected(self):
    for key in ('actual','mactual','pactual','bactual','sactual'):
        e=self.env();e[key]='a'*64
        with self.assertRaises(AssertionError):self.transaction(e)
        COUNTS['foreign_states']+=1
    for missing in ('run.sh','libmffmpeg.so','libttmplayer.so','liboh_adapter_bridge.so','libwebview_bionic_shim.so'):
        e=self.env((0,0,0,0,1,0),missing=missing)
        with self.assertRaises(AssertionError):self.transaction(e)
 def test_no_parent_host_required_physical_branch(self):
    e=self.env();self.assertNotIn('host',e['ad'])
    exec(compile(ast.Module(body=[HOST],type_ignores=[]),'actual-host-branch','exec'),e)
    self.transaction(e)
    e=self.env(no_parent=False)
    with self.assertRaises(KeyError):exec(compile(ast.Module(body=[HOST],type_ignores=[]),'actual-host-branch','exec'),e)
 def test_fresh_recovery_wid_exact_and_other_bytes_rejected(self):
    e=self.env();e['current_wid']=31;e['ad']['recovery_wid']=31
    e['actual']=sha(AT.replace(b'=30\n',b'=31\n'));e['ad']['recovery_run_sha256']=e['actual']
    self.transaction(e)
    for key,value in [('recovery_wid',32),('recovery_run_sha256','a'*64)]:
        bad=self.env();bad['ad'][key]=value
        with self.assertRaises(AssertionError):self.transaction(bad)
    e=self.env();e['normalized']=AT+b'foreign'
    with self.assertRaises(AssertionError):self.transaction(e)
 def test_directory_alias_reject(self):
    e=self.env();self.assertIn('stat -L',e['directory_guard']())
    e['ad']['protected_directories']['/data/local/tmp/asx']=e['ad']['directory_identities'][RT]
    with self.assertRaises(AssertionError):e['directory_guard']()
    e=self.env();e['ad']['directory_identities'][RT+'/lib']=e['ad']['directory_identities'][RT]
    with self.assertRaises(AssertionError):e['directory_guard']()
 def test_actual_local_guard_bytes_metadata_symlink(self):
    e=self.env();f=self.root/'backup';payload=b'original\n';digest=sha(payload)
    prefix='stat() { printf "%s\\n" "$TEST_META"; }; ls() { printf "%s local\\n" "$TEST_LABEL"; };\n'
    for value,meta,label,ok in [(payload,META,LABEL,True),(b'foreign',META,LABEL,False),(payload,'644:0:0',LABEL,False),(payload,META,'wrong',False)]:
        f.write_bytes(value)
        r=subprocess.run(['bash','-eu','-c',prefix+e['fg'](str(f),digest,META,LABEL)],env=dict(os.environ,TEST_META=meta,TEST_LABEL=label),capture_output=True)
        self.assertEqual(r.returncode==0,ok);COUNTS['local_shell_cases']+=1
    link=self.root/'alias';link.symlink_to(f)
    r=subprocess.run(['bash','-eu','-c',e['pathguard'](str(link))],capture_output=True)
    self.assertNotEqual(r.returncode,0);COUNTS['local_shell_cases']+=1
 def test_atomic_rename_preserves_shared_old_inode(self):
    e=self.env();e['RT']=str(self.root);e['directory_guard']=lambda:''
    target=self.root/'target';alias=self.root/'old-shared-link';source=self.root/'candidate'
    target.write_bytes(b'before');os.link(target,alias);source.write_bytes(b'after')
    oldino=target.stat().st_ino
    # Ownership/SELinux calls are mocked for a non-root host; cp/mv/hash/files are real.
    prefix=f'''stat() {{ printf "%s\\n" "{META}"; }}; ls() {{ printf "%s local\\n" "{LABEL}"; }};
chown() {{ :; }}; chmod() {{ :; }}; chcon() {{ :; }};
'''
    script=e['swap']('target',str(source),sha(b'after'),META,LABEL,sha(b'before'))
    r=subprocess.run(['bash','-eu','-c',prefix+script],capture_output=True)
    self.assertEqual(r.returncode,0,r.stderr)
    self.assertEqual(alias.read_bytes(),b'before');self.assertEqual(alias.stat().st_ino,oldino)
    self.assertEqual(target.read_bytes(),b'after');self.assertNotEqual(target.stat().st_ino,oldino)
    COUNTS['local_shell_cases']+=1

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'success':r.wasSuccessful(),'tests':r.testsRun,'counts':COUNTS,'device_calls':0,
                      'limits':'Actual derived Python branches and local bash guards. No HDC. Full remote transaction remains unexecuted.'}))
    raise SystemExit(not r.wasSuccessful())
