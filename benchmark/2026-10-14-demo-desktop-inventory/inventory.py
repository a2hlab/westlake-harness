#!/usr/bin/env python3
"""Derive package facts and disabled actions from pinned S and raw receipts, offline only."""
import argparse,collections,hashlib,json,os,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2]))).resolve()
MAIN=WS/'westlake-harness';SERIAL='61b0657200000000000000000324012c';BOOT='086db6c7-a7e7-40ce-a336-9608adc05afc'
PACKAGE=re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+\Z')
PROTECTED={'org.westlake.imehost','com.ss.android.article.news','com.example.helloworld','com.a2hlab.bridge.zigzag'}
def need(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def path(value):
 p=WS/value.removeprefix('$WORKSPACES/') if value.startswith('$WORKSPACES/') else Path(value)
 need(p.is_absolute() and p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(WS),'missing/nonregular source');return p.resolve()
def pin(ref):
 need(isinstance(ref,dict) and re.fullmatch('[0-9a-f]{64}',ref.get('sha256','')),'complete SHA required')
 p=path(ref['path']);need(sha(p)==ref['sha256'],'source SHA drift: '+ref['path']);return p
def ref(p):return {'path':'$WORKSPACES/'+p.resolve().relative_to(WS).as_posix(),'sha256':sha(p)}
def parse_bundles(text):
 lines=text.splitlines();need(lines and lines[0]=='ID: 100:' and len(lines)>1,'strict user100 nonempty BMS list required')
 names=[]
 for line in lines[1:]:
  need(line.startswith('\t') and PACKAGE.fullmatch(line[1:]),'malformed/truncated BMS package line');names.append(line[1:])
 need(len(names)==len(set(names)),'duplicate BMS package');return set(names)
def is_protected(package):return package in PROTECTED or package.startswith(('com.ohos.','ohos.','org.westlake.'))
def disposition(package,group,installed):
 if is_protected(package):return 'protect'
 if group=='excluded':return 'remove' if installed else 'protect'
 if group in ('core','limited','boat'):return 'keep' if installed else 'install'
 return 'unknown'
def click_evidence(record,p,launch_package,ability):
 icon=record.get('selected_icon');clicked=record.get('clicked') is True
 fact={'launch_method':record.get('launch_method'),'clicked':record.get('clicked'),'selected_icon':icon,'kind':'NO_DESKTOP_CLICK_PROVEN','commands':[],'human_hand_tap_proven':False,'current_icon_reverified':False}
 if not clicked or not isinstance(icon,dict):return fact
 expected='AppIconCommonView_'+launch_package+'.'+ability if ability else None
 need(expected and icon.get('id')==expected,'desktop icon package/ability mismatch')
 center=icon.get('center');need(isinstance(center,list) and len(center)==2 and all(type(x) is int for x in center),'icon center unknown')
 prefix=f'uitest uiInput click {center[0]} {center[1]}; '
 for directory in (p.parent/'commands',p.parent.parent/'commands'):
  if not directory.is_dir():continue
  for command in directory.glob('command-*.json'):
   j=read(command);argv=j.get('argv',[])
   if not argv or not argv[-1].startswith(prefix):continue
   if record.get('clicked_at') is None or not 0<=record['clicked_at']-j.get('finished',-100)<=2:continue
   need(argv[-4:-1]==['-t',SERIAL,'shell'] and j.get('exit_code')==0,'desktop click transport/serial failed')
   stdout=command.with_suffix('.stdout.txt');stderr=command.with_suffix('.stderr.txt')
   marker=re.search(r'(__BMS_REMOTE_RC_[0-9a-f]+__)',argv[-1]);need(marker is not None,'click remote status marker missing')
   need(re.search(re.escape(marker[1])+r'0\s*\Z',stdout.read_text()) is not None and stderr.read_bytes()==b'','click remote rc failed/unknown')
   fact['commands'].append({'command':ref(command),'stdout':ref(stdout),'stderr':ref(stderr),'transport_rc':0,'remote_rc':0})
 need(len(fact['commands'])==1,'clicked flag lacks unique real desktop input receipt')
 fact['kind']='ACTUAL_AUTOMATED_DESKTOP_ICON_CLICK_RAW_RC_VERIFIED';return fact
def derive():
 sources=read(HERE/'sources.json');s=read(pin(sources['signed_S']))
 need(s.get('status')=='SIGNED_OUTER_REVIEW' and s.get('actual_reviewer')=='outer(codex)','actual signed S required')
 seal=read(pin(s['source_seal']));need(seal['serial']==SERIAL,'signed seal wrong board')
 demo=s['demo_set'];core=set(demo['core_startup_only_keys']);limited=set(demo['limited_startup_appendix_keys']);excluded={r['key']:r for r in demo['excluded_keys_with_reasons']}
 need(len(core)==109 and len(limited)==6 and len(excluded)==13 and not(core&limited or core&set(excluded) or limited&set(excluded)),'S109/6/13 membership drift')
 boot=pin(sources['boot_stdout']).read_text().strip();need(boot==BOOT,'actual initial boot differs')
 need(read(pin(sources['identity']))['serial']==SERIAL,'initial identity wrong board')
 raw_receipts={}
 for name,cmd in [('boot','cat /proc/sys/kernel/random/boot_id'),('bundles','bm dump -a'),('processes','ps -A -o PID,PPID,UID,NAME'),('window',"hidumper -s WindowManagerService -a '-a'"),('demo-directory',None)]:
  metadata=read(pin(sources[name]));stdout=pin(sources[name+'_stdout']);stderr=pin(sources[name+'_stderr'])
  need(metadata.get('rc')==0 and metadata['argv'][1:4]==['-t',SERIAL,'shell'] and stderr.read_bytes()==b'','initial transport failed: '+name)
  if cmd is not None:need(metadata['argv'][-1]==cmd,'initial raw command differs: '+name)
  raw_receipts[name]={'command':sources[name],'stdout':sources[name+'_stdout'],'stderr':sources[name+'_stderr'],'transport_rc':metadata['rc'],'remote_rc':None,'remote_rc_basis':'initial collector did not separately retain a remote status marker'}
 installed=parse_bundles(pin(sources['bundles_stdout']).read_text())
 recommendations=read(pin(sources['recommendations']));need(len(recommendations['rows'])==128,'128 raw record references missing')
 packages={r['package']:r for r in seal['packages']};rows=[]
 for item in recommendations['rows']:
  key=item['key'];need(key in core|limited|set(excluded),'unknown key outside S')
  record_ref={'path':item['record'],'sha256':item['record_sha256']};p=pin(record_ref);r=read(p)
  need(r['serial']==SERIAL and r['boot_id']==BOOT and r['key']==key,'record board/boot/key differs')
  package=r['package'];expected=packages[package];need(r['apk_sha256']==expected['apk_sha256']==item['apk_sha256'],'signed APK/record drift')
  group='core' if key in core else 'limited' if key in limited else 'excluded'
  ability=r.get('desktop_activity');need(ability==r.get('bms',{}).get('desktop_activity'),'record BMS desktop ability mismatch')
  rows.append({'key':key,'package':package,'group':group,'disposition':disposition(package,group,package in installed),'installed_name_observed':package in installed,'expected_desktop_ability':ability,'ability_basis':'original sameboot BMS record; not fresh per-package dump','source_apk':r.get('input_apk'),'source_apk_sha256':r['apk_sha256'],'expected_installed_apk_path':expected['apk_path'],'expected_installed_apk_sha256':expected['apk_sha256'],'current_apk_sha256':None,'current_ability':None,'record':record_ref,'raw_record_status':r['status'],'desktop_click':click_evidence(r,p,package,ability),'scope':'startup only' if group!='excluded' else 'excluded from demonstration','scope_note':item['reason'],'excluded_verdict':excluded.get(key,{}).get('verdict'),'device_reverification':'PENDING; package list presence is not current APK/icon/UI proof'})
 need(len({r['key'] for r in rows})==len({r['package'] for r in rows})==128,'key/package aliases collide')
 boat_ref=s['evidence']['boat_partial'];boat_p=pin(boat_ref);boat=read(boat_p);bp='com.Unity3d.BoatAttackDay';be=packages[bp]
 rows.append({'key':'boatattack','package':bp,'group':'boat','disposition':disposition(bp,'boat',bp in installed),'installed_name_observed':bp in installed,'expected_desktop_ability':'com.unity3d.player.UnityPlayerActivity','ability_basis':'original clicked exact desktop icon','source_apk':None,'source_apk_sha256':be['apk_sha256'],'expected_installed_apk_path':be['apk_path'],'expected_installed_apk_sha256':be['apk_sha256'],'current_apk_sha256':None,'current_ability':None,'record':boat_ref,'desktop_click':click_evidence(boat,boat_p,bp,'com.unity3d.player.UnityPlayerActivity'),'interaction_review':s['evidence']['boat_review'],'scope':'signed steering/movement/reset/LAP0-to1 only; no completed race','device_reverification':'PENDING'})
 tt_review=read(pin(s['evidence']['toutiao_review']));initial=tt_review['evidence'][0];tt_ref={'path':'$WORKSPACES/westlake-harness/'+initial['record'],'sha256':initial['record_sha256']};tt_p=pin(tt_ref);tt=read(tt_p)
 tt_files={k:v for group in seal['files'].values() for k,v in group.items() if k.endswith('/toutiao.apk')};need(len(tt_files)==1,'unique signed RouteB Toutiao APK required');tt_apk,tt_sha=next(iter(tt_files.items()))
 rows.append({'key':'toutiao-route-b','package':'com.ss.android.article.news','launch_package':'org.westlake.imehost','group':'toutiao','disposition':'protect','installed_name_observed':'com.ss.android.article.news' in installed,'expected_desktop_ability':'EntryAbility','ability_basis':'RouteB host icon only; no direct com.ss Android icon claim','source_apk':None,'source_apk_sha256':tt_sha,'expected_installed_apk_path':tt_apk,'expected_installed_apk_sha256':tt_sha,'archive_role':'signed RouteB embedded APK; not evidence of current BMS APK bytes','current_apk_sha256':None,'current_ability':None,'record':tt_ref,'desktop_click':click_evidence(tt,tt_p,'org.westlake.imehost','EntryAbility'),'interaction_review':s['evidence']['toutiao_review'],'scope':'signed feed/article/back/changed-feed with original SIG11/clipping/gray-image limits','device_reverification':'PENDING'})
 known={r['package'] for r in rows};other=[]
 for package in sorted(installed-known):
  protected=is_protected(package)
  other.append({'package':package,'package_class':'protected_system_or_host_or_control' if protected else 'unknown','disposition':'protect' if protected else 'unknown','delete_allowed':False,'identification_basis':'explicit safety allowlist/prefix; no APK type inferred' if protected else 'name only; source APK/type not identified','current_apk_sha256':None})
 manifest={'schema':'demo-desktop-inventory/v1','serial':SERIAL,'observed_boot':boot,'sources':sources,'signed_seal':s['source_seal'],'raw_initial':raw_receipts,'signed_key_counts':{'core':109,'limited':6,'excluded':13,'special':2},'installed_unique_packages':len(installed),'apps':rows,'other_installed_packages':other,'protected_paths':['/system','/vendor','/data/app/el1/bundle/public/org.westlake.imehost','/data/app/el2/100/base/org.westlake.imehost','/data/app/el2/100/base/com.ss.android.article.news','/data/local/tmp/asx','/data/westlake-demo'],'metadata_currentness':'initial-readonly-r2 package-name snapshot only; no current per-package APK/ability/hash proof','device_calls':0}
 actions={'schema':'demo-desktop-actions/v1','execution_enabled':False,'serial':SERIAL,'boot_id':boot,'install':[],'keep':[],'remove':[],'protect':[],'unknown_no_action':other and [r for r in other if r['disposition']=='unknown'] or [],'guards':['fresh sameboard boot/held-owner/current complete user100 list before writes','no system/host/runtime/Toutiao-data mutation','unknown packages never deleted','remove only named S excluded corpus packages after fresh actualAPK SHA equals signed expected','no aa/manual launch as desktop-click evidence','installation set changes are separate from immutable V2 130-package fingerprint'],'executed':False}
 for r in rows:actions[r['disposition']].append({'key':r['key'],'package':r['package'],'expected_apk_sha256':r['expected_installed_apk_sha256'],'why':r['group'],'requires_fresh_package_verification':True})
 actions['protect'].extend(r for r in other if r['disposition']=='protect')
 validate(manifest,actions)
 clicks=collections.Counter(r['desktop_click']['kind'] for r in rows[:128]);results={'status':'OFFLINE_INVENTORY_COMPLETE_PENDING_HUMAN_REVIEW_AND_DEVICE_REVERIFICATION','serial':SERIAL,'boot_id':boot,'installed_unique_packages':len(installed),'signed_core':109,'signed_limited':6,'signed_excluded':13,'specials':2,'missing_approved_packages':[r['package'] for r in rows if r['group']!='excluded' and not r['installed_name_observed']],'ordinary_desktop_click_facts':dict(clicks),'ordinary_ability_fallbacks':[{'key':r['key'],'package':r['package'],'ability':r['expected_desktop_ability']} for r in rows[:128] if r['desktop_click']['kind']=='NO_DESKTOP_CLICK_PROVEN'],'action_counts':{k:len(actions[k]) for k in ('install','keep','remove','protect','unknown_no_action')},'current_APK_hash_reverification':None,'current_icon_reverification':None,'current_UI_reverification':None,'device_calls':0,'raw_initial_remote_rc_not_separately_recorded':True,'V2_frozen_modified':False,'actions_executed':False,'human_signoff':False}
 return manifest,actions,results
def validate(m,a):
 need(a['execution_enabled'] is False and a['executed'] is False,'actions must remain disabled')
 rows=m['apps'];need(len(rows)==130 and len({r['key'] for r in rows})==130 and len({r['package'] for r in rows})==130,'signed membership/unique package failed')
 seen={}
 for category in ('install','keep','remove','protect'):
  for r in a[category]:need(r['package'] not in seen,'overlapping disposition');seen[r['package']]=category
 need(all(seen.get(r['package'])==r['disposition'] for r in rows),'signed package lacks exactly one disposition')
 for r in a['remove']:
  match=[x for x in rows if x['package']==r['package']];need(len(match)==1 and match[0]['group']=='excluded' and not is_protected(r['package']),'destructive action targets unknown/protected/demo package')
 need(not(set(x['package'] for x in a['unknown_no_action'])&set(seen)),'unknown overlaps action list')
 return True
def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['build','check']);args=p.parse_args();generated=derive()
 for name,obj in zip(['manifest.json','actions.disabled.json','results.json'],generated):
  target=HERE/name
  if args.command=='build':need(not target.exists(),'fresh inventory output required');target.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
  else:need(read(target)==obj,'inventory derived data drift: '+name)
 if args.command=='check':
  import unittest,test_inventory
  result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(test_inventory));need(result.wasSuccessful(),'inventory negative controls failed')
 print(json.dumps(generated[2],ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
