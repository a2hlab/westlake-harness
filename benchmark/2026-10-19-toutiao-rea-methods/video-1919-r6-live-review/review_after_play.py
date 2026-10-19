#!/usr/bin/env python3
"""Offline checkpoint from existing r6 files. No transport, writes only beside this file."""
import hashlib,json,re
from pathlib import Path
BASE=Path.home()/'.local/share/westlake/toutiao-resume-20261019'
OUT=Path(__file__).resolve().parent
pins=[]
def read(name):
 p=BASE/name;b=p.read_bytes();pins.append({'private_relative_path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b.decode(errors='replace')
def stat(name):
 s=read(name);a=s[s.rfind(')')+2:].split();return {'pid':s.split()[0],'state':a[0],'ppid':a[1],'birth':a[19]}
n='video-r6-native-after-play1/'
identity=json.loads(read(n+'identity.json'))
identities={x:stat(n+x+'.stat') for x in ['before-child','after-child','before-parent','after-parent']}
assert all(identities[x]['pid']=='7085' and identities[x]['ppid']=='5130' and identities[x]['birth']=='11201' for x in ['before-child','after-child'])
assert all(identities[x]['pid']=='5130' and identities[x]['birth']=='9571' for x in ['before-parent','after-parent'])
terms=['debug.ttplayer.log.enable','JNI_OnLoad','setDataSource','prepareAsync','TTVideoEngine','MetaVideoPlayerLog','DataLoaderHelper','TTPlayer','ttmplayer','avmdl']
logs={};property_hits=[]
for name in ['child.stderr','hilog.txt']:
 s=read(n+name);logs[name]={'exact_case_counts':{t:s.count(t) for t in terms}}
 for i,line in enumerate(s.splitlines(),1):
  if '[WESTLAKE-WEBVIEW-BIONIC] property debug.ttplayer.log.enable=' in line:property_hits.append({'file':name,'line':i,'text':line})
 if name=='hilog.txt':
  parsed=[m.groups() for line in s.splitlines() if (m:=re.match(r'^\s*(\d+\.\d+)\s+(\d+)\s+(\d+)\s+([DIWEF])\s',line))]
  logs[name].update({'parsed_rows':len(parsed),'monotonic_first':parsed[0][0] if parsed else None,'monotonic_last':parsed[-1][0] if parsed else None,'pids':sorted({x[1] for x in parsed}),'priorities_present':sorted({x[3] for x in parsed})})
cmds=[]
for p in sorted((BASE/n/'commands').glob('*.json')):
 d=json.loads(read(str(p.relative_to(BASE))));o=p.with_suffix('.stdout.txt');raw=read(str(o.relative_to(BASE))) if o.exists() else '';remote=re.findall(r'__BMS_REMOTE_RC_[a-f0-9]+__(\d+)',raw)
 cmds.append({'name':p.name,'exit_code':d.get('exit_code'),'remote_rcs':remote,'hilog_levels_explicit':'hilog -x -P 7085 -L D,I,W,E,F -v monotonic' in ' '.join(d.get('argv',[]))})
assert all(x['exit_code']==0 and all(rc=='0' for rc in x['remote_rcs']) for x in cmds)
plan=read('video-r6-apply/plan.json');rollback=json.loads(read('video-r6-rollback/result.json'));assert rollback['origin_apply_plan_sha256']==hashlib.sha256(plan.encode()).hexdigest()
reboot=json.loads(read('video-r6-rollback-reboot/result.json'))
record=json.loads(read('video-r6-play1/record.json'));got=json.loads(read('video-r6-play1/got.json'))
r={'token':'video-1919-r6-live-review','status':'IN_PROGRESS_NOT_FROZEN','identity':identity,'parsed_original_stats':identities,'posttap_collection_commands':cmds,'logs':logs,'property_consumer_observation':property_hits,'property_interpretation':'Actual child bridge property read returned true after player-load messages. Consistent with static JNI_OnLoad evidence; no call stack/return-PC in this text, so exact callsite attribution not independently established. Not merely param get.','source_prepare_observation':'Exact-case setDataSource/prepareAsync absent in these two collected logs; no proof they did not execute. Java logging enablement unproved.','visual':'Pre-tap actual feed. Three play screenshots have identical bytes and show the same cover; no dynamic playback demonstrated.','playback':'NOT_PASSED','audio':'UNKNOWN','got_original_status':got['status'],'got_modified':False,'rollback':{'original_apply_plan_binding_verified':True,'status':rollback['status'],'fresh_reboot_command_completed':reboot['completed'],'new_boot_restored_identity_parameter_feed_unlock':'PENDING'},'pins':pins,'device_calls':0,'API_changes':False}
(OUT/'after-play-checkpoint.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS offline identity/raw rc/apply-plan binding; checkpoint remains IN_PROGRESS_NOT_FROZEN')
