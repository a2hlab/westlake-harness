"""Offline answers: Route B ownership guards and read-only U13 installer interface."""
import json, os, subprocess, tempfile, unittest
from pathlib import Path
D=Path(__file__).parent;W=D.parents[2]
HELPER=D/'payload/scripts/route-b-owner.sh'
class OwnershipTests(unittest.TestCase):
 def probe(self, uid='20010053', exe='/data/local/tmp/asx/asx-spawner', digest='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c', inode='1:2', expected='123', action='rb_signal 100 '+ '123 15'):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);p=root/'100';p.mkdir();(p/'status').write_text('Uid:\t'+ '\t'.join([uid]*4)+'\n');(p/'stat').write_text('100 (asx-spawner) S '+ ' '.join(['0']*18)+' 123 0\n')
   script=f'''RB_PROC='{root}'; RB_RUNTIME='{root}/runtime'; . '{HELPER}'
readlink() {{ echo '{exe}'; }}
sha256sum() {{ echo '{digest}  $1'; }}
stat() {{ case "$*" in *'/root/'*) echo '{inode}';; *) echo '1:2';; esac; }}
kill() {{ echo "SIGNAL:$*"; }}
{action}
'''
   return subprocess.run(['bash','-c',script],capture_output=True,text=True)
 def test_owned_route_b_signalled(self):
  r=self.probe();self.assertEqual(r.returncode,0,r.stderr);self.assertIn('SIGNAL:-15 100',r.stdout)
 def test_u13_root_parent_never_signalled(self):
  r=self.probe(uid='0',exe='/system/bin/appspawn-x');self.assertNotEqual(r.returncode,0);self.assertNotIn('SIGNAL:',r.stdout)
 def test_uid_executable_sha_private_root_and_birth_fail_closed(self):
  for k,v in [('uid','20010054'),('exe','/system/bin/appspawn-x'),('digest','0'*64),('inode','8:9'),('action','rb_signal 100 999 15')]:
   with self.subTest(k=k):
    r=self.probe(**{k:v});self.assertNotEqual(r.returncode,0);self.assertNotIn('SIGNAL:',r.stdout)
 def test_script_argument_must_be_exact_token(self):
  s=HELPER.read_text();self.assertIn('grep -Fxq "$script"',s);self.assertNotIn('grep -aFq',s)
class InterfaceTests(unittest.TestCase):
 def test_disabled_cfg_matches_read_only_installer_slot(self):
  cfg=json.loads((D/'payload/init/01_westlake_u13_toutiao.cfg.disabled').read_text());svc=cfg['services'][0]
  self.assertEqual(svc['name'],'westlake-u13-toutiao-overlay');self.assertEqual(svc['path'],['/system/bin/sh','/system/etc/westlake-u13-toutiao-overlay.sh']);self.assertEqual(cfg['jobs'][0]['condition'],'sys.westlake.demo.u13.ready=true')
  wiki=W/'westlake-harness-wiki/benchmark/2026-10-10-u13-autostart/payload-61b/init/00_westlake_u13_recover.cfg'
  if wiki.exists():
   text=wiki.read_text();self.assertIn(svc['name'],text);self.assertIn(svc['path'][-1],text)
 def test_no_name_based_kill_and_no_u13_service_change(self):
  for name in ['watchdog.sh','rollback_toutiao_boot_slot.sh','route-b-owner.sh']:
   s=(D/'payload/scripts'/name).read_text();self.assertNotIn('pidof', '\n'.join(l for l in s.splitlines() if not l.lstrip().startswith('#')));self.assertNotIn('pkill',s);self.assertNotIn('killall',s)
  worker=(D/'payload/scripts/westlake-u13-toutiao-overlay.sh').read_text()
  for command in ['begetctl','mount --bind','aa start','reboot','setenforce']:
   self.assertNotIn(command,'\n'.join(l for l in worker.splitlines() if not l.lstrip().startswith('#')))
 def test_same_boot_cannot_spawn_second_supervisor(self):
  s=(D/'payload/scripts/westlake-u13-toutiao-overlay.sh').read_text();self.assertIn('fail SAME_BOOT_ALREADY_ATTEMPTED',s);self.assertNotIn('log ALREADY_ARMED',s)
 def test_shell_syntax(self):
  for p in (D/'payload/scripts').glob('*.sh'):
   with self.subTest(p=p.name):subprocess.run(['bash','-n',str(p)],check=True)
if __name__=='__main__': unittest.main()
