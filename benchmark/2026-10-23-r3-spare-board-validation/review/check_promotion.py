#!/usr/bin/env python3
"""Hash/stat + permitted startup/init data only. Does not execute author code."""
import hashlib,json,stat
from pathlib import Path
HERE=Path(__file__).resolve().parent; WS=HERE.parents[3]
OWNER=WS/'westlake-harness-g10-env'; D=OWNER/'benchmark/2026-10-23-r3-spare-board-validation'; P=D/'.private/promotion-01'
T=OWNER/'benchmark/2026-10-23-qualified-r3-board-package/.private/build-02'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def j(p):return json.loads(p.read_text())
checks=[]
def ck(n,v):checks.append({'name':n,'pass':bool(v)})
def ordinary(p):
 return stat.S_ISREG(p.lstat().st_mode) and all(not x.is_symlink() for x in [p,*p.parents]) and '..' not in p.parts
r=j(D/'results.json');m=j(P/'package-manifest.json');plan=j(P/'plan.json');parent=j(T/'output-manifest.json')
accept=Path.home()/'.local/share/westlake/t120-outer-review-20261023/outerreview.json'
ck('outer acceptance pin',sha(accept)==m['acceptance_sha256']==r['acceptance_sha256'])
ck('parent manifest pin',sha(T/'output-manifest.json')==m['parent_output_manifest_sha256']==r['parent_manifest_sha256'])
ck('manifest public private exact',sha(P/'package-manifest.json')==sha(D/'package-manifest.json')==r['package_manifest_sha256'])
ck('plan public private exact',sha(P/'plan.json')==sha(D/'plan.json')==r['plan_sha256'])
ck('install manifest pin',sha(D/'install-manifest.json')==r['install_manifest_sha256'])
rows=m['files'];ck('22 unique regular payload files',len(rows)==len({x['name'] for x in rows})==22 and {x.name for x in (P/'payload').iterdir()}=={x['name'] for x in rows})
changed=[]
for x in rows:
 n=x['name'];p=P/'payload'/n;h=sha(p)
 ck('payload:'+n,ordinary(p) and h==x['sha256'] and format(stat.S_IMODE(p.stat().st_mode),'o')==x['mode']==x['actual_local_mode'] and x['target']==plan['root']+'/'+n and x['target_owner']=='0:0')
 ck('parent untouched:'+n,sha(T/'package/payload'/n)==parent['payload/'+n])
 if h!=parent['payload/'+n]:changed.append(n)
ck('only startup and expected changed',sorted(changed)==['startup.env','startup.expected.sha256'])
b=(T/'package/payload/startup.env').read_bytes();a=(P/'payload/startup.env').read_bytes();e=b
for old,new in [(b"STARTUP_ENABLED='0'",b"STARTUP_ENABLED='1'"),(b"STARTUP_APPROVED_BY='DISABLED-PENDING-OUTER'",b"STARTUP_APPROVED_BY='outer(codex)'")]:
 ck('unique startup field:'+old.decode().split('=')[0],b.splitlines().count(old)==1);e=e.replace(old,new,1)
ck('exact two field byte transform',a==e)
ck('expected exact digest bytes',(P/'payload/startup.expected.sha256').read_bytes()==(sha(P/'payload/startup.env')+'\n').encode())
old=(P/'init.before.cfg').read_bytes();new=(P/'init.after.cfg').read_bytes();roll=(P/'init.rollback.cfg').read_bytes()
pin='19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152'
raw=Path.home()/'.local/share/westlake/current-control-fingerprint-20261023/raw2/5cd/cfg.stdout'
ck('init exact original raw receipt',old==raw.read_bytes().split(b'---CFG\n',1)[1] and sha(P/'init.before.cfg')==pin)
ck('init rollback exact bytes',roll==old)
ck('init sole argv byte change',old.count(plan['init']['before'].encode())==1 and new==old.replace(plan['init']['before'].encode(),plan['init']['after'].encode(),1))
for name in ['init.before.cfg','init.after.cfg','init.rollback.cfg']:
 ck('init mode/regular:'+name,ordinary(P/name) and stat.S_IMODE((P/name).stat().st_mode)==0o550)
rawstat=raw.read_text().splitlines()[0].split();ck('original init owner/mode',rawstat[-4:-1]==['0','0','550'])
chain=j(WS/'westlake-harness/benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root/CHAIN.json')['payload_manifest']
fixed=[n for n,h in parent.items() if chain[n]==h];ck('17 historical fixed match',len(fixed)==17 and all(sha(P/n)==parent[n] for n in fixed))
install=[x for x in rows if x['install']];ck('20 install/2 excluded',len(install)==20 and {x['name'] for x in rows if not x['install']}=={'recovery.cfg','rollback-inert.cfg'})
im=j(D/'install-manifest.json');ck('install manifest exact subset and binding',im['files']==install and im['root']==plan['root'] and im['package_manifest_sha256']==sha(P/'package-manifest.json'))
serial='5cd1e3dd00000000000000000923012c';ck('serial whitelist',plan['serial']==serial)
commands=[]
for item in plan['payload_commands']:
 for k,v in item.items():
  if k.endswith('_argv'):commands.append(v)
commands+=list(plan['init_and_rollback_commands'].values())
ck('all provided device argv target 5cd',all(v[1:3]==['-t',serial] for v in commands))
ck('budget declared 900/180',plan['budget_seconds']==900 and plan['rollback_reserve_seconds']==180)
log=D/'.private/promote01';ck('actual promotion rc0 empty stderr',(log/'rc').read_text().strip()=='0' and (log/'stderr').stat().st_size==0)
ck('raw log binds outputs',j(log/'stdout')['package_sha256']==sha(P/'package-manifest.json') and j(log/'stdout')['plan_sha256']==sha(P/'plan.json'))
result={'package_verdict':'PASS' if all(c['pass'] for c in checks) else 'FAIL','execution_plan_verdict':'PENDING_SEPARATE_CC_EXECUTOR_REVIEW','checks':checks,'counts':{'pass':sum(c['pass'] for c in checks),'total':len(checks),'payload':22,'install':20,'unchanged_vs_parent':20,'historical_fixed':17},'pins':{'package_manifest':sha(P/'package-manifest.json'),'plan':sha(P/'plan.json'),'startup_env':sha(P/'payload/startup.env'),'startup_expected':sha(P/'payload/startup.expected.sha256'),'init_before':sha(P/'init.before.cfg'),'init_after':sha(P/'init.after.cfg'),'init_rollback':sha(P/'init.rollback.cfg')},'raw_promotion_receipts':{n:{'sha256':sha(log/n),'bytes':(log/n).stat().st_size} for n in ['argv.json','start','end','stdout','stderr','rc']},'separate_execution_review_items':[{'id':'E1','evidence':'plan.json /pending_execution_bindings/0 and /init_and_rollback_commands','finding':'Only sends/current verification/reboot are specified; concrete existing atomic init install and rollback argv, mount/label preservation/readback method remain unbound.'},{'id':'E2','evidence':'plan.json /budget_seconds, /rollback_reserve_seconds, /execution_requirements','finding':'900/180 budgets declared; no concrete start, stop-at-720s or rollback-deadline sequence attached. Fresh lock/boot/power/host gates likewise require CC binding before execution.'}],'scope':{'device_calls':0,'controller_execution':0,'implementation_text_reads':0,'author_generators_executed_by_reviewer':0},'rollback_scope':'Original ROOT untouched; exact original init bytes verified. No demand for scanning the five unindexed old-root files.','limits':['Package byte/mode PASS is not execution admission or runtime compatibility','agent-spec explain reports three skipped scenarios; no device acceptance asserted','Initial prepared-01 findings retained; promotion absence resolved by promotion-01, E1/E2 assigned to separate CC executor review; not package-stage blockers']}
(HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'package':result['package_verdict'],'plan':result['execution_plan_verdict'],'counts':result['counts'],'failed':[c for c in checks if not c['pass']]}))
raise SystemExit(0 if result['package_verdict']=='PASS' else 1)
