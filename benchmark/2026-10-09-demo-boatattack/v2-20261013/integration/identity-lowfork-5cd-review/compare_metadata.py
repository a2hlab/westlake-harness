#!/usr/bin/env python3
"""Default offline preview; original/candidate metadata-only comparison on fixed5cd."""
import argparse,hashlib,importlib.util,json,os,re,shlex,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
SERIAL='5cd1e3dd00000000000000000923012c'
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def resolve(p):return Path(os.path.expandvars(p))
def pinned(ref):
 p=resolve(ref['path']);need(p.is_file() and sha(p)==ref['sha256'],'source pin drift: '+str(p));return p
def module(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def validate(p):
 need(p['serial']==SERIAL and p['schema']=='metadata-ab-readonly/v1','5cd-only plan')
 need(0<p['max_seconds']<=1200,'20min budget within30min window')
 for ref in p['pins'].values():pinned(ref)
 need(len(p['files'])==507 and len(p['directories'])==5 and len(p['candidate_sha256'])==18,'full507+5/18 required')
 need(not set(p['files'])&set(p['directories']),'file/directory overlap')
 for target in [*p['files'],*p['directories'],*p['candidate_sha256']]:need(re.fullmatch(r'/(system|data)/[A-Za-z0-9_./+-]+',target) and '..' not in target.split('/'),'unsafe target')
 original=module(pinned(p['pins']['original']),'metadata_original');candidate=module(pinned(p['pins']['candidate']),'metadata_candidate');base=module(pinned(p['pins']['reader']),'metadata_base')
 need(candidate.ORIGINAL_SHA256==p['pins']['original']['sha256'],'candidate base differs')
 original.parse_metadata('\n'.join(t+'|'+'|'.join(str(m[k]) for k in ('mode','uid','gid','label')) for t,m in p['files'].items()),p['files'])
 original.parse_metadata('\n'.join(t+'|'+'|'.join(str(m[k]) for k in ('mode','uid','gid','label')) for t,m in p['directories'].items()),p['directories'])
 return original,candidate,base

def execute(p,auth,out,mods):
 need(sys.platform=='linux','original Reader transport requires Orb Linux; use command card')
 need(auth['approved_by']=='outer(codex)' and auth['action']=='metadata-readonly-ab' and auth['serial']==SERIAL and auth['boot_id']==p['boot_id'],'authorization identity')
 need(auth['holder'].split()[0]=='outer(codex)' and len(auth['holder'].split())==3,'complete actual holder')
 need(time.time()<auth['expires_epoch']<=time.time()+1800,'fresh bounded authority')
 deadline=min(time.monotonic()+p['max_seconds'],time.monotonic()+auth['expires_epoch']-time.time())
 need(not out.exists(),'fresh output');out.mkdir(parents=True)
 result={'status':'RUNNING','serial':SERIAL,'boot_id':p['boot_id'],'remote_writes':0,'lock_operations':0,'phases':[],'accepted_for_full128':False}
 def budget():need(time.monotonic()+90<deadline and time.time()<auth['expires_epoch'],'insufficient remaining90s transport budget')
 def held(tag):
  budget();r=subprocess.run(['mac','bash',str(pinned(p['pins']['lock'])),'held',SERIAL],capture_output=True,text=True,timeout=15)
  save(out/(tag+'-held.json'),{'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr});need(r.returncode==0 and not r.stderr and r.stdout.strip()==auth['holder'],'canonical Mac holder changed')
 def make(factory,folder):
  folder.mkdir();calls=[]
  class Logged(factory(mods[2].Reader)):
   def _presence_read(self,name,command):
    budget();started=time.monotonic()
    try:return super()._presence_read(name,command)
    finally:
     calls.append({'name':name,'command':command,'seconds':time.monotonic()-started});save(folder/'calls.json',calls)
  return Logged(folder,SERIAL),calls
 def guard(reader,tag):
  boot=reader._presence_read('boot-'+tag,'cat /proc/sys/kernel/random/boot_id');need(boot==p['boot_id'],'boot changed')
  text=reader._presence_read('sha-'+tag,'sha256sum '+' '.join(shlex.quote(t) for t in p['candidate_sha256']))
  rows={}
  for line in text.splitlines():
   m=re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)',line);need(m is not None and m[2] not in rows,'malformed/duplicate candidate SHA');rows[m[2]]=m[1]
  need(rows==p['candidate_sha256'],'candidate18 SHA changed');return {'boot':boot,'candidate18_sha256':rows}
 try:
  for name,factory in [('original',mods[0].with_presence),('candidate',mods[1].with_presence)]:
   held(name+'-before');reader,calls=make(factory,out/name);before=guard(reader,'before');started=time.monotonic()
   reader.verify_metadata(p['files'],p['directories']);duration=time.monotonic()-started
   metadata_calls=[c for c in calls if c['name']=='metadata'];need(len(metadata_calls)==23,'original23 batches required')
   after=guard(reader,'after');held(name+'-after');need(before==after,'phase bookends differ')
   phase={'name':name,'metadata_seconds':duration,'metadata_calls':len(metadata_calls),'objects':512,'expected_matched':True,'bookends_equal':True};result['phases'].append(phase);save(out/'result.json',result)
  # Same expected map/parser and target shell; stdout includes differing unique rc marker.
  old=out/'original';new=out/'candidate';a=sorted(old.glob('presence-*-metadata.stdout.txt'));b=sorted(new.glob('presence-*-metadata.stdout.txt'))
  def body(path):return re.sub(r'\n__BOAT_PRESENCE_RC_[0-9a-f]+__0\s*$','',path.read_text()).strip()
  need(len(a)==len(b)==23 and all(body(x)==body(y) for x,y in zip(a,b)),'ordered metadata output differs')
  result.update(status='METADATA_AB_PASS_ONLY',ordered_metadata_equal=True,speed_ratio=result['phases'][0]['metadata_seconds']/result['phases'][1]['metadata_seconds'])
 except Exception as e:result.update(status='FAILED_READONLY_EVIDENCE_RETAINED',error=str(e))
 finally:save(out/'result.json',result)
 return 0 if result['status']=='METADATA_AB_PASS_ONLY' else 2

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--plan',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--execute',action='store_true');a.add_argument('--authorization',type=Path);a.add_argument('--authorization-sha256');x=a.parse_args();p=read(x.plan);mods=validate(p)
 if not x.execute:print(json.dumps({'status':'PREVIEW_ONLY','serial':SERIAL,'objects':512,'batches_per_helper':23,'device_calls':0,'execution_enabled':p['execution_enabled']}));return 0
 need(p['execution_enabled'] is True,'disabled plan');need(x.authorization and sha(x.authorization)==x.authorization_sha256,'independent authorization pin');auth=read(x.authorization);need(auth['plan_sha256']==sha(x.plan) and auth['runner_sha256']==sha(__file__),'plan/runner auth pins');return execute(p,auth,x.out,mods)
if __name__=='__main__':raise SystemExit(main())
