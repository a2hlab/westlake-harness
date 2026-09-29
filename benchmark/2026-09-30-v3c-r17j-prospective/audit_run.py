#!/usr/bin/env python3
"""Read-only audit of the producer's completed run and actual component hashes."""
import argparse,datetime,hashlib,json,re
from pathlib import Path
from score import HERE,sha,verify,effective_profile
HASH=re.compile(r'^([0-9a-f]{64})\s+(/\S+)\s*$')
def read_hashes(text):
 rows={}
 for line in text.splitlines():
  match=HASH.match(line.strip())
  if not match:continue
  digest,path=match.groups()
  if path in rows and rows[path]!=digest:raise ValueError('conflicting hashes: '+path)
  rows[path]=digest
 return rows
def projected_hashes(package,profile):
 expected={}
 for mount in package['mounts']:
  for path,digest in package['files'].items():
   if path==mount['source']:expected[mount['target']]=digest
   elif path.startswith(mount['source']+'/'):expected[mount['target']+path[len(mount['source']):]]=digest
 routes={m['target'] for m in package['mounts'] if m['source']=='payload/route'}
 selected={path:h for path,h in expected.items() if (path.startswith('/system/android/lib64/') and path.endswith('.so')) or (any(path.startswith(r+'/') for r in routes) and path.endswith('.so')) or path in ('/system/bin/appspawn-x','/system/android/framework/oh-adapter-runtime.jar')}
 selected['/system/android/framework/oh-adapter-runtime.jar']=profile['jar_sha256']
 return selected,expected
def audit_installer(path,profile):
 result={'verified':False,'source':str(path) if path else None,'errors':[],'rows':{}}
 if path is None or not path.exists():result['errors'].append('installer_readback_missing');return result
 result['source_sha256']=sha(path);text=path.read_text(errors='replace');rows=read_hashes(text)
 boot=re.search(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',text)
 result['boot_id']=boot[0] if boot else None
 result['capture_header']=text.splitlines()[0] if text else None
 foundation_pid=re.search(r'foundation=(\d+)',text);result['foundation_pid']=int(foundation_pid[1]) if foundation_pid else None
 for name,expected in profile['installer_sha256'].items():
  found={k:v for k,v in rows.items() if Path(k).name==name};root={k:v for k,v in found.items() if k.startswith('/system/')};foundation={k:v for k,v in found.items() if re.match(r'/proc/\d+/root/system/',k)}
  result['rows'][name]={'root':root,'foundation_root':foundation,'expected':expected}
  if not root:result['errors'].append(name+':root_readback_missing')
  if not foundation:result['errors'].append(name+':foundation_readback_missing')
  if foundation_pid and any(not k.startswith('/proc/'+foundation_pid[1]+'/root/') for k in foundation):result['errors'].append(name+':foundation_pid_mismatch')
  if any(v!=expected for v in found.values()):result['errors'].append(name+':hash_mismatch')
 result['verified']=not result['errors'];return result
def audit_run(run,freeze=HERE/'freezes/v2',installer_readback=None,amendment=HERE/'execution-amendment-5ea.json'):
 verify(freeze);profile=effective_profile(freeze,amendment);package=json.loads((freeze/'evidence/v3c-package.json').read_text());expected,all_expected=projected_hashes(package,profile)
 errors=[];run=Path(run);facts=run/'facts.txt';fingerprint=run/'runtime-fingerprint.txt';sources={};rows={};short=None;header=None
 if not fingerprint.exists():errors.append('runtime_fingerprint_missing')
 else:
  body=fingerprint.read_text().strip();short=hashlib.sha256(body.encode()).hexdigest()[:12];rows=read_hashes(body);sources['runtime-fingerprint.txt']=sha(fingerprint)
 if not facts.exists():errors.append('facts_missing_or_run_incomplete')
 else:
  text=facts.read_text();header=text.splitlines()[0] if text else '';sources['facts.txt']=sha(facts);m=re.fullmatch(r'RUNTIME fingerprint=([0-9a-f]{12}) files=(\d+) .*',header)
  if not m:errors.append('facts_header_invalid')
  elif m[1]!=short or int(m[2])!=len(rows):errors.append('facts_fingerprint_mismatch')
 baseline=run/'baseline.json';boot=None
 if baseline.exists():
  b=json.loads(baseline.read_text());boot=b.get('boot_id');sources['baseline.json']=sha(baseline)
  if b.get('runtime_fingerprint')!=short:errors.append('baseline_fingerprint_mismatch')
 missing=[p for p in expected if p not in rows];different=[{'path':p,'expected':h,'actual':rows[p]} for p,h in expected.items() if p in rows and rows[p]!=h]
 if missing:errors.append('runtime_paths_missing')
 if different:errors.append('runtime_hash_mismatch')
 extras=[p for p in rows if p.startswith('/system/android/') and p not in expected]
 if extras:errors.append('unexpected_android_runtime_component')
 installer=audit_installer(installer_readback or run/'installer-readback.txt',profile);errors.extend(installer['errors'])
 if not boot or installer.get('boot_id')!=boot:errors.append('installer_boot_unknown_or_mismatch')
 for path,digest in rows.items():
  name=Path(path).name
  if name in profile['installer_sha256'] and digest!=profile['installer_sha256'][name]:errors.append('installer_fingerprint_mismatch:'+path)
 if run.name not in profile['boards']:errors.append('board_unknown')
 return {'verified':not errors,'errors':errors,'board':run.name,'boot_id':boot,'run':str(run),'facts_first_line':header,'runtime_fingerprint':short,'source_hashes':sources,'runtime_projection':{'required':len(expected),'matched':len(expected)-len(missing)-len(different),'missing':missing,'different':different,'unexpected_android':extras,'unmeasured_package_paths':sorted(set(all_expected)-set(expected))},'installer':installer,'profile':{k:profile[k] for k in ('package_sha256','jar_sha256','installer_sha256')},'package_identity_basis':'Outer active_verified attestation plus run-local runtime hash projection; unmeasured package paths are explicitly listed, not claimed rehashed.','run_scope_limit':'Producer snapshot is at run start; per-app sampled profile/boot disagreements must be excluded.'}
def record_facts(record,run_audit):
 folder=record.parent;r=json.loads(record.read_text());uid=(r.get('bms') or {}).get('uid');captures=[];processes={};errors=[]
 for shot in r.get('screenshots',[]):
  if shot.get('captured') is not True:continue
  p=Path(shot['path']);valid=p.is_file() and sha(p)==shot.get('sha256');captures.append({'path':str(p),'sha256':shot.get('sha256'),'valid':valid,'scheduled_seconds':shot.get('scheduled_seconds')})
  if not valid:errors.append('screenshot_hash_or_file_missing')
 for stage in ('t5','t20'):
  p=folder/('processes-'+stage+'.txt');found=[];helpers=[]
  if not p.exists() or uid is None:processes[stage]=None;continue
  lines=p.read_text().splitlines();header=lines[0].split() if lines else []
  if not {'UID','PID','PPID','NAME'}<=set(header):processes[stage]=None;continue
  for lineno,line in enumerate(lines[1:],2):
   f=line.split()
   if len(f)>=4 and f[header.index('UID')]==str(uid):
    item={'pid':int(f[header.index('PID')]),'ppid':int(f[header.index('PPID')]),'name':f[header.index('NAME')],'line':lineno}
    (found if item['name']=='appspawn-x' or item['name']==r.get('package') else helpers).append(item)
  processes[stage]={'source':str(p),'sha256':sha(p),'app_processes':found,'same_uid_helpers':helpers,'alive':bool(found)}
 grant=None;bundle=folder/'bundle.txt'
 if bundle.exists():
  try:
   raw=bundle.read_text();b=json.loads(raw[raw.index('{'):]);idx=b['reqPermissions'].index('ohos.permission.START_ABILITIES_FROM_BACKGROUND');grant=b['reqPermissionStates'][idx]==0
  except (ValueError,KeyError,IndexError):pass
 if not run_audit['boot_id'] or r.get('boot_id')!=run_audit['boot_id']:errors.append('record_boot_unknown_or_mismatch')
 if r.get('serial')!=run_audit['board']:errors.append('record_board_unknown_or_mismatch')
 if r.get('runtime_fingerprint') and r['runtime_fingerprint']!=run_audit['runtime_fingerprint']:errors.append('record_runtime_mismatch')
 if r.get('clicked') is not True:errors.append('record_not_clicked')
 return {'key':r['key'],'uid':uid,'record':str(record),'record_sha256':sha(record),'apk_sha256':r.get('apk_sha256'),'clicked_at':r.get('clicked_at'),'clicked':r.get('clicked'),'record_status':r.get('status'),'record_error':r.get('error'),'actual_launcher':(r.get('bms') or {}).get('desktop_activity'),'queryable':(r.get('bms') or {}).get('queryable'),'grant_verified':grant,'grant_evidence':str(bundle) if bundle.exists() else None,'grant_evidence_sha256':sha(bundle) if bundle.exists() else None,'captures':captures,'captured_count':len(captures),'processes':processes,'errors':errors}
def launcher_verified(key,actual):
 old=HERE.parent/'2026-09-30-background-start-prospective';receipt=old/'freezes/v1/predictions.json'
 indexed={x['prediction']['key']:x['prediction'] for x in json.loads(receipt.read_text())}
 expected=indexed.get(key)
 if not expected or not actual:return None
 path=old/'evidence'/(key+'.json')
 if sha(path)!=expected['evidence_sha256']:raise ValueError('launcher input evidence changed: '+key)
 data=json.loads(path.read_text());name=actual.replace('.','/');aliases={x['class']:x.get('target') for x in data.get('activities',[]) if x.get('target')};resolved=aliases.get(name,name)
 # Explicit known-answer fixture: SelectLauncher must avoid LeakCanary's Activity.
 if key=='anki':return resolved=='com/ichi2/anki/IntentHandler'
 return resolved in data.get('launchers',[])
def observations_from_run(observations,run,audit):
 """Outcome labels come from adjudication; identity/permission facts come from the run."""
 checked=[];facts=[]
 for original in observations:
  o=dict(original);record=run/o['key']/'record.json'
  if not record.exists():raise ValueError('observation has no source record: '+o['key'])
  if o.get('board',run.name)!=run.name:raise ValueError('observation board disagrees with run')
  f=record_facts(record,audit);raw=json.loads(record.read_text());facts.append(f)
  if o.get('apk_sha256') and o['apk_sha256']!=f['apk_sha256']:f['errors'].append('adjudication_apk_mismatch')
  stamp=f['clicked_at'];clicked=datetime.datetime.fromtimestamp(stamp,datetime.timezone.utc).isoformat() if isinstance(stamp,(int,float)) else None
  assembly=raw.get('native_assembly') or {};assembled=assembly.get('status') in ('verified','not_needed') and all(x.get('verified') is True for x in assembly.get('files',[]))
  launcher=launcher_verified(o['key'],f['actual_launcher']) if f['queryable'] else None
  o.update(board=run.name,apk_sha256=f['apk_sha256'],clicked_at=clicked,grant_verified=f['grant_verified'],select_launcher_verified=launcher if audit['installer']['verified'] else None,batch_sidecars_enabled=assembled,runtime_audit_verified=audit['verified'] and not f['errors'],profile_evidence=str(run/'facts.txt'),actual_launcher=f['actual_launcher'],source_record=f['record'],source_record_sha256=f['record_sha256'],**audit['profile'])
  # The claimed UI verdict must refer to one of this exact record's verified captures.
  screenshot=o.get('screenshot_evidence')
  if screenshot and str(Path(screenshot).resolve()) not in {str(Path(s['path']).resolve()) for s in f['captures'] if s['valid']}:
   o['screenshot_evidence']=None;o['screenshot_rejected']='not a verified capture of this record'
  checked.append(o)
 return checked,facts
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--installer-readback',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();report=audit_run(a.run,installer_readback=a.installer_readback);report['records']=[record_facts(r,report) for r in sorted(a.run.glob('*/record.json'))]
 with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'verified':report['verified'],'errors':report['errors'],'records':len(report['records']),'runtime_projection':report['runtime_projection']['matched']},indent=2))
if __name__=='__main__':main()
