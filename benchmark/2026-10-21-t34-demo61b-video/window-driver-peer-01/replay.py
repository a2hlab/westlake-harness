#!/usr/bin/env python3
"""Host-only adversarial replay of the actual T34 driver functions."""
import argparse, hashlib, importlib.util, json, re, subprocess, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--window',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 pins={n:sha(a.source/n) for n in ('common.py','exec_driver.py','recover_driver.py','helper-pins.json')}
 sys.path.insert(0,str(a.source));c=load('common',a.source/'common.py');sys.modules['common']=c;r=load('peer_recovery',a.source/'recover_driver.py')
 cv=load('peer_cv',a.repo/'benchmark/2026-10-21-t34-demo61b-video/candidate-view-01/prepare.py')
 fresh=json.loads((a.window/'data/fresh.json').read_text());parent=dict(fresh['parent'],mnt=fresh['parent_mnt']);boot='11111111-2222-3333-4444-555555555555'
 rows=[]
 def case(name,fn,reject=False):
  try: fn()
  except (AssertionError,KeyError):
   if not reject: raise
   rows.append({'case':name,'result':'REJECTED_AS_REQUIRED'});return
  assert not reject, 'unexpected acceptance: '+name
  rows.append({'case':name,'result':'PASS'})
 def text():
  x=''
  for root in (c.RT,f'/proc/{parent["pid"]}/root/data/local/tmp/asx'):
   for rel,h in r.ORIGINAL.items():x+=h+'  '+root+'/'+rel+'\n'
  for p,h in dict(fresh['controls'],**{r.CFG:fresh['cfg_sha256'],r.HAP:fresh['hap_sha256']}).items():x+=h+'  '+p+'\n'
  return x+'PHYSICAL_COMPAT_ABSENT\nPRIVATE_COMPAT_ABSENT\nTimeout=30000ms  OverrideTimeout=86400000ms\nDEBUG_PROCESS_RC=0\nGet parameter "debug.ttplayer.log.enable" fail! errNum is:106!\nRESTORE_IDENTITY_MATCH\n'
 good=text()
 def verify(t):return r.verify_text(t,parent,boot,fresh['controls'],fresh['cfg_sha256'],fresh['hap_sha256'],fresh['debug_get_process_rc'])
 case('valid_exact_restore',lambda:verify(good))
 for root in (c.RT,f'/proc/{parent["pid"]}/root/data/local/tmp/asx'):
  for rel,h in r.ORIGINAL.items():
   old=h+'  '+root+'/'+rel+'\n';bad=good.replace(old,'0'*64+'  '+root+'/'+rel+'\n')
   case(('physical' if root==c.RT else 'private')+'_wrong_'+rel,lambda b=bad:verify(b),True)
 for name,old,new in [('missing_private_absence','PRIVATE_COMPAT_ABSENT\n',''),('wrong_power','OverrideTimeout=86400000ms','OverrideTimeout=10000ms'),('wrong_debug_rc','DEBUG_PROCESS_RC=0','DEBUG_PROCESS_RC=1'),('wrong_debug_body','errNum is:106!','errNum is:105!'),('missing_identity_marker','RESTORE_IDENTITY_MATCH\n',''),('wrong_cfg',fresh['cfg_sha256'],'0'*64),('wrong_hap',fresh['hap_sha256'],'0'*64),('wrong_guardian',next(iter(fresh['controls'].values())),'0'*64)]:case(name,lambda old=old,new=new:verify(good.replace(old,new)),True)
 class Fake:
  def __init__(self):
   self.w=a.window;self.repo=a.repo;self.out=a.out/'restore-local';self.out.mkdir();self.origin={'fresh_data_sha256':sha(a.window/'data/fresh.json')};self.cv=cv;self.op=['OFFLINE_NO_TRANSPORT'];self.holder='outer(codex) 1 2026-10-21T00:00:00+0800';self.start=0;self.events=[]
  def boot(self):return json.loads((a.window/'rollback-admission.json').read_text())['boot'] if (a.window/'rollback-admission.json').exists() else fresh['boot_before']
  def held(self):self.events.append('held')
  def raw(self,tag,*args):self.events.append(tag);return (1,b'',b'') if tag=='held-after' else (0,b'PHYSICAL_FILES_RESTORED_REQUIRES_FRESH_BOOT',b'')
  def reboot(self,pre):self.events.append('reboot');return boot
  def ui(self,b,tag,action,seconds):self.events.append('ui-'+action)
  def discover(self,b,include_child):assert include_child is False;self.events.append('discover');return parent,fresh['host'],None,fresh['wid'], 'mnt:[4026531841]'
  def shell(self,tag,script,to):self.events.append(tag);self.script=script;return True,good
 # An isolated fixture window preserves the actual fresh/run inputs; no changes to the real window.
 with tempfile.TemporaryDirectory() as td:
  tmp=Path(td);(tmp/'data').mkdir()
  for n in ('fresh.json','run61b.before.reference.sh'):(tmp/'data'/n).write_bytes((a.window/'data'/n).read_bytes())
  (tmp/'rollback-admission.json').write_text(json.dumps({'boot':fresh['boot_before']}))
  d=Fake();d.w=tmp
  case('actual_restore_order_and_unlock_gate',lambda:r.restore(d))
  assert d.events.index('ui-launch')<d.events.index('ui-power')<d.events.index('final-restore-verification')<d.events.index('unlock')<d.events.index('held-after')
  (a.out/'generated-final-restore.sh').write_text(d.script)
  syntax=subprocess.run(['sh','-n'],input=d.script.encode(),capture_output=True);assert syntax.returncode==0
  rows.append({'case':'generated_shell_syntax','result':'PASS'})
  checks=[l for l in d.script.splitlines() if l.startswith('test ! -')]
  assert len(checks)==8
  for i,line in enumerate(checks):
   p=tmp/f'compat-{i}';p.write_bytes(b'present') if ' ! -e ' in line else p.symlink_to(tmp/'missing-target')
   local=re.sub(r'(test ! -(?:e|L)) .*?( \|\| exit 81)$',r'\1 '+str(p)+r'\2',line)
   got=subprocess.run(['sh','-c','set -eu\n'+local+'\necho WRONG_ABSENT\n'],capture_output=True)
   assert got.returncode==81 and b'WRONG_ABSENT' not in got.stdout
  rows.append({'case':'actual_generated_8_absence_checks_reject_present_or_dangling','result':'PASS'})
  old=subprocess.run(['sh','-c','set -eu\ntest ! -e "$1" && test ! -L "$1"\necho PRIVATE_COMPAT_ABSENT','sh',str(tmp/'compat-0')],capture_output=True)
  assert old.returncode==0 and b'PRIVATE_COMPAT_ABSENT' in old.stdout
  rows.append({'case':'preserved_old_AND_list_counterexample','result':'REPRODUCED_OLD_FALSE_SUCCESS'})
  # Run the actual process guard against local file fixtures using path-only substitution.
  pr=tmp/'proc';pdir=pr/str(parent['pid']);(pdir/'ns').mkdir(parents=True)
  stat=['S',str(parent['ppid'])]+['0']*17+[str(parent['birth'])]
  (pdir/'stat').write_text(str(parent['pid'])+' (fixture) '+' '.join(stat)+'\n')
  (pdir/'status').write_text('Uid:\t0\t0\t0\t0\nTracerPid:\t0\n');(pdir/'ns/mnt').symlink_to(parent['mnt']);(pdir/'exe').write_bytes(b'fixture-exe')
  ident=dict(parent,exe_sha256=sha(pdir/'exe'));guard=cv.process_guard(ident).replace('/proc/',str(pr)+'/')
  assert subprocess.run(['sh','-c','set -eu\n'+guard],capture_output=True).returncode==0
  (pdir/'stat').write_text(str(parent['pid'])+' (fixture) '+' '.join(stat[:-1]+[str(parent['birth']+1)])+'\n')
  assert subprocess.run(['sh','-c','set -eu\n'+guard],capture_output=True).returncode==81
  rows.append({'case':'actual_process_guard_accept_then_birth_drift_reject','result':'PASS'})
 for name,rc,body,reject in [('frame0',0,b'__T34_DRIVER_REMOTE_RC__0\n',False),('missing_frame',0,b'',True),('remote1_transport0',0,b'__T34_DRIVER_REMOTE_RC__1\n',True),('duplicate_frame',0,b'__T34_DRIVER_REMOTE_RC__0\n'*2,True),('transport124',124,b'__T34_DRIVER_REMOTE_RC__0\n',True)]:
  d=SimpleNamespace(a=SimpleNamespace(hdc=Path('NO_DEVICE')),held=lambda:None,raw=lambda *args,rc=rc,body=body:(rc,body,b''))
  case(name,lambda d=d:c.Driver.shell(d,'fixture','true'),reject)
 d=SimpleNamespace(holder='original',repo=Path('.'),raw=lambda *args:(0,b'foreign',b''))
 case('changed_holder_rejected',lambda:c.Driver.held(d),True)
 d=SimpleNamespace(deadline=time.monotonic()-1);case('expired_original_deadline_rejected',lambda:c.Driver.remaining(d),True)
 rc,out,err=c.run_record(a.out/'timeout-local',[sys.executable,'-c','import sys,time;print("PARTIAL",flush=True);print("ERROR",file=sys.stderr,flush=True);time.sleep(2)'],.15)
 assert rc==124 and b'PARTIAL' in out and b'ERROR' in err;rows.append({'case':'actual_subprocess_timeout_preserves_partial_bytes','result':'PASS'})
 assert pins=={n:sha(a.source/n) for n in pins},'source changed during replay'
 result={'scope':'HOST_ONLY_NO_DEVICE_CALLS','source_pins':pins,'source_stable_before_after':True,'cases':rows,'case_count':len(rows),'runtime_admission':False}
 (a.out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
