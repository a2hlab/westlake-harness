#!/usr/bin/env python3
"""Post-freeze evidence packaging for the two outer-adjudicated 5ea runs."""
import argparse,csv,datetime,hashlib,json,re,shutil
from pathlib import Path
from backtest import verify_freeze,score

HERE=Path(__file__).resolve().parent
ADJUDICATION={
 'fd-filemanager':('yes','yes','Target MainActivity UI accepted by outer; no main-thread fatal found in this capture.'),
 'fd-binaryeye':('yes','no','CameraActivity resume throws CameraX configuration exception after successful dispatch; camera initialization blocks even the page.'),
 'fd-gallery':('yes','no','MainActivity throws NoSuchFieldError for MediaStore.Images.Media.EXTERNAL_CONTENT_URI after successful dispatch.'),
 'fd-tusky':('no','no','OpenSSLProvider class unavailable; Sun-provider failure and kk.e initializer failure before any captured target StartAbility.'),
 'vlc':('yes','no','Onboarding dispatch succeeds before process exit; AudioSystem.native_getMaxChannelCount ULE and later fatal coroutine/provider initializer failure are distinct observed errors.'),
 'anki':('yes','no','New IntentHandler dispatches DeckPicker; second process throws lateinit instance initialization error. Earlier librsdroid dlopen cannot resolve liblog. v0 abstained; launcher changed, so permission-only causality is unproven.'),
 'wikipedia':('unknown','unknown','Explicitly excluded by outer: r17g provider class-loader regression blocks BC SecureRandom before forecast Activity transition.')}
PATTERN=re.compile(r'OH_AbilityMgrClient:.*(?:StartAbility: bundle|StartAbility returned)|canStartAbilityFromBackground:1|J_invokeStaticMain_main_threw|Caused by:|failed initialization:.*UnsatisfiedLinkError|FATAL EXCEPTION|background.*(?:denied|not allowed)',re.I)
def save(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def iso(t):return datetime.datetime.fromtimestamp(t,datetime.timezone(datetime.timedelta(hours=8))).isoformat()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 receipt=verify_freeze(HERE/'freezes/v0');preds=[x['prediction'] for x in json.loads((HERE/'freezes/v0/predictions.json').read_text())];by={x['key']:x for x in preds}
 records=sorted(a.source.glob('bglaunch-apps*/*/*/record.json'));assert len(records)==7
 observations=[];exclusions=[];rows=[];sources=[]
 for record in records:
  raw=json.loads(record.read_text());key=raw['key'];assert raw['apk_sha256']==by[key]['apk_sha256'];app=record.parent;board=app.parent
  dest=a.out/'evidence'/key;dest.mkdir(parents=True)
  used=[record,app/'bundle.txt',app/'hilog.txt',board/'runtime-fingerprint.txt']
  for name in ('record.json','processes-t5.txt','processes-t20.txt'):
   shutil.copy2(app/name,dest/name)
   if name!='record.json':used.append(app/name)
  fingerprint=(board/'runtime-fingerprint.txt').read_text();shutil.copy2(board/'runtime-fingerprint.txt',dest/'runtime-fingerprint.txt')
  jar=next(l.split()[0] for l in fingerprint.splitlines() if l.endswith('/oh-adapter-runtime.jar'))
  runtime=next(l.split()[0] for l in fingerprint.splitlines() if l.endswith('/liboh_android_runtime.so'))
  installs=[]
  for command in sorted((board/'commands').glob('*.json')):
   data=json.loads(command.read_text());command_text=' '.join(data.get('argv',[]))
   if 'bm install -p ' in command_text and '/'+key+'/original.apk' in command_text:installs.append((command,data))
  assert len(installs)==1 and installs[0][1]['exit_code']==0 and raw['install']['return_code']==0
  command,install=installs[0];used.append(command);shutil.copy2(command,dest/'install-command.json')
  bundle_text=(app/'bundle.txt').read_text();bundle=json.loads(bundle_text[bundle_text.index('{'):])
  grant_index=bundle['reqPermissions'].index('ohos.permission.START_ABILITIES_FROM_BACKGROUND')
  grant_state=bundle['reqPermissionStates'][grant_index];assert grant_state==0
  grant_lines=[{'line':n,'text':l} for n,l in enumerate(bundle_text.splitlines(),1) if 'START_ABILITIES_FROM_BACKGROUND' in l]
  save(dest/'grant.json',{'declared':True,'reqPermissionState':grant_state,'outer_confirms_granted':True,'source':str(app/'bundle.txt'),'lines':grant_lines})
  lines=(app/'hilog.txt').read_text(errors='replace').splitlines();hits=[i for i,l in enumerate(lines) if PATTERN.search(l)]
  keep=sorted({n for i in hits for n in range(max(0,i-1),min(len(lines),i+4))})
  (dest/'hilog-excerpts.txt').write_text('Source: '+str(app/'hilog.txt')+'\n'+''.join(str(i+1)+': '+lines[i]+'\n' for i in keep))
  transition=[i+1 for i,l in enumerate(lines) if 'OH_AbilityMgrClient:' in l and 'StartAbility returned 0' in l]
  advanced,page,reason=ADJUDICATION[key]
  if advanced=='yes':assert transition
  if key=='fd-tusky':assert not transition
  process={}
  for stage in ('t5','t20'):
   ps=(app/('processes-'+stage+'.txt')).read_text().splitlines();uid=str(raw['bms']['uid']);matches=[];helpers=[]
   for lineno,line in enumerate(ps,1):
    fields=line.split()
    if len(fields)>=4 and fields[2]==uid:
     entry={'line':lineno,'pid':int(fields[0]),'ppid':int(fields[1]),'uid':int(uid),'name':fields[3]}
     (matches if fields[3]=='appspawn-x' or fields[3]==raw['package'] else helpers).append(entry)
   process[stage]={'target_processes':matches,'same_uid_helpers':helpers,'alive_app':bool(matches)}
  screenshots=[]
  for shot in raw['screenshots']:
   if shot.get('captured') is not True:continue
   original=Path(shot['path']);assert original.exists() and sha(original)==shot['sha256'];used.append(original);shutil.copy2(original,dest/original.name)
   screenshots.append({'file':str((dest/original.name).relative_to(a.out)),'sha256':shot['sha256'],'captured':True,'scheduled_seconds':shot['scheduled_seconds']})
  save(dest/'counts.json',{'processes':process,'screenshots':screenshots})
  observation=dict(key=key,apk_sha256=raw['apk_sha256'],grant_verified=True,grant_evidence=str((dest/'grant.json').relative_to(a.out)),intervention_at=iso(install['finished']),intervention_time_semantics='successful per-app reinstall completion; grant effective no later than this return',clicked_at=iso(raw['clicked_at']),board_serial=raw['serial'],runtime_fingerprint=sha(board/'runtime-fingerprint.txt'),runtime_jar_sha256=jar,runtime_native_sha256=runtime,actual_launcher=raw['bms']['desktop_activity'],comparable_profile=False,profile_reason='r17g JAR/native profile differs from calibration; new launcher selection also affects Anki. Descriptive outcome scoring only.',advance_observed=advanced,predicted_page_observed=page,transition_evidence=str((dest/'hilog-excerpts.txt').relative_to(a.out)),screenshot_evidence=str((dest/'t20.jpeg').relative_to(a.out)),notes=reason)
  if key=='wikipedia':exclusions.append({'observation':observation,'reason':reason,'authority':'Explicit outer/user instruction after freeze; not a forecast revision.'})
  else:observations.append(observation)
  rows.append(dict(key=key,calibration=by[key]['calibration'],clicked_at=observation['clicked_at'],post_v0=raw['clicked_at']>datetime.datetime.fromisoformat(receipt['frozen_at']).timestamp(),excluded=key=='wikipedia',expected_advance=by[key]['expected_advance'],advance_observed=advanced,expected_page=by[key]['expected_page'],page_observed=page,captured=len(screenshots),t5_alive=process['t5']['alive_app'],t20_alive=process['t20']['alive_app'],t5_target_processes=len(process['t5']['target_processes']),t20_target_processes=len(process['t20']['target_processes']),reason=reason,evidence=str(dest.relative_to(a.out))))
  for path in used:sources.append({'path':str(path),'sha256':sha(path)})
 save(a.out/'observations.json',observations);save(a.out/'excluded.json',exclusions);save(a.out/'source-hashes.json',sources)
 result=score(preds,observations,receipt['frozen_at'],require_pre_intervention=False)
 result.update(freeze_sha256=sha(HERE/'freezes/v0/freeze.json'),observation_sha256=sha(a.out/'observations.json'),timing_scope='pre-click-only-initial-policy',selected_runs=['bglaunch-apps','bglaunch-apps2'],explicit_exclusions=exclusions,raw_counts={'apps':len(rows),'captured':sum(r['captured'] for r in rows),'t5_alive_apps':sum(r['t5_alive'] for r in rows),'t20_alive_apps':sum(r['t20_alive'] for r in rows),'t5_target_processes':sum(r['t5_target_processes'] for r in rows),'t20_target_processes':sum(r['t20_target_processes'] for r in rows)})
 save(a.out/'results.json',result)
 with (a.out/'backtest.csv').open('w') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 print(json.dumps({'metrics':result['metrics'],'raw_counts':result['raw_counts']},indent=2))
if __name__=='__main__':main()
