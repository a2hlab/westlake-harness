"""Real boot-entry shell with lexical path relocation; endpoint/native tools are
explicit recorded substitutes. No board, init, namespace or UI acceptance."""
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
D=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
A='11111111-1111-1111-1111-111111111111';B='22222222-2222-2222-2222-222222222222'
class AutoBootTests(unittest.TestCase):
 def setup_case(self,real_entry=False):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);tmp=Path(t.name);root=tmp/'candidate';root.mkdir();tools=tmp/'tools';tools.mkdir();kernel=tmp/'kernel-boot';kernel.write_text(A+'\n');old=tmp/'historical-stop';old.write_bytes(b'');calls=tmp/'calls';config=D/'payload/config-common.sh'
  def relocate(s):
   return s.replace('/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview',str(root)).replace('/data/local/tmp/operator45/selfheal48/stop',str(old)).replace('/proc/sys/kernel/random/boot_id',str(kernel)).replace('/system/bin/sh','/bin/bash').replace('export PATH=/system/bin:/bin:/system/xbin','export PATH='+str(tools)+':/usr/bin:/bin')
  for name in ['boot-entry.sh','config-common.sh']:(root/name).write_text(relocate((D/'payload'/name).read_text()))
  entry='#!/bin/bash\nprintf "ENTRY kernel=%s\\n" "$(cat '+str(kernel)+')" >> '+str(calls)+'\n'
  if real_entry:entry=relocate((D/'payload/entry.sh').read_text())
  (root/'entry.sh').write_text(entry)
  for name in ['stat','chown','chcon','timeout','nsenter','hidumper']:
   text='#!/bin/bash\nexit 0\n'
   if name=='stat':text='#!/bin/bash\nprintf "20011206\\n"\n'
   if name=='timeout':text='#!/bin/bash\nshift; exec "$@"\n'
   if name=='hidumper':text='#!/bin/bash\nprintf "imehost0 a b 33 d e f 1\\n"\n'
   (tools/name).write_text(text);(tools/name).chmod(0o755)
  (tools/'sha256sum').write_text('#!/bin/bash\nexec /usr/bin/shasum -a 256 "$@"\n');(tools/'sha256sum').chmod(0o755)
  if real_entry:
   # Real decoder compiled from exactly the production C source for host tests.
   subprocess.run(['clang','-O2',str(D/'src/screen_gate_jpeg.c'),'-o',str(root/'screen-gate'),'-lm'],check=True)
   (root/'decoder-probe.jpeg').write_bytes(b'\xff\xd8BROKEN')
  rows=[]
  for name in ['entry.sh','config-common.sh']+(['screen-gate','decoder-probe.jpeg'] if real_entry else []):rows.append(f'{sha(root/name)} {name} 550\n')
  (root/'members.tsv').write_text(''.join(rows))
  cfg=(D/'payload/startup.env').read_text().replace("STARTUP_APPROVED_BY='PENDING'","STARTUP_APPROVED_BY='outer(codex)'").replace("STARTUP_ENABLED='0'","STARTUP_ENABLED='1'")
  import re
  for key,value in [('STARTUP_MEMBERS_SHA',sha(root/'members.tsv')),('STARTUP_DECODER_SHA',sha(root/'screen-gate') if real_entry else '0'*64),('STARTUP_PROBE_SHA',sha(root/'decoder-probe.jpeg') if real_entry else '0'*64)]:cfg=re.sub(key+r"='[^']*'",key+"='"+value+"'",cfg)
  (root/'startup.env').write_text(cfg);(root/'startup.expected.sha256').write_text(sha(root/'startup.env')+'\n')
  # Config tools are explicitly relocated for host execution; log their identity.
  provenance={n:dict(source_sha256=sha(D/'payload'/n),rendered_sha256=sha(root/n)) for n in ['boot-entry.sh','config-common.sh']}
  return tmp,root,tools,kernel,old,calls,provenance
 def invoke(self,root,tools):return subprocess.run(['/bin/bash',str(root/'boot-entry.sh')],env={**os.environ,'PATH':str(tools)+':/usr/bin:/bin'},capture_output=True,text=True)
 def test_same_immutable_config_two_boots_no_mac_authorization(self):
  tmp,root,tools,kernel,old,calls,prov=self.setup_case();config_sha=sha(root/'startup.env');x=self.invoke(root,tools);self.assertEqual(x.returncode,0,x.stderr)
  kernel.write_text(B+'\n');x=self.invoke(root,tools);self.assertEqual(x.returncode,0,x.stderr)
  self.assertEqual(calls.read_text().splitlines(),['ENTRY kernel='+A,'ENTRY kernel='+B]);self.assertEqual(sha(root/'startup.env'),config_sha);self.assertEqual(old.read_bytes(),b'')
  self.assertFalse((root/'authorization.env').exists());self.assertTrue((root/'boots'/A/'entry.sh').is_file());self.assertTrue((root/'boots'/B/'entry.sh').is_file())
 def test_candidate_stop_survives_later_boot(self):
  tmp,root,tools,kernel,old,calls,prov=self.setup_case();self.assertEqual(self.invoke(root,tools).returncode,0);(root/'boots'/A/'stop').write_text('operator stop\n');kernel.write_text(B+'\n');x=self.invoke(root,tools);self.assertNotEqual(x.returncode,0);self.assertIn('ATTEMPT_STOP',x.stderr);self.assertFalse((root/'boots'/B).exists())
 def test_config_drift_and_unsigned_no_entry(self):
  for kind in ['drift','unsigned']:
   tmp,root,tools,kernel,old,calls,prov=self.setup_case()
   if kind=='drift':(root/'startup.env').write_text('STARTUP_ENABLED=1\n')
   else:(root/'startup.expected.sha256').write_text('NONE\n')
   x=self.invoke(root,tools);self.assertNotEqual(x.returncode,0);self.assertFalse(calls.exists())
 def test_real_entry_corrupt_decoder_before_parent(self):
  tmp,root,tools,kernel,old,calls,prov=self.setup_case(True);x=self.invoke(root,tools);self.assertNotEqual(x.returncode,0,x.stderr);self.assertIn('DECODER_PRELAUNCH_FAILED',x.stderr);self.assertNotIn('READY',x.stdout);self.assertFalse((root/'boots'/A/'parent-start.txt').exists())
 def test_first_human_tap_after_virtual_601_seconds_enters_guardian_guard(self):
  tmp,root,tools,kernel,old,calls,prov=self.setup_case(True)
  # Actual entry and C decoder; virtual clock advances >old600 limit in one
  # read-only wait. Real immutable watchdog is reached and then fails on the
  # host's absent /proc; no namespace/parent/spawn is invoked.
  import re
  (root/'decoder-probe.jpeg').write_bytes((D/'payload/decoder-probe.jpeg').read_bytes())
  for name in ['watchdog.sh','route-b-owner.sh','launch-common.sh']:
   text=(D/'payload'/name).read_text()
   if name=='launch-common.sh':text=text.replace('/system/bin/sh','/bin/bash')
   (root/name).write_text(text)
  rows=[]
  for name in ['entry.sh','config-common.sh','screen-gate','decoder-probe.jpeg','watchdog.sh','route-b-owner.sh','launch-common.sh']:rows.append(f'{sha(root/name)} {name} 550\n')
  (root/'members.tsv').write_text(''.join(rows));cfg=(root/'startup.env').read_text()
  for key,value in [('STARTUP_MEMBERS_SHA',sha(root/'members.tsv')),('STARTUP_PROBE_SHA',sha(root/'decoder-probe.jpeg'))]:cfg=re.sub(key+r"='[^']*'",key+"='"+value+"'",cfg)
  (root/'startup.env').write_text(cfg);(root/'startup.expected.sha256').write_text(sha(root/'startup.env')+'\n')
  elapsed=tmp/'elapsed';ready=tmp/'human-ready'
  (tools/'hidumper').write_text('#!/bin/bash\n[ -e '+str(ready)+' ] || exit 1\nprintf "imehost0 a b 33 d e f 1\\n"\n');(tools/'hidumper').chmod(0o755)
  (tools/'sleep').write_text('#!/bin/bash\nprintf "601\\n" > '+str(elapsed)+'\n: > '+str(ready)+'\n');(tools/'sleep').chmod(0o755)
  x=self.invoke(root,tools);self.assertEqual(elapsed.read_text().strip(),'601');self.assertIn('launching immutable guardian',x.stdout);self.assertNotIn('READY',x.stdout);self.assertFalse((root/'boots'/A/'parent-start.txt').exists())
 def test_cfg_privileges_and_no_expiring_runtime_ticket(self):
  cfg=json.loads((D/'payload/recovery.cfg').read_text());s=cfg['services'][0]
  for field in ['permission','permission_acls']:self.assertEqual(set(s[field]),{'ohos.permission.DUMP','ohos.permission.CAPTURE_SCREEN'})
  self.assertEqual(s['uid'],'root');self.assertEqual(s['setuid'],True);self.assertEqual(s['secon'],'u:r:su:s0');self.assertNotIn('caps',s)
  for file in ['config-common.sh','boot-entry.sh','entry.sh','startup.env']:
   text=(D/'payload'/file).read_text();self.assertNotIn('AUTH_EXPIRES',text);self.assertNotIn('9529',text);self.assertNotIn('WL_PARENT_ID=33',text)
if __name__=='__main__':unittest.main(verbosity=2)
