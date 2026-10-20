from pathlib import Path
import sys,time,json,copy,os,hashlib
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P));import window_exec as m
MAIN=Path(os.environ['T31_MAIN']);D=MAIN/'benchmark/2026-10-20-t30-request-recovery/deployment/final-01';W=P/'t31-5cd-window-99';W.mkdir();start=time.time()-5
ad=json.loads((D/'admission.template.json').read_text());ad.update(holder='inner(cx-seal) 111 2026-10-20T17:00:00+08:00',window_start=start,boot='00000000-0000-0000-0000-000000000001',deployment_scope='T31_5CD_DEMO_CANDIDATE',origin_window_id=W.name)
c=dict(serial=m.SERIAL,deploy=str(D),holder=ad['holder'],start=start,repo=str(MAIN),inputs=str(P/'inputs'),hdc='NEVER_EXECUTED')
ids=dict(boot=ad['boot'],parent=999,parent_birth=10);a=W/'scoped-admission.json';i=W/'identity.json';i.write_text(json.dumps(ids));results=[]
def call(name,mode,cfg,admission,expect,**kw):
 a.write_text(json.dumps(admission))
 try:argv=m.command(mode,cfg,W,a,i,W/('apply' if mode=='apply' else mode),**kw)
 except ValueError as ex:
  assert not expect,(name,str(ex));results.append(dict(case=name,rejected=True,reason=str(ex)));return
 assert expect,name
 assert argv[argv.index('--admission')+1]==str(a);assert argv[argv.index('--out')+1]==str(W/('apply' if mode=='apply' else mode));results.append(dict(case=name,rejected=False,argv=argv))
call('apply-scoped','apply',c,ad,True)
v=copy.deepcopy(ad);v.pop('deployment_scope');call('unscoped-refused','apply',c,v,False)
v=copy.deepcopy(ad);v['origin_window_id']='t31-5cd-window-98';call('wrong-window-refused','apply',c,v,False)
v=copy.deepcopy(ad);v['executor_sha256']='0'*64;call('executor-drift-refused','apply',c,v,False)
expired=dict(c,start=time.time()-1201);v=dict(ad,window_start=expired['start']);call('apply-1200-refused','apply',expired,v,False)
origin=W/'origin-plan.json';origin.write_text(json.dumps({'holder':c['holder'],'start':c['start']}));v=dict(ad,origin_apply_plan_sha256=m.sha(origin));call('same-window-rollback','same-window-rollback',c,v,True,origin_plan=origin)
expired=dict(c,start=time.time()-1801);v=dict(ad,window_start=expired['start'],origin_apply_plan_sha256=m.sha(origin));call('rollback-1800-refused','same-window-rollback',expired,v,False,origin_plan=origin)
origin_ad=W/'origin-admission.json';origin_ad.write_text('{}');v=dict(ad,executor_sha256=m.sha(P/'recovery/recovery.py'));call('durable-route','durable-recovery',dict(c,purpose='T31_DURABLE_RECOVERY'),v,True,origin_plan=origin,origin_admission=origin_ad)
for r in results:
 if r['case']=='durable-route':assert '--origin-data' in r['argv'] and '--origin-admission' in r['argv']
output=dict(status='PASS',cases=results,device_calls=0,helper_sha256=m.sha(P/'window_exec.py'),limits='Actual command() construction/validation only. No executor dispatched; synthetic identities. Underlying executor still checks timestamp/held/provenance.')
(P/'results.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps({'status':'PASS','cases':len(results),'helper_sha256':output['helper_sha256']}))
