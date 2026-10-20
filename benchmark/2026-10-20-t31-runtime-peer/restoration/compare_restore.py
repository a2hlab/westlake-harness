#!/usr/bin/env python3
"""Local-only comparison of this window's original and restored evidence."""
from pathlib import Path
import json,hashlib,sys
W=Path(__file__).resolve().parent.parent
names=['before-snapshot/snapshot.json','restored-snapshot/snapshot.json','before-supplement/result.json','restored-supplement/result.json','before-supplement/stdout.raw','restored-supplement/stdout.raw','apply/plan.json','restored-boot.json']
missing=[n for n in names if not (W/n).is_file()]
if missing:
 print(json.dumps({'status':'PENDING_INPUTS','missing':missing,'device_calls':0}));sys.exit(2)
def load(n):return json.loads((W/n).read_text())
b,a=load(names[0]),load(names[1]);bs,as_=load(names[2]),load(names[3]);plan=load('apply/plan.json');rb=load('restored-boot.json')
fields=['sha','labels','params','init_configs','bind_targets','config_policy_layer_roots','selinux_enforce','plan_sha256']
checks={}
for label,s in [('before',b),('after',a)]:
 checks[label+'_complete']=all(s.get(k) is True for k in ['complete','collection_complete','boot_stable']) and s.get('capture_status')=='COMPLETE' and not s.get('errors')
 checks[label+'_518_targets']=s.get('plan_target_count')==518
checks['original_before_boot']=b['boot_id']==plan['boot']
checks['restored_fresh_boot']=a['boot_id']!=b['boot_id'] and a['boot_id']==rb.get('boot',rb.get('boot_id'))
for k in fields:checks['equal_'+k]=k in b and k in a and b[k]==a[k]
checks['collection_sha_equal']=bool(b.get('collection_sha256')) and b['collection_sha256']==a.get('collection_sha256')
for label,s,snap,raw in [('before',bs,b,names[4]),('after',as_,a,names[5])]:
 checks[label+'_supplement_complete']=s.get('status')=='SUPPLEMENT_BYTES_COMPLETE' and s.get('targets')==26 and s.get('rc')==0 and s.get('boot')==snap['boot_id']
 checks[label+'_supplement_raw_sha']=hashlib.sha256((W/raw).read_bytes()).hexdigest()==s.get('raw',{}).get('stdout.raw',{}).get('sha256')
def norm(n,boot):
 text=(W/n).read_text(); assert text.count(boot)==1,text.count(boot)
 return text.replace(boot,'<WINDOW_BOOT>')
checks['supplement_equal_except_boot']=norm(names[4],b['boot_id'])==norm(names[5],a['boot_id'])
r={'status':'SNAPSHOT_AND_SUPPLEMENT_EQUAL' if all(checks.values()) else 'MISMATCH','checks':checks,'source_refs':[{'path':n,'sha256':hashlib.sha256((W/n).read_bytes()).hexdigest(),'bytes':(W/n).stat().st_size} for n in names],'not_checked':['six physical/private states','power','debug parameter','UI','lock release','video/audio'],'device_calls':0,'close_written':False}
print(json.dumps(r,indent=2));sys.exit(0 if all(checks.values()) else 1)
