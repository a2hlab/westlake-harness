#!/usr/bin/env python3
"""Offline descriptive U0 receipt; never changes frozen J1/N1/U1 predictions."""
import csv, datetime, hashlib, json, re, sys
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
PLAN=HERE.parent/'freeze-v1'
ROOT=HERE.parents[2]
SOURCE=ROOT.parent/'westlake-harness/benchmark/2026-09-30-unified-assetfd-5cd-sweep'
sys.path.insert(0,str(HERE.parent/'shard'))
from merge_facts import record_facts,fingerprint
sys.path.insert(0,str(ROOT/'benchmark/2026-09-29-static-wall-prediction'))
import extract_unified_failures as ex
from score_unified_r17r import actual_family,lighting_metric

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,data):(HERE/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def csvout(name,rows):
 with (HERE/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def own(lines,pkg):
 pids={m[1] for l in lines if 'nativeOnScheduleLaunchApplication ENTRY bundle='+pkg+' ' in l and (m:=ex.PID.match(l))}
 return [(n,l) for n,l in enumerate(lines,1) if (m:=ex.PID.match(l)) and m[1] in pids]
def hit(ls,pat):
 return [dict(line=n,text=l) for n,l in ls if re.search(pat,l)]

def main():
 predictions=json.loads((PLAN/'predictions.json').read_text()); plan=json.loads((PLAN/'plan.json').read_text())
 frozen=datetime.datetime.fromisoformat(json.loads((PLAN/'freeze.json').read_text())['frozen_at']).timestamp()
 old=json.loads((ROOT/'benchmark/2026-09-29-static-wall-prediction/unified-r17r-feedback/first-failures.json').read_text())
 old={r['key']:r for r in old}
 # Outer README explicitly supplies the delta against its already signed baseline.
 lit={p['key'] for p in predictions if p['baseline_r17r_lit']};lit.remove('antennapod');lit.add('newpipe')
 assert len(lit)==21 and 'NewPipe' in (SOURCE/'README.md').read_text()
 ex.TERMINAL=re.compile(ex.TERMINAL.pattern+r'|\[W-ROOM-SURVIVE\] UNCAUGHT.*main=true|DFX_SignalHandler :: signo\((?:6|11)\), si_code\([12]\)')
 records={};runs=[];maps=[]
 for run in sorted((SOURCE/'runs').glob('*/*')):
  files=list(run.glob('*/record.json')); fp=run/'runtime-fingerprint.txt'; m=fingerprint(fp);maps.append(m)
  rawfacts=run/'facts.txt'
  if not rawfacts.exists():rawfacts=SOURCE/'evidence/facts-unified-assetfd-5cd-first35.txt'
  runs.append(dict(run=str(run),keys=len(files),fingerprint_sha256=sha(fp),fingerprint=m,facts=str(rawfacts),facts_sha256=sha(rawfacts),facts_text=rawfacts.read_text()))
  for p in files:
   r=json.loads(p.read_text());assert r['key'] not in records;records[r['key']]=(p,r)
 assert set(records)=={p['key'] for p in predictions} and all(m==maps[0] for m in maps)
 required={'/system/android/lib64/liboh_android_runtime.so':'53f00423','/system/android/framework/oh-adapter-runtime.jar':'dd4f0eae','/system/lib64/libbms.z.so':'6aadb8b4','/system/lib64/libapk_installer.so':'7048c7c5'}
 for path,prefix in required.items():assert maps[0][path].startswith(prefix),(path,maps[0].get(path))
 facts=[];rows=[];failures=[];observations={}
 for p in predictions:
  k=p['key'];rp,r=records[k];f=record_facts(rp);facts.append(f);lp=rp.with_name('hilog.txt')
  ls=lp.read_text(errors='replace').splitlines() if lp.exists() else []; ol=own(ls,r['package']);observations[k]=ol
  e=dict(key=k,package=r['package'],lit=k in lit,log=str(lp),log_sha256=sha(lp) if lp.exists() else None,record_error=r.get('error'))
  e.update(ex.select(ls,r['package']) if lp.exists() else dict(stage='prelaunch',anchor=None,chain=[],pids=[]))
  if not lp.exists() and not r.get('error'):e['stage']='interrupted-evidence'
  e['first_terminal']=ex.select(ls,r['package'],False) if lp.exists() else None
  e['supplemental']=hit(ol,r'LoadLibrary failed|\[B8-UEH\] background.*uncaught|\[B8-AMB\] in-process bind failed|DFX_SignalHandler :: signo\((?:6|11)\)|System.exit called|finishActivity: OH TerminateAbility|Shattered Pixel Dungeon failed|Error loading shared library.*libgdx')[:20]
  failures.append(e)
  family=actual_family(e)
  if not lp.exists() and not r.get('error'):family='incomplete-run-evidence'
  if k=='vlc' and hit(ol,r'No implementation found.*AudioSystem.native_getMaxChannelCount'):family='audiosystem-native-gap'
  if k=='antennapod':family='native-renderthread-sigsegv'
  if k=='fd-feeder' and hit(ol,r'No virtual method getNetworkSpecifier'):family='boot-networkrequest-method'
  if k=='ppsspp' and hit(ol,r'LoadLibrary failed.*libGLESv2'):family='app-native-namespace-dependency'
  causes=[x for x in e['chain'] if 'Caused by:' in x['text']];cause=causes[-1] if causes else e['anchor']
  rows.append(dict(key=k,J1=p['J1'],N1=p['N1'],U1=p['U1'],actual_lit=k in lit,baseline_lit=p['baseline_r17r_lit'],cluster_ids=p['cluster_ids'],apk_matches=r.get('apk_sha256')==p['apk_sha256'],clicked_after_freeze=isinstance(r.get('clicked_at'),(int,float)) and r['clicked_at']>frozen,actual_first_family=family,prior_first_family=actual_family(old[k]),first_failure=cause,terminal=(e['first_terminal'] or {}).get('anchor'),record=str(rp),log=str(lp),log_sha256=e['log_sha256'],alive_t5=f['alive_t5'],alive_t20=f['alive_t20'],captured=f['captured']))
 dump('first-failures.json',failures);dump('per-key.json',rows);csvout('per-key.csv',rows);dump('record-facts.json',facts)
 patterns={
 'N01':r'ASSERT FAILED.*EGL_NO_SURFACE', 'N02':r'Error loading shared library.*(?:libandroid|libGLES)|inherits.*fail',
 'N03':r'Error loading shared library.*(?:liblog|libstdc\+\+|libGLES|libOpenSLES)', 'N04':r'Error relocating.*(?:__register_atfork|__FD_SET_chk)',
 'N05':r'(?:UnsatisfiedLinkError|not found).*libjnidispatch', 'N06':r'Landroid/media/SoundPool; failed initialization|SoundPool.<clinit>',
 'N07':r'No implementation found.*GLImpl._nativeClassInit', 'N08':r'WebViewFactory.getProvider', 'N09':r'without a color space',
 'J01':r'CameraX is not configured|Failed to resolve SessionToken', 'J02':r'You need to use a Theme.AppCompat|Failed to resolve attribute',
 'J03':r'NullPointerException.*getApplicationRestrictions','J04':r'SystemVibrator.getInfo', 'J05':r'No implementation found.*AudioProductStrategy',
 'J06':r'NoSuchFieldError.*EXTERNAL_CONTENT_URI','J07':r'(?:Exception|Error).*DSN|Failed to initialize Sentry',
 'B01':r'NoSuchMethodError.*setProperty','B02':r'NoSuchFieldError.*EXTERNAL_CONTENT_URI','B03':r'NoSuchMethodError.*getLinkUpstreamBandwidthKbps',
 'A01':r'maxSizeBytes must be','A02':r'VerifyError.*A2.b|Verifier rejected class A2.b','A03':r'NullPointerException.*getClass',
 }
 bykey={r['key']:r for r in rows};clusters=[];members=[]
 for c in plan['clusters']:
  cid=c['cluster_id']; rr=[]
  for k in c['beneficiary_keys']:
   ev=hit(observations[k],patterns[cid])[:3] if cid in patterns else []
   status='unknown';note='No positive checkpoint proof; absence of the prior exception is not passage.'
   if ev:status='still-blocked';note='Target API failure still observed in app PID; may be secondary to an earlier wall.'
   if cid.startswith('KEEP'):
    if bykey[k]['actual_lit']:status='passed';note='Outer-signed retained/new own-content screen.'
    elif cid=='KEEP01' and k=='fd-uhabits':
     status='passed-new-first-wall';ev=hit(observations[k],r'ASSERT FAILED.*EGL_NO_SURFACE')[:1];note='Asset FD exception no longer blocks main; later rendering reached and EGL assertion terminates. Background widget NPE also observed.'
    elif k=='antennapod':status='new-first-wall';ev=hit(observations[k],r'DFX_SignalHandler :: signo\(11\).*si_code\(1\)')[:1];note='RenderThread SIGSEGV; native root cause unknown, repeat before attribution.'
   if cid.startswith('INPUT'):
    status='still-blocked' if not records[k][1].get('clicked') else 'unknown';note=records[k][1].get('error') or 'Input gate not repeated.'
   if cid=='A05':
    pats={'fd-feeder':r'No virtual method getNetworkSpecifier','ppsspp':r'LoadLibrary failed|System.exit called','termux':r'finishActivity: OH TerminateAbility','fd-mobile':r'\[T=8000ms\].*mDrewOnceForSync=true'}
    ev=hit(observations[k],pats[k])[:2]
    if k in ['fd-feeder','ppsspp'] and ev:status='still-blocked';note='Addendum diagnosis repeated; boot for Feeder, native namespace for PPSSPP.'
    elif k=='termux':status='unknown';note='Activity finishes; reason remains unknown.'
    elif k=='fd-mobile':status='unknown';note='Old background Asset FD throw absent, rendering reached; no positive background job completion proof and outer does not count lit.'
   if cid=='A04':note='No target startup fatal selected; authentication/worker hang remains unproven.'
   if cid=='N07':note='Own error Activity is not game content. Launcher still throws GLImpl ULE; earlier libgdx/libstdc++ load failure also observed.'
   item=dict(cluster_id=cid,key=k,layer=c['layer'],lane=c['lane'],status=status,note=note,evidence=ev,log=bykey[k]['log'],actual_first_family=bykey[k]['actual_first_family'],actual_lit=bykey[k]['actual_lit'])
   rr.append(item);members.append(item)
  clusters.append(dict(cluster_id=cid,cluster=c['cluster'],layer=c['layer'],lane=c['lane'],checkpoint=c['pass_checkpoint'],status_counts=dict(Counter(x['status'] for x in rr)),members=rr))
 dump('clusters.json',clusters);csvout('cluster-members.csv',members)
 followups=[]
 for key,lane,kind,pattern,note in [
  ('newpipe','J1','post-light-functionality',r'\[B8-AMB\] in-process bind failed.*PlayerService','PlayerService in-process bind fails with InvocationTargetException. Inner cause is not logged; playback not exercised, not a first-screen blocker.'),
  ('fd-shatteredpixeldungeon','N1','additional-prerequisite',r'Error loading shared library libstdc\+\+.*libgdx|J_invokeStaticMain_main_threw.*GLImpl|text=.Shattered Pixel Dungeon failed','libgdx dependency fails before GLImpl fatal; second PID renders error Activity. Pair N03-style libstdc++ visibility with N07 GLES JNI; no claim of gameplay progress.'),
  ('antennapod','N1','new-first-wall',r'DFX_SignalHandler :: signo\(11\).*si_code\(1\)|threadName\(RenderThread\)','RenderThread native SIGSEGV, stack/root cause unknown. Repeat three times before attributing to asset-fd.'),
  ('vlc','N1 + J1','new-first-wall-plus-retained-wall',r'UNCAUGHT.*AudioSystem.native_getMaxChannelCount|Caused by:.*Failed to resolve attribute','AudioSystem JNI precedes old theme attribute #13 on a later PID. Native plus JAR closure is required.'),
  ('fd-uhabits','N1 + J1','passed-new-first-wall',r'ASSERT FAILED.*EGL_NO_SURFACE|Caused by:.*AppWidgetManager.getAppWidgetIds','Asset FD main path advances into EGL recreation fatal. Widget null exception is background/tolerated; it must not replace the fatal wall.'),
  ('fd-mobile','N1','observation-boundary',r'\[T=8000ms\].*mDrewOnceForSync=true','Old background asset FD exception absent; job completion and usable UI not established.'),
 ]:
  followups.append(dict(key=key,lane=lane,kind=kind,note=note,log=bykey[key]['log'],log_sha256=bykey[key]['log_sha256'],evidence=hit(observations[key],pattern)[:8]))
 dump('next-walls.json',followups)
 summary=dict(scope='U0 descriptive checkpoint receipt; NOT J1/N1/U1 exact-profile accuracy',keys=len(rows),runs=runs,all_four_fingerprint_maps_equal=True,profile=plan['profiles']['U0'],prediction_freeze_sha256=sha(PLAN/'freeze.json'),outer_verdict_source=str(SOURCE/'README.md'),outer_verdict_sha256=sha(SOURCE/'README.md'),lit_keys=sorted(lit),lit=21,new_lit=['newpipe'],lost_lit=['antennapod'],apk_mismatch=[r['key'] for r in rows if not r['apk_matches']],finished_records=sum(f['finished'] for f in facts),incomplete_keys=[f['key'] for f in facts if not f['finished']],clicked_records=sum(bool(r.get('clicked')) for _,r in records.values()),clicked_after_freeze=sum(r['clicked_after_freeze'] for r in rows),captured=sum(f['captured'] for f in facts),captured_unknown=sum(f['captured'] is None for f in facts),alive={t:dict(yes=sum(f['alive_'+t] is True for f in facts),no=sum(f['alive_'+t] is False for f in facts),unknown=sum(f['alive_'+t] is None for f in facts)) for t in ['t5','t20']},descriptive_frozen_lighting={col:lighting_metric(rows,col) for col in ['J1','N1','U1']},cluster_membership_status_counts=dict(Counter(r['status'] for r in members)))
 baseline_lit={p['key'] for p in predictions if p['baseline_r17r_lit']}
 summary['baseline_retention']=dict(retained=len(lit & baseline_lit),previous_lit=len(baseline_lit),new_lit=len(lit-baseline_lit))
 summary['scoring_boundary']='J1/N1/U1 are absent. Lighting retrieval below is descriptive only, not repair acceptance or prospective accuracy. 66 records include one interrupted LibreTube entry and three input-gated entries.'
 summary['source_scripts']={str(f):sha(f) for f in [Path(__file__),Path(ex.__file__),HERE.parent/'shard/merge_facts.py',PLAN/'predictions.json',PLAN/'plan.json']}
 dump('results.json',summary)
 print(json.dumps({k:v for k,v in summary.items() if k not in ['runs','descriptive_frozen_lighting','lit_keys']},ensure_ascii=False,indent=2))
 for r in rows:
  if not r['actual_lit']:print(r['key'],r['actual_first_family'],str(r['first_failure'])[:260])
if __name__=='__main__':main()
