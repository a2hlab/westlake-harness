"""Exact T30 origin, independent T31 recovery window. Local checks only."""
import datetime
import hashlib
import json
import re
import uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
SERIAL='5cd1e3dd00000000000000000923012c'
EXECUTOR='693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb'
PIN_KEYS={'executor_sha256':'executor.py','parameters_sha256':'parameters.json','source_pins_sha256':'executor-source-pins.json','readonly_inputs_sha256':'readonly-inputs.json','bridge_candidate_sha256':'bridge-candidate.json','shim_candidate_sha256':'shim-candidate.json','three_slot_requirements_sha256':'three-slot-admission.json','bridge_binding_requirements_sha256':'bridge-binding-pending.json'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,why):
    if not ok:raise ValueError(why)
def data_check(d):
    pins=json.loads((HERE/'origin-data-pins.json').read_text())
    for rel,h in pins.items():require(sha(d/rel)==h,'origin data drift: '+rel)
    return pins
def validate_origin(d,plan_path,admission_path):
    data_check(d)
    p=json.loads(Path(plan_path).read_text());o=json.loads(Path(admission_path).read_text())
    require(sha(admission_path)==p['admission_sha256'],'origin admission hash')
    require(p['mode']=='apply' and p['serial']==o['serial']==SERIAL and p['uid']==o['uid']==20011300,'origin scope')
    require(p['executor_sha256']==o['executor_sha256']==EXECUTOR,'origin executor')
    require(o.get('deployment_scope')=='T31_5CD_DEMO_CANDIDATE','T31 actual apply scope required; T30 historical plan forbidden')
    require(re.fullmatch(r't31-5cd-window-[0-9]+',o.get('origin_window_id','')),'T31 origin window id')
    require(Path(plan_path).name=='plan.json' and Path(plan_path).parent.name=='apply' and Path(plan_path).parent.parent.name==o['origin_window_id'],'origin plan path/window mismatch')
    require(p['holder']==o['holder'] and p['start']==o['window_start'] and p['boot']==o['boot'],'origin identity')
    tok=p['holder'].split();require(len(tok)==3 and tok[0]=='inner(cx-seal)' and tok[1].isdigit(),'origin holder')
    require(abs(datetime.datetime.fromisoformat(tok[2]).timestamp()-p['start'])<1,'origin start')
    require(str(uuid.UUID(p['boot']))==p['boot'] and str(p['wid'])=='29','origin boot/WID29')
    require(o['approved_by']=='outer(codex)' and p['compat_before_absent'] is True,'origin authorization')
    for k,n in PIN_KEYS.items():require(o[k]==sha(d/n),'origin admission source '+k)
    require(p['before_sha']==sha(d/'run5cd.before.reference.sh') and p['after_sha']==sha(d/'run5cd.after.wid29.reference.sh'),'origin run pair')
    for role in ('bridge','shim'):
        c=json.loads((d/(role+'-candidate.json')).read_text())
        for suffix,value in [('before_sha',c['before_sha256']),('after_sha',c['after_sha256']),('candidate_sha256',sha(d/(role+'-candidate.json')))]:require(p[role+'_'+suffix]==value,'origin '+role+' '+suffix)
    params=json.loads((d/'parameters.json').read_text())
    require(p['runtime']==params['runtime'] and p['cfg_sha']==o['cfg_sha256']==params['cfg_sha256'],'origin runtime/cfg')
    for role,path,mode in [('media','lib/arm64-v8a/libmffmpeg.so','644'),('player','lib/arm64-v8a/libttmplayer.so','644'),('bridge','liboh_adapter_bridge.so','644'),('shim','webview-t-lib/libwebview_bionic_shim.so','755')]:
        row=next(x for x in params['artifacts'] if x['path']==path)
        require(p[role+'_before_sha']==row['before_sha256'] and p[role+'_after_sha']==row['after_sha256'],'origin artifact '+role)
        require(p[role+'_metadata']==mode+':20011300:20011300' and p[role+'_label']=='u:object_r:appdat:s0','origin metadata '+role)
        if role!='media':require(p[role+'_path']==path,'origin target path '+role)
    require(p['run_metadata']=='755:20011300:20011300' and p['run_label']==p['dso_label']=='u:object_r:appdat:s0','origin run/compat metadata')
    require(p['dso_sha']==params['artifacts'][1]['after_sha256'],'origin compat')
    require(p['compat_absence_marker']==params['runtime']+'/libopensles_android_compat.so.t21-5cd-before-'+p['boot'][:8]+'.absent' and p['compat_absence_marker_sha256']==hashlib.sha256(b'ABSENT\n').hexdigest(),'origin absence marker')
    return p,o
def source_pins():
    return {n:sha(HERE/n) for n in ('recovery.py','recovery_core.py','recovery_policy.py','recovery_admission.py','origin-data-pins.json')}
def validate_sources(ad):require(ad['recovery_source_pins']==source_pins(),'recovery source drift')
def validate_window(ad,origin,holder,start,boot,now):
    tok=holder.split();require(len(tok)==3 and tok[0]=='inner(cx-seal)' and tok[1].isdigit(),'new holder')
    require(abs(datetime.datetime.fromisoformat(tok[2]).timestamp()-start)<1,'new holder timestamp')
    require(start>origin['start'] and holder!=origin['holder'],'independent recovery window required')
    require(0<=now-start<1800,'new recovery window expired')
    require(str(uuid.UUID(boot))==boot,'current boot')
    require(ad['holder']==holder and ad['window_start']==start and ad['boot']==boot,'current identity binding')
    require(ad['approved_by']=='outer(codex)' and ad['serial']==SERIAL and ad['uid']==20011300,'recovery authorization')
