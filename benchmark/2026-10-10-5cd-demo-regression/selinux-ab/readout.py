#!/usr/bin/env python3
"""Offline A/B facts, final-shot contacts and PID-attributed CANTOPEN/first-fatal.
Counts are log-line occurrences, not unique exceptions; no UI verdict is inferred.
"""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;D=HERE.parent;WS=Path(os.environ.get('WORKSPACES',D.parents[2]));SERIAL='5cd1e3dd00000000000000000923012c'
def read(p):return json.loads(Path(p).read_text())
def portable(p):return str(Path(p).resolve()).replace(str(WS),'$WORKSPACES')
def analyze(p):
 r=read(p);log=p.parent/'hilog.txt';lines=log.read_text(errors='replace').splitlines() if log.is_file() else [];package=re.escape(r['package']);pids=set(r.get('observed_pids') or [])
 for v in lines:
  for pattern in [r'spawned pname_'+package+r', pid_(\d+)',r'\bb:'+package+r' pid:(\d+)']:
   m=re.search(pattern,v)
   if m:pids.add(int(m[1]))
 def own(v):
  m=re.match(r'^\S+ \S+\s+(\d+)\s+',v)
  return bool(m and int(m[1]) in pids)
 wms=[{'line':i+1,'text':v,'target_package':r['package'] in v} for i,v in enumerate(lines) if 'already existed in array' in v]
 cant=[{'line':i+1,'text':v,'target_pid':own(v)} for i,v in enumerate(lines) if re.search('CANTOPEN',v,re.I)]
 fatal=re.compile(r'J_invokeStaticMain_main_threw|JniAbort|FATAL EXCEPTION|Fatal signal|exit with signal|Unable to start activity|DfxFaultLogger.*(?:Pid|Process)',re.I)
 hits=[{'line':i+1,'text':v} for i,v in enumerate(lines) if own(v) and 'MUSL-SIGCHAIN' not in v and fatal.search(v)]
 times=[(x.get('scheduled_seconds',-1),x) for x in r.get('screenshots',[]) if x.get('captured')]
 shot=max(times,key=lambda x:x[0])[1] if times else None
 return {'key':r['key'],'package':r['package'],'uid':r.get('bms',{}).get('uid'),'status':r['status'],'error':r.get('error'),'launch_method':r.get('launch_method'),'clicked':r.get('clicked'),'target_pids':sorted(pids),'cantopen_log_lines':len(cant),'target_cantopen_log_lines':sum(x['target_pid'] for x in cant),'wms_already_existed_log_lines':len(wms),'target_wms_already_existed_log_lines':sum(x['target_package'] for x in wms),'wms_already_existed_original_lines':wms,'first_cantopen':cant[0] if cant else None,'first_fatal':hits[0] if hits else None,'fatal_unknown':not hits,'bind_returned_ok':sum(own(v) and '[B43-BIND] handleBindApplication returned OK' in v for v in lines),'record':portable(p),'hilog':portable(log),'last_shot':shot,'interpretation':'No PID/launch or missing hilog makes zero CANTOPEN uninformative; screenshot verdict is outer-owned.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(exist_ok=False)
 keys=(D/'resume-organicmaps/compare-observed-89/suspect.keys').read_text().split();modes={}
 for mode in ['enforcing','permissive']:
  rows={};paths={}
  for p in a.run.glob(mode+'-*/*/*/*/record.json'):
   if not read(p).get('finished_at'):continue
   v=analyze(p)
   if v['key'] in rows:raise ValueError('duplicate mode/key')
   rows[v['key']]=v;paths[v['key']]=p
  modes[mode]=rows;view=a.out/mode/SERIAL;view.mkdir(parents=True)
  for key,p in paths.items():
   (view/key).symlink_to(p.parent.resolve(),target_is_directory=True)
  for name in ['runtime-fingerprint.txt','boot-image-fingerprint.txt','plan.json']:
   files=[p.parent.parent/name for p in paths.values()]
   if files and all(x.exists() for x in files):
    if name!='plan.json' and len({x.read_bytes() for x in files})!=1:raise ValueError('mode fingerprint drift')
    (view/name).write_bytes(files[0].read_bytes())
  if rows:
   facts=subprocess.check_output([sys.executable,str(WS/'westlake-harness/scripts/lab/run_facts.py'),str(view.parent)],text=True);(a.out/(mode+'-facts.txt')).write_text(facts)
  images=a.out/(mode+'-last-shots');images.mkdir()
  for key,row in rows.items():
   shot=row['last_shot'];dest=images/key;dest.mkdir();p=paths[key]
   if shot:
    seconds=shot['scheduled_seconds'];tag='t'+str(float(seconds)).removesuffix('.0');source=p.parent/(tag+'.jpeg')
    if source.exists():(dest/'final.jpeg').symlink_to(source.resolve())
   (dest/'record.json').write_text(json.dumps({'key':key})+'\n')
  if rows:
   with (a.out/(mode+'-contact-mapping.txt')).open('w') as f:subprocess.run([str(WS/'westlake-harness/scripts/lab/contact_sheet.sh'),str(a.out/(mode+'-contact.jpeg')),'--run',str(images),'--shot','final'],stdout=f,stderr=subprocess.STDOUT,check=True)
 comparison=[{'key':k,**{m:modes[m].get(k,{'status':'unknown','reason':'not captured in bounded window'}) for m in modes}} for k in keys]
 (a.out/'comparison.json').write_text(json.dumps({'schema':'selinux-icon-click-ab/v1','counts_are':'log-line occurrences, not unique exceptions','keys':comparison},ensure_ascii=False,indent=2).replace(str(WS),'$WORKSPACES')+'\n')
 text=['key\tenforcing_CANTOPEN\tpermissive_CANTOPEN\tenforcing_WMS_already_existed\tpermissive_WMS_already_existed\tenforcing_first_fatal\tpermissive_first_fatal']
 for row in comparison:
  values=[]
  for mode in modes:
   v=row[mode];values.append(str(v.get('target_cantopen_log_lines','unknown')))
  fatalvalues=[(row[m].get('first_fatal') or {}).get('text','unknown') for m in modes]
  wmsvalues=[str(row[m].get('target_wms_already_existed_log_lines','unknown')) for m in modes]
  text.append('\t'.join([row['key']]+values+wmsvalues+fatalvalues))
 (a.out/'comparison.tsv').write_text('\n'.join(text)+'\n')
 print(json.dumps({'keys_requested':26,'captured':{k:len(v) for k,v in modes.items()},'missing':{k:sorted(set(keys)-set(v)) for k,v in modes.items()},'UI_verdict':'pending_outer_review'}))
if __name__=='__main__':main()
