#!/usr/bin/env python3
"""Create an immutable prospective table; never consumes rollout results."""
import argparse,collections,csv,datetime,hashlib,json,shutil,sys
from pathlib import Path
from detector import HERE,CALIBRATION,classify
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
POLICY={
 'intervention':'Installed synthetic HAP actually declares AND is granted START_ABILITIES_FROM_BACKGROUND; new installer alone is not enough without reinstall/grant verification.',
 'runtime_condition':'Same runtime/launcher/app data state as baseline; Gallery/VLC screen prediction assumes CE runtime 9e14 is present. Any simultaneous JAR/native/launcher-selection change is a separate confounded stratum.',
 'advance_definition':'A previously permission-blocked transition to the named non-launcher Activity progresses; a callsite alone and an already-scheduled second Activity are not improvement.',
 'page_definition':'Predicted destination Activity own UI is visually identified, including login/welcome/file-browser pages. Desktop, blank window and mere process survival are not success. Wikipedia predicts InitialOnboardingActivity welcome, not stable article/content rendering.',
 'calibration':'gallery/vlc/tusky/binaryeye/filemanager + Wikipedia are disclosed pre-grant positive calibration cases; report their scores separately from unseen keys. Termux is a disclosed negative control.',
 'require_freeze_before_intervention':True,
 'strict_prospective':'Require frozen_at < intervention_at < clicked_at for strict pre-board scoring; exact APK SHA and grant_verified=true required. Missing timestamps/grant/identity remain unknown/ineligible, not misses.',
 'outcomes':'advance_observed=yes/no/unknown and predicted_page_observed=yes/no/unknown are adjudicated fields; page requires screenshot evidence and advance requires transition/log evidence or identified destination UI.',
 'abstentions':'Unknown predictions are abstentions. Report classified accuracy plus coverage and a conservative coverage-adjusted rate; no_static_startup_hit does not mean unaffected.',
 'analysis_limits':'Branch feasibility, callbacks/async/reflection/native navigation, cross-method Intent mutation and first-frame behavior are unresolved. All enabled launcher candidates are scanned; actual BMS launcher must be recorded.',
 'no_post_intervention_reads':'No post-grant rollout logs, records, screenshots or directory listings consumed before this freeze. Prior samples explicitly supplied by outer are calibration inputs.'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--version',required=True);ap.add_argument('--initial',action='store_true');a=ap.parse_args()
 out=HERE/'freezes'/a.version;out.mkdir(parents=True,exist_ok=False)
 src=ROOT/'benchmark/2026-09-28-bms-route-deploy/batch/apps.json';entries=json.loads(src.read_text())['apps'];rows=[];details=[]
 coverage={x['key']:x for x in json.loads((ROOT/'benchmark/2026-09-30-framework-jni-gaps/app-coverage.json').read_text())}
 for e in entries:
  key=e['key'];evidence=HERE/'evidence'/(key+'.json');d=None
  if not a.initial:
   if not evidence.exists():raise ValueError('missing scan '+key)
   d=json.loads(evidence.read_text())
  if d is None:
   status=coverage[key]['status'];pred=classify(key,[],status)
   if key not in CALIBRATION and key!='termux':pred=dict(tier='unknown',expected_advance='unknown',expected_page='unknown',reason='Initial freeze: full DEX scan pending; no forecast promoted from manifest names alone')
   d=dict(key=key,status=status,calls=[],launchers=[],**pred)
  calls=d['calls'];strong=[c for c in calls if c['startup_reachable']=='yes-static' and c['non_launcher_targets']]
  splash=[c for c in calls if c['splash_class']]
  target=sorted({t.replace('/','.') for c in strong+splash for t in c['non_launcher_targets']})
  if key=='wikipedia' and not target:target=['org.wikipedia.onboarding.InitialOnboardingActivity']
  counts=d.get('counts',{})
  hints=sorted({h['class_name'].replace('/','.') for c in strong+splash for h in c.get('activity_class_hints',[]) if h['class_name'] not in d.get('launchers',[])})
  phases=sorted({c.get('root',{}).get('method','unknown') for c in strong+splash})
  row=dict(key=key,apk_sha256=e.get('apk_sha256') or coverage[key].get('apk_sha256',''),package=e['package'],scan_status=d['status'],calibration=key in CALIBRATION,negative_control=key=='termux',tier=d['tier'],expected_advance=d['expected_advance'],expected_page=d['expected_page'],launcher_classes=';'.join(d.get('launchers',[])),nonlauncher_targets=';'.join(target),target_hints_only=';'.join(hints),lifecycle_roots=';'.join(phases),all_start_calls=counts.get('all_start_calls','unknown'),launcher_path_calls=counts.get('launcher_path_calls','unknown'),explicit_nonlauncher_startup=counts.get('explicit_nonlauncher_startup','unknown'),splash_class_calls=counts.get('splash_class_calls','unknown'),manifest_splash_to_main_hint=d.get('manifest_splash_to_main_hint','unknown'),reason=d['reason'],evidence=('../../evidence/'+key+'.json' if not a.initial else 'outer-disclosed calibration; prior app-coverage.json'),evidence_sha256=sha(evidence) if not a.initial else '')
  rows.append(row)
  details.append({'prediction':row,'selected_witnesses':strong+splash,'static_detection_independent_of_calibration':bool(strong)})
 with (out/'predictions.csv').open('w') as f:
  wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
 save(out/'predictions.json',details);save(out/'policy.json',POLICY)
 save(out/'inputs.json',dict(manifest=str(src),manifest_sha256=sha(src),apps=[dict(key=e['key'],apk_sha256=e.get('apk_sha256') or coverage[e['key']].get('apk_sha256'),path=coverage[e['key']].get('apk'),scan_status=coverage[e['key']]['status']) for e in entries],scanner={p.name:sha(p) for p in [HERE/'detector.py',HERE/'scan.py',HERE/'publish.py',HERE/'backtest.py']},prior_coverage_sha256=sha(ROOT/'benchmark/2026-09-30-framework-jni-gaps/app-coverage.json')))
 if not a.initial:
  code=out/'code';code.mkdir()
  for name in ['detector.py','scan.py','publish.py','backtest.py']:shutil.copy2(HERE/name,code/name)
  from detector import OLD
  dependency=out/'dependencies';dependency.mkdir()
  for name in ['scan_reachability.py','scan_apps.py','scan_jni.py','scan_io.py']:shutil.copy2(OLD/name,dependency/name)
 frozen=datetime.datetime.now(datetime.timezone.utc).isoformat()
 receipt=dict(version=a.version,frozen_at=frozen,initial_calibration_only=a.initial,keys=len(rows),counts=dict(collections.Counter(r['tier'] for r in rows)),hashes={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},post_intervention_results_read=False)
 save(out/'freeze.json',receipt)
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
