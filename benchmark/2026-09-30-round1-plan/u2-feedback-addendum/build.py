#!/usr/bin/env python3
"""Additive correction of U2 JNA causal order and VLC theme interpretation."""
import csv,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'u2-feedback'
NATIVE=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/benchmark/2026-09-30-n3-native')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def dump(name,x):(HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def matches(path,symbol,package):
 lines=path.read_text(errors='replace').splitlines()
 pids={l.split()[2] for l in lines if 'nativeOnScheduleLaunchApplication ENTRY bundle='+package+' ' in l}
 found=[dict(line=n,text=l) for n,l in enumerate(lines,1) if len(l.split())>2 and l.split()[2] in pids and 'libjnidispatch.so s='+symbol+' ' in l and 'relocating failed:' in l]
 assert found,(path,symbol)
 return dict(log=str(path),sha256=sha(path),pids=sorted(pids),symbol=symbol,evidence=found)
def main():
 u0={r['key']:r for r in read(HERE.parent/'u0-assetfd-feedback/per-key.json')};evidence={r['key']:r for r in read(OLD/'evidence.json')}
 rows=read(OLD/'unlit-42.json');clusters=read(OLD/'next-clusters.json');changes=[]
 for key in ['firefox','fd-fennec_fdroid']:
  e=evidence[key];before=matches(Path(u0[key]['log']),'__errno',e['package']);after=matches(Path(e['log']),'__sF',e['package'])
  row=next(r for r in rows if r['key']==key)
  assert after['evidence'][0]['line']<row['first_blocker']['line']
  changes.append(dict(key=key,U0=before,U2=after,previous_selected_failure=row['first_blocker'],correction='Native relocation fails before JNA resource fallback; __errno -> __sF is progression, not an unchanged resource-path root cause.'))
  row.update(cluster_id='N3-jna-symbol',first_blocker=after['evidence'][0],U0_exact_checkpoint_score='miss',U0_first_native_blocker=before['evidence'][0],cause='libjnidispatch relocation now fails at __sF; U0 failed at __errno. JNA resource fallback is secondary. Resolve versioned stdio ABI through N3; resource packaging root cause is not established.')
 # Reproduce the accepted APK style graph read-only; do not execute a script writing the other worktree.
 graph=read(NATIVE/'evidence/vlc-theme-graph.json');apk=Path(graph['apk']);assert sha(apk)==graph['apk_sha256']==evidence['vlc']['apk_sha256']
 text=subprocess.check_output(['/Users/zhaoyue/Library/Android/sdk/build-tools/37.0.0/aapt2','dump','resources',str(apk)],text=True)
 styles={};current=None
 for line in text.splitlines():
  m=re.match(r'    resource (0x[0-9a-f]+) style/(.*)',line)
  if m:current=m[1];styles[current]=dict(name=m[2],parents=set(),defines_attr=False);continue
  if line.startswith('    resource '):current=None
  if current:
   m=re.search(r'parent=style/.* \((0x[0-9a-f]+)\)',line)
   if m:styles[current]['parents'].add(m[1])
   if 'background_default(0x7f040072)=' in line:styles[current]['defines_attr']=True
 actual={}
 for root in ['0x7f1402f9','0x7f140278','0x7f1402ec']:
  todo=[root];seen=set();chain=[]
  while todo:
   x=todo.pop()
   if x in seen:continue
   seen.add(x)
   if x not in styles:continue
   r=styles[x];chain.append(dict(id=x,name=r['name'],defines_attr=r['defines_attr']));todo+=sorted(r['parents'])
  actual[root]=dict(chain=chain,definition_present=any(r['defines_attr'] for r in chain))
 assert {k:v['definition_present'] for k,v in actual.items()}=={'0x7f1402f9':False,'0x7f140278':False,'0x7f1402ec':True}
 assert actual==graph['styles']
 dump('vlc-theme-audit.json',dict(apk=str(apk),apk_sha256=sha(apk),styles=actual,method='Read-only aapt2 dump resources, union of config variants; reproduction of cx-t0 audit_resources.py',upstream_script=str(NATIVE/'audit_resources.py'),upstream_script_sha256=sha(NATIVE/'audit_resources.py'),limit='Active Transparent/Empty theme lacks the app-specific attribute; why the inflater selected that context remains unknown. No OH parser defect demonstrated.'))
 vlc=next(r for r in rows if r['key']=='vlc');vlc.update(layer_confidence='medium',cause='VLC still has libvlc -> libGLESv2 dependency failure and later theme attr 0x7f040072/index13 exception. Actual APK Transparent/Empty ancestors lack that attribute; Onboarding ancestors provide it. Trace context/theme selection before changing native resource projection; root cause unproved. Existing N3 ownership retained for coordination.')
 for c in clusters:
  if c['cluster_id']=='N3-jna-resource':
   c['cluster_id']='N3-jna-symbol';c['notes']=[r['cause'] for r in rows if r['cluster_id']=='N3-jna-symbol']
   for ev in c['evidence']:
    ev['blocker']=next(r['first_blocker'] for r in rows if r['key']==ev['key'])
  if c['cluster_id']=='N3-theme-projection':c['confidence']='medium';c['notes']=[vlc['cause']];c['implementation_status']='investigate-context-selection; no verified native resource repair'
 dump('corrections.json',changes);dump('unlit-42.json',rows);dump('next-clusters.json',clusters)
 with (HERE/'unlit-42.csv').open('w') as f:
  fields=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
 for batch in ['J4','N3']:dump(batch+'.json',[c for c in clusters if c['batch']==batch])
 result=read(OLD/'results.json');w=result['wall_comparison'];w['original_receipt_counts']=dict(hits=w['hits'],misses=w['misses'],unknown=w['unknown'])
 w['hit_keys']=[k for k in w['hit_keys'] if k not in ['firefox','fd-fennec_fdroid']];w['miss_keys']=sorted(w['miss_keys']+['firefox','fd-fennec_fdroid'])
 w.update(hits=len(w['hit_keys']),misses=len(w['miss_keys']),known_first_or_secondary_hits=len(w['hit_keys'])+1,policy='Causal-order correction: JNA fallback text repeats, but the earlier native symbol wall changed from __errno to __sF. Counts are descriptive U0-to-U2 transfer, not exact-profile prospective accuracy.')
 result['addendum_sources']={str(p):sha(p) for p in [OLD/'SHA256SUMS',NATIVE/'evidence/vlc-theme-graph.json',NATIVE/'audit_resources.py',Path(__file__)]}
 result['J3_scope']='Raw runs available, but no outer UI signature in that directory at this receipt; not merged into U2 counts.'
 assert len(rows)==42 and w['hits']==15 and w['misses']==21 and w['unknown']==6
 assert [r['key'] for r in rows]==[r['key'] for r in read(OLD/'unlit-42.json')]
 dump('results.json',result);print('PASS: 42 keys; 2 JNA earlier relocation pairs; VLC APK graph independently reproduced; scores 15/21/6; original U2 receipt unchanged')
if __name__=='__main__':main()
