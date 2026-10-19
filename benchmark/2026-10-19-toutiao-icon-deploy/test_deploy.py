import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import deploy
import prepare
BOOT='6944c37e-31a6-4846-8f1f-48088a917153'
ROOT='/data/westlake-demo/toutiao/recovery-attempts/icon-manual-fixture'

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=HERE,prefix='fixture-');self.addCleanup(self.tmp.cleanup)
        self.d=Path(self.tmp.name).resolve();src=self.d/'src';src.mkdir();self.src=src
        for name in ('boot-entry.sh','entry.sh','watchdog.sh'):(src/name).write_text('#!/system/bin/sh\nexit 0\n')
        (src/'config-common.sh').write_text('ROOT='+ROOT+'\n')
        names=['entry.sh','watchdog.sh','config-common.sh']
        (src/'members.tsv').write_text(''.join(deploy.sha(src/n)+' '+n+' 550\n' for n in names))
        (src/'startup.env').write_text("STARTUP_APPROVED_BY='outer(codex)'\nSTARTUP_ENABLED='1'\nSTARTUP_SERIAL='"+deploy.SERIAL+"'\nSTARTUP_MEMBERS_SHA='"+deploy.sha(src/'members.tsv')+"'\n")
        (src/'startup.expected.sha256').write_text(deploy.sha(src/'startup.env')+'\n')
        before=self.d/'original.cfg';before.write_text(json.dumps({'jobs':[{'condition':'ready'}],'services':[{'name':'fixture','path':['/system/bin/sh',deploy.OLD_ROOT+'/boot-entry.sh'],'permission':['DUMP','CAPTURE_SCREEN']}]}))
        self.pkg=self.d/'pkg';self.plan=prepare.prepare(src,before,BOOT,self.pkg)
    def test_precise_cfg_change_and_original_rollback(self):
        deploy.validate(self.plan,self.pkg)
        a=json.loads((self.pkg/'before.cfg').read_text());b=json.loads((self.pkg/'after.cfg').read_text())
        a['services'][0]['path'][1]=ROOT+'/boot-entry.sh';self.assertEqual(a,b)
        s=deploy.cfg_script(self.plan,True)
        self.assertIn(ROOT+'/before.cfg',s);self.assertNotIn('rollback-inert',s)
    def test_bad_scope(self):
        for key,value in [('serial','5cd'),('root',deploy.OLD_ROOT),('cfg','/system/etc/other.cfg')]:
            p=copy.deepcopy(self.plan);p[key]=value
            with self.assertRaises(ValueError):deploy.validate(p,self.pkg)
    def test_file_drift(self):
        (self.pkg/'payload/watchdog.sh').write_text('changed')
        with self.assertRaises(ValueError):deploy.validate(self.plan,self.pkg)
    def test_parent_symlink_rejected(self):
        (self.pkg/'payload').rename(self.d/'outside');(self.pkg/'payload').symlink_to(self.d/'outside',target_is_directory=True)
        with self.assertRaises(ValueError):deploy.validate(self.plan,self.pkg)
    def test_cfg_symlink_rejected(self):
        (self.pkg/'before.cfg').rename(self.d/'outside.cfg');(self.pkg/'before.cfg').symlink_to(self.d/'outside.cfg')
        with self.assertRaises(ValueError):deploy.validate(self.plan,self.pkg)
    def test_permission_change_rejected(self):
        p=copy.deepcopy(self.plan);b=json.loads((self.pkg/'after.cfg').read_text());b['services'][0]['permission']=[]
        (self.pkg/'after.cfg').write_text(json.dumps(b));p['after_sha256']=deploy.sha(self.pkg/'after.cfg')
        with self.assertRaises(ValueError):deploy.validate(p,self.pkg)
    def test_remote_guard_failure_propagates(self):
        class Fake(deploy.Device):
            def run(self,args):
                return subprocess.run(['sh','-c',args[1]],text=True,capture_output=True).stdout
        with self.assertRaises(ValueError):Fake(self.d).shell('false\nprintf SHOULD_NOT_RUN')
    def test_rollback_requires_original_transaction(self):
        with patch.object(deploy.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='outer(codex) 1')):
            with self.assertRaisesRegex(ValueError,'transaction receipt'):
                deploy.execute(self.plan,self.pkg,self.d/'rollback',True,BOOT,'a'*64)
        self.assertFalse((self.d/'rollback').exists())
    def test_rollback_rejects_changed_plan_receipt(self):
        receipt=self.d/'receipt.json';receipt.write_text('{}')
        with patch.object(deploy.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='outer(codex) 1')):
            with self.assertRaisesRegex(ValueError,'binding differs'):
                deploy.execute(self.plan,self.pkg,self.d/'rollback',True,BOOT,'a'*64,receipt)
        self.assertFalse((self.d/'rollback').exists())
    def test_missing_lock_refuses_before_output(self):
        with patch.object(deploy.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='')):
            with self.assertRaisesRegex(ValueError,'lock missing'):
                deploy.execute(self.plan,self.pkg,self.d/'apply',False,BOOT,'a'*64)
        self.assertFalse((self.d/'apply').exists())
    def shell_fixture(self,fail=''):
        # Execute the generated transaction shell against an isolated device filesystem.
        # Only device metadata/mount commands are substituted; cp/mv/guards use real files.
        fs=self.d/'device';fs.mkdir();bins=self.d/'bin';bins.mkdir()
        cfg=fs/'system/etc/init/01_westlake_u13_toutiao.cfg';cfg.parent.mkdir(parents=True);cfg.write_bytes((self.pkg/'before.cfg').read_bytes());cfg.chmod(0o550)
        source=fs/ROOT.lstrip('/');source.mkdir(parents=True)
        for name in ('before.cfg','after.cfg'):
            (source/name).write_bytes((self.pkg/name).read_bytes());(source/name).chmod(0o440)
        proc=fs/'proc';(proc/'sys/kernel/random').mkdir(parents=True)
        (proc/'sys/kernel/random/boot_id').write_text(BOOT+'\n');(proc/'mounts').write_text('/dev/test / ext4 ro,seclabel 0 0\n')
        log=self.d/'mount.log'
        code='''import sys,os,hashlib,stat
from pathlib import Path
cmd=Path(sys.argv[0]).name;a=sys.argv[1:];p=Path(os.environ['FAKE_PROC'])
if cmd=='mount':
 with open(os.environ['FAKE_LOG'],'a') as f:f.write(' '.join(a)+'\\n')
 kind=a[1].split(',')[0]
 if os.environ.get('FAKE_FAIL')==kind:sys.exit(1)
 (p/'mounts').write_text('/dev/test / ext4 '+kind+',seclabel 0 0\\n')
elif cmd=='stat':print(oct(Path(a[-1]).stat().st_mode & 0o777)[2:]+':0:0')
elif cmd=='sha256sum':print(hashlib.sha256(Path(a[-1]).read_bytes()).hexdigest()+'  '+a[-1])
elif cmd=='ls':print('u:object_r:'+('system_etc_file' if '/system/' in a[-1] else 'data_file')+':s0')
elif cmd=='cp':
 if os.environ.get('FAKE_FAIL')=='cp':sys.exit(1)
 import shutil;shutil.copyfile(a[0],a[1])
'''
        for name in ('mount','stat','sha256sum','ls','chown','chcon','cp'):
            f=bins/name;f.write_text('#!'+sys.executable+'\n'+code);f.chmod(0o755)
        script=deploy.cfg_script(self.plan)
        script=script.replace('/system/etc/',str(fs/'system/etc')+'/').replace('/data/westlake-demo/',str(fs/'data/westlake-demo')+'/').replace('/proc/',str(proc)+'/')
        env=dict(os.environ,PATH=str(bins)+':'+os.environ['PATH'],FAKE_PROC=str(proc),FAKE_LOG=str(log),FAKE_FAIL=fail)
        r=subprocess.run(['sh','-c',script],capture_output=True,text=True,env=env,timeout=20)
        return r,cfg,proc,log
    def test_real_shell_success(self):
        r,cfg,proc,log=self.shell_fixture();self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(deploy.sha(cfg),self.plan['after_sha256']);self.assertIn('ICON_CFG_OK',r.stdout)
        self.assertIn(' ro,',(proc/'mounts').read_text())
    def test_real_shell_copy_failure_reseals(self):
        r,cfg,proc,log=self.shell_fixture('cp');self.assertNotEqual(r.returncode,0)
        self.assertEqual(deploy.sha(cfg),self.plan['before_sha256']);self.assertNotIn('ICON_CFG_OK',r.stdout)
        self.assertIn('-o ro,remount /',log.read_text())
    def test_real_shell_rw_failure_attempts_ro(self):
        r,cfg,proc,log=self.shell_fixture('rw');self.assertNotEqual(r.returncode,0)
        self.assertEqual(log.read_text().splitlines(),['-o rw,remount /','-o ro,remount /'])
        self.assertNotIn('ICON_CFG_OK',r.stdout)
    def test_real_shell_ro_failure_has_no_success(self):
        r,cfg,proc,log=self.shell_fixture('ro');self.assertNotEqual(r.returncode,0)
        self.assertNotIn('ICON_CFG_OK',r.stdout);self.assertEqual(deploy.sha(cfg),self.plan['after_sha256'])

if __name__=='__main__':unittest.main(verbosity=2)
