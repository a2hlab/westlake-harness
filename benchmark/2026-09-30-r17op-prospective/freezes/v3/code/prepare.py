#!/usr/bin/env python3
"""Only prior accepted evidence and pinned code inputs; no future run reads."""
import collections,csv,hashlib,json,shutil,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=Path('/Users/zhaoyue/orca/workspaces')
V2=R/'benchmark/2026-09-30-v3c-r17j-prospective';FB=R/'benchmark/2026-09-30-v2-scanner-feedback';SRC=W/'westlake-harness-walls'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def copy(p,target):target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
def main():
 if (H/'freezes/v3').exists():raise ValueError('v3 already frozen')
 e=H/'evidence';e.mkdir(exist_ok=True)
 # Stop board evidence at the already-read boundary; do not ingest later candidate outcomes.
 board=W/'westlake-harness/.octos/boards/app-lighting.md';lines=board.read_text(errors="replace").splitlines();end=next(i for i,l in enumerate(lines) if '**累计稳定点亮 18 个**' in l)+1
 selected=[{'line':i+1,'text':l} for i,l in enumerate(lines[:end]) if any(t in l for t in ['r17o','r17p','累计稳定点亮 18']) and i>2250]
 save(e/'prior-board-exposure.json',{'path':str(board),'through_line':end,'r17p_outcomes_read':False,'rows':selected})
 profiles={};source_hashes={}
 for version,prefix in [('r17o','cd06eecf'),('r17p','a0ed5c4f')]:
  jar=W/f'vm-copies/{version}-{prefix}/oh-adapter-runtime.jar';receipt=SRC/f'benchmark/2026-09-29-bms-link-entry-walls/build-result-{version}.json';build=load(receipt)
  assert sha(jar)==build['output_sha256'];copy(receipt,e/f'build-result-{version}.json');source_hashes[version]=build['sources']
  profiles[version]={**load(V2/'freezes/v2/profile.json'),'jar_sha256':sha(jar),'boards':['5ea34a4500000000000000001123012c'],'require_runtime_audit':True,
    'native_overrides':{'/system/android/lib64/libhwui.so':'a578b94933cfac4a8fa79116abf145435248df7bce315b9c8eedf41eccb793c6'},'source_commit_r17j':None,
    'excludes':['next2/next3 native packages','AudioSystem/ANL later overrides','any JAR other than the exact selected variant'],
    'variant':version,'jar_path':str(jar)}
 for name in ['B7BindFixes.java','WindowSessionProxy.java','SystemServiceFetcherStubs.java']:
  rel='bms/src/adapter/framework/activity/java/'+name;p=SRC/rel
  assert sha(p)==source_hashes['r17p'][rel];copy(p,e/name)
 # The receipt is the r17o source digest authority; retrieve matching committed text when possible.
 rel='bms/src/adapter/framework/activity/java/WindowSessionProxy.java';expected=source_hashes['r17o'][rel]
 commits=subprocess.check_output(['git','-C',str(SRC),'log','-12','--format=%H','--',rel],text=True).splitlines()
 for commit in commits:
  raw=subprocess.check_output(['git','-C',str(SRC),'show',commit+':'+rel])
  if hashlib.sha256(raw).hexdigest()==expected:(e/'WindowSessionProxy-r17o.java').write_bytes(raw);save(e/'source-commit.json',{'r17o_window_commit':commit});break
 copy(V2/'freezes/v2/evidence/v3c-package.json',e/'v3c-package.json')
 assert sha(e/'v3c-package.json')==profiles['r17o']['package_sha256']
 for name in ['matrix.json','calibration.json','results.json','SHA256SUMS']:copy(FB/name,e/('b10-'+name))
 for name in ['results.json','observations.json']:copy(V2/'backtests/v2-5ea'/name,e/('v2-'+name))
 # Compact primary selected-run line evidence, already exposed during the accepted v2 analysis.
 copy(FB/'evidence/later-egl-experiment.json',e/'prior-egl-experiment.json')
 prior=load(V2/'freezes/v2/predictions.json');observed={x['key']:x for x in load(e/'v2-results.json')['rows']};obs={x['key']:x for x in load(e/'v2-observations.json')};cal={x['key']:x for x in load(FB/'calibration.json')};matrix=load(FB/'matrix.json')
 rows=[]
 exposed={'fd-droidify','newpipe','wikipedia','fd-catima','noice','fd-AppManager','fd-calendar','antennapod','fd-auxio','fd-tusky','fd-netguard','fd-reader','fd-tasks','fd-k9'}
 # Explicit bounded hypotheses, not promises inferred from API/reference counts.
 changes={
 'wikipedia':('不变','推进','EGL_NO_SURFACE on onboarding window','A nonzero EGLSurface for the onboarding window remains usable through a subsequent relayout; positive surface/buffer evidence required','r17o targeted baseline still aborts; r17p drops delegate resized. Native lifetime repair remains unproven.'),
 'newpipe':('不变','推进','EGL failure after provider wall cleared','MainActivity obtains a usable nonzero window surface after provider initialization; positive surface evidence required','r17o targeted run clears provider and reaches EGL; wrapper may clear this next wall but UI not established.'),
 'antennapod':('不变','推进','EGL failure after provider wall cleared','MainActivity reaches a usable nonzero EGL surface after provider initialization','Prior r17o batch reports EGL after provider fix; wrapper targets this trigger, later feed/service failure remains possible.'),
 'fd-AppManager':('不变','亮','successful surface but blank first frame','Own AppManager verification or main content captured','r17o surface exists but page is blank; r17p wrapper may prevent first-frame churn. Low-confidence visual hypothesis.'),
 'noice':('不变','亮','EGL_NO_SURFACE after intro transition','Own Noice intro or sound page captured','Prior own UI exists in earlier generations; r17o still aborts. r17p wrapper is a runtime-only repair hypothesis.'),
 'fd-noice':('不变','亮','EGL_NO_SURFACE after intro transition','Own Noice intro or sound page captured','v2 log proves EGL failure; shared runtime wrapper may restore earlier own UI, not established by static EGL detection.'),
 'fd-k9':('unknown','亮','r17j database page versus r17o blank page','Own database upgrade or mail page captured','Conflicting prior visual states: installer-selected UpgradeDatabaseActivity is not a proved secondary launch. r17p may remove frame churn; no r17p result read.'),
 'fd-droidify':('亮','亮','provider lookup during MainActivity initialization','Own Droid-ify page captured','r17o targeted own UI signed on 5ea/61b; retain it under p with disclosed wrapper regression risk.'),
 'fd-calendar':('亮','亮','JobScheduler manager lookup null','Own calendar month page captured','r17o prior 61b Calendar UI signed; class-to-service mapping repair inherited in both variants, board/profile transfer remains a forecast.'),
 'fd-tasks':('亮','亮','AndroidKeyStore unavailable','Own Tasks welcome/account page captured','r17o prior 61b Tasks own UI signed; software keystore inherited in both variants.'),
 'fd-tusky':('推进','推进','Conscrypt resource JAR verification during provider setup','Tusky MainActivity.onCreate proceeds beyond the former provider initializer to window creation or a later distinct stage','r17o prior Tusky survives with a blank page; provider first wall expected cleared. EGL wrapper alone does not establish login UI.'),
 'fd-com-amaze-filemanager':('推进','推进','SunProviderHolder/AppConfig initialization','AppConfig or Activity initialization reaches a distinct stage after JAR verification','Boot BC rewrite addresses observed provider failure; FileObserver/storage/theme successors still unproven.'),
 'fd-im-vector-app':('推进','推进','SunProviderHolder during startup','Application/Activity initialization passes JAR verification and reaches a distinct subsequent stage','Observed v2 provider failure plus B10 startup witness; native Realm namespace still a possible next wall.'),
 'fd-reader':('推进','推进','MainDispatcherLoader provider initialization','MainDispatcher initialization passes JAR verification and reaches subsequent Activity/service initialization','Provider rewrite targets v2 fatal chain; r17o targeted no-child evidence does not prove the next checkpoint.'),
 'fd-uhabits':('推进','推进','provider initialization before asset path','Initialization passes the provider failure and reaches a distinct subsequent stage, such as the asset operation','Provider use is a latent B10 requirement; observed v2 fatal supplies the wall. AssetManager implementation remains a successor risk.'),
 'fd-shatteredpixeldungeon':('不变','不变','GLImpl JNI missing after EGLImpl was passed','GLImpl required JNI call succeeds and reaches a later render stage','Both JAR changes leave the observed successor JNI gap untouched; no new native gapfill in profile.'),
 'termux':('不变','unknown','degenerate first frame','Nonzero usable content frame is submitted after layout','r17o does not repair the known layout behavior; r17p suppresses callbacks and preserves separate recovery, effect uncertain.'),
 'fd-mobile':('unknown','unknown','1200x1920 frame but black content','Nonblack own content captured or a distinct positive rendering checkpoint','No proved first fatal or redundant-window cause; size alone is not a page.'),
 'fd-seal':('不变','不变','batch rejects non-ELF libaria2c.zip.so','Install preflight completes and desktop launch occurs','No batch/installer change in this profile repairs this prior prelaunch rejection; track separately from clicked-app score.'),
 'toutiao':('不变','不变','batch rejects non-AArch64 libcvt.so','Install preflight completes and desktop launch occurs','No batch/installer change specified; prelaunch rejection remains separate from clicked-app score.')}
 for p in prior:
  key=p['key'];o=observed[key];v='亮' if o['observed']=='亮' else '不变' if o['observed']=='不变' else 'unknown';wall=p['prior_wall'];checkpoint=p['progress_checkpoint'];reason='Retain the accepted v2 own UI; neither change is evidence of a new blocker.' if v=='亮' else 'No targeted repair for the observed wall in either pinned JAR/native profile.' if v=='不变' else 'Current first-wall/progress evidence is insufficient; static references do not resolve the outcome.'
  a,b,wall,checkpoint,reason=changes.get(key,(v,v,wall,checkpoint,reason))
  if key=='subwaysurfers':a=b='unknown';reason='Pinned APK identity mismatch; no confident prediction or scoring eligibility.'
  for src,dest in [(FB/f'evidence/observed/{key}.json',e/f'prior/{key}.json')]:
   if src.exists():copy(src,dest)
   else:copy(V2/f'backtests/v2-5ea/evidence-continuation-c/{key}.json',dest)
  findings=[r for r in matrix if r['key']==key]
  rows.append({'key':key,'apk_sha256':p['apk_sha256'],'package':p['package'],'r17o':a,'r17p':b,'prior_wall':wall,'progress_checkpoint':checkpoint,
      'reason_r17o':reason,'reason_r17p':reason,'confidence':'low' if a!=b or a in ('推进','unknown') else 'medium',
      'r17o_exposure':'prior-r17o-targeted-board-report' if key in exposed else 'prior-v2-only','r17p_exposure':'no-r17p-outcome-read',
      'b10_static_families':[r['family']+':'+r['status'] for r in findings],'egl_detection':'runtime-only',
      'primary_evidence':f'evidence/prior/{key}.json;evidence/v2-observations.json',
      'patch_evidence':'evidence/B7BindFixes.java:30;333;evidence/SystemServiceFetcherStubs.java;evidence/WindowSessionProxy.java:90;226;261',
      'prior_targeted_evidence':'evidence/prior-board-exposure.json' if key in exposed else '',
      'v2_observed':o['observed'],'v2_eligible':o['eligible']})
 save(H/'predictions.json',rows);save(H/'profiles.json',profiles)
 with (H/'predictions.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in row.items()})
 save(H/'results.json',{'status':'predictions-only; future backtest pending','keys':66,'counts':{v:dict(collections.Counter(r[v] for r in rows)) for v in profiles},'future_full_sweep_results_read':False,'r17p_validation_outcomes_read':False,'r17o_prior_targeted_keys':sorted(exposed)})
 print(json.dumps(load(H/'results.json'),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
