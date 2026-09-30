"""Derive the evidence summary; visual notes record an actual image inspection."""
from pathlib import Path
import json,hashlib,re,subprocess
r=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
census=json.loads((r/'census.json').read_text());trials={}
for key in ['wikipedia','helloworld','negative','negative-retry']:
 d=r/'evidence'/key;rec=json.loads((d/'record.json').read_text())
 samples=[float(x.split()[1]) for x in (d/'timeline.txt').read_text().splitlines() if x.startswith('T ')]
 pids=sorted(set(int(x.split()[1]) for x in (d/'timeline.txt').read_text().splitlines() if x.startswith('P ')))
 trials[key]={'package':rec['package'],'uid':rec['bms']['uid'],'clicked':rec['clicked'],'icon_id':rec['selected_icon']['id'],'sample_span_seconds':round(samples[-1]-samples[0],3),'sample_count':len(samples),'sampled_pids':pids,'pids_after':rec['pids_after'],'screenshots':{x:{'path':f'evidence/{key}/{x}.jpeg','sha256':sha(d/f'{x}.jpeg')} for x in ['t3','final']},'new_faults':rec['new_faults']}
trials['wikipedia'].update(alias='org.wikipedia.DefaultIcon',target='org.wikipedia.main.MainActivity',agent_visual_observation='final is OH desktop; no Wikipedia own UI',outer_visual_verdict='pending_review',blocker='SIGSEGV in ContextWrapper.getApplicationInfo called from ContextImpl.getTheme / Activity.attach; exact root cause not established')
trials['helloworld'].update(agent_visual_observation='final shows Hello World!, CHANGE COLOR, lifecycle CREATED/RESUMED, and activity/service controls',outer_visual_verdict='pending_review')
trials['negative']['outcome']='preceding failure: nonexistent nativeLibraryDir, not a missing-target pass'
trials['negative-retry'].update(outcome='MissingTarget ClassNotFoundException; child 7151 exits code 1; no live UID process',alias='org.a2hlab.b5aliasnegative.LauncherAlias',target='org.a2hlab.b5aliasnegative.MissingTarget')
result={'task':30,'contract':'specs/bms-copy/b5-activity-alias.spec.md','serial':'5ea34a4500000000000000001123012c','boot_id':'56e521b3-858f-4fbf-8e35-daec29525c93','scope':'runtime alias only; subsequent Activity.attach crash handed to outer/B4','R2':'partially','key_count':66,'selected_alias_count':len(census['selected_alias_keys']),'selected_alias_keys':census['selected_alias_keys'],'enabled_launcher_alias_count':len(census['enabled_launcher_alias_keys']),'selection_rule':'observed BMS desktop_activity, else first enabled MAIN/LAUNCHER; see census.json per-key selection basis','trials':trials,'runtime':json.loads((r/'build-result.json').read_text()),'campaign_apks_modified':False,'deployed_boards':['5ea34a4500000000000000001123012c'],'native_installer_modified':False,'visual_acceptance':'pending outer review; Wikipedia process gate failed independently of review','negative_fixture_cleanup':json.loads((r/'negative/cleanup.json').read_text())}
(r/'results.json').write_text(json.dumps(result,indent=2)+'\n')
up=Path.home()/'orca/00.Workspace'
files=['src/adapter/framework/activity/java/LaunchActivityAliasProjection.java','src/adapter/framework/activity/java/ManifestComponentProjection.java','src/adapter/framework/activity/java/AppSchedulerBridge.java']
(r/'source-provenance.json').write_text(json.dumps({'upstream_worktree':str(up),'upstream_head':subprocess.check_output(['git','-C',str(up),'rev-parse','HEAD'],text=True).strip(),'files':[{'path':f,'sha256':sha(up/f)} for f in files],'adaptation':'Preserve OH launch identity, populate only targetActivity; use baseline bounded AXML reader because upstream InstalledApkApplicationProjection PM closure is absent. No original APK changes.'},indent=2)+'\n')
print({key:(v['sample_span_seconds'],v['sampled_pids'],v['pids_after']) for key,v in trials.items()})
