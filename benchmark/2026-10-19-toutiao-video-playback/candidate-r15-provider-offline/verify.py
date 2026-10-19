#!/usr/bin/env python3
"""Validate actual local build evidence, not a declaration of provider readiness."""
import argparse, copy, json, struct
from pathlib import Path
from build import STATUS, R14_PINS, OH_PINS, sha, need
COUNTS={'pair':7,'layout':16,'failures':13,'concurrency':8}
def verify(out,record=None):
 out=Path(out).resolve();r=record if record is not None else json.loads((out/'receipt.json').read_text())
 need(r['schema']=='r15-build-v1' and r['status']==STATUS and r['complete'] is True,'not a completed offline build')
 need(r['device_calls']==0 and r['shared_library'] is False and r['production_binding'] is False,'scope changed')
 need(r['r14_pins']==R14_PINS,'R14 pins changed');need(r['dependencies_unchanged'] is True,'dependency drift')
 for p,h in r['sources'].items():need(sha(p)==h,'source SHA drift')
 for p,h in r['dependencies_before'].items():need(sha(p)==h,'dependency SHA drift')
 need(r['dependencies_before'],'missing dependencies')
 for v in r['tools'].values():need(sha(v['path'])==v['sha256'],'tool SHA drift')
 names=[]
 for command in r['commands']:
  name=command['name'];need(name not in names,'duplicate stage');names.append(name);need(command['rc']==0,'command failed')
  expected={f'raw/{name}.{suffix}' for suffix in ['command.json','stdout.txt','stderr','rc']}
  need(set(command['raw'])==expected,'incomplete raw triplet/argv')
  for rel,v in command['raw'].items():
   p=out/rel;need(p.is_file() and sha(p)==v['sha256'] and p.stat().st_size==v['bytes'],'raw identity drift')
  need((out/'raw'/f'{name}.rc').read_text().strip()=='0','raw rc failed')
  argv=json.loads((out/'raw'/f'{name}.command.json').read_text());need(isinstance(argv,list) and argv and all(isinstance(x,str) for x in argv),'missing argv')
 need(names and names[0]=='00-frozen','frozen check not first')
 for rel,v in r['artifacts'].items():need(sha(out/rel)==v['sha256'] and (out/rel).stat().st_size==v['bytes'],'artifact drift')
 if r['mode']=='host':
  need(set(r['artifacts'])=={'window_module.o','provider_adapter.o','test_adapter.o','test_adapter'},'unexpected host artifact')
  need(r['groups'],'empty groups')
  for group,v in r['groups'].items():
   need(group in COUNTS and v['cases']==COUNTS[group] and v['status']=='PASS','wrong case count')
   log=out/'raw'/f'30-{group}.stdout.txt';need(sha(log)==v['journal_sha256'],'journal drift');items=[json.loads(x) for x in log.read_text().splitlines()]
   need(len(items)==COUNTS[group] and len({x['case'] for x in items})==len(items) and all(x['status']=='PASS' and isinstance(x['journal'],list) for x in items),'invalid journal')
   need('30-'+group in names,'unexecuted group')
  need({'10-object-0','10-object-1','10-object-2','19-link-plan','20-link'}<=set(names),'missing host build stages')
 elif r['mode']=='oh':
  need(set(r['artifacts'])=={'provider_adapter.o'},'unexpected OH artifact');need(r['sdk_signature_layout_assertions']=='PASS_COMPILE_ONLY','ABI assertions missing')
  need(r['tools']['cc']['sha256']==OH_PINS['clang'] and r['tools']['readelf']['sha256']==OH_PINS['llvm-readelf'],'wrong OH tools')
  need({'10-object-0','20-readelf'}<=set(names),'missing OH stages');data=(out/'provider_adapter.o').read_bytes()
  need(data[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<HH',data,16)==(1,183) and struct.unpack_from('<H',data,56)[0]==0,'not AArch64 ET_REL')
 else:raise RuntimeError('unknown build mode')
 return {'status':'PASS','mode':r['mode'],'raw_stages':len(names),'deployment':False}
def negative_checks(host,oh):
 base=json.loads((Path(host)/'receipt.json').read_text());cases=[]
 def reject(name,mutate):
  x=copy.deepcopy(base);mutate(x)
  try:verify(host,x)
  except (RuntimeError,KeyError,FileNotFoundError):cases.append({'case':name,'rejected':True});return
  raise RuntimeError('accepted negative '+name)
 reject('incomplete',lambda x:x.update(complete=False))
 reject('production-binding',lambda x:x.update(production_binding=True))
 reject('wrong-status',lambda x:x.update(status='DEPLOYABLE'))
 reject('changed-r14',lambda x:x['r14_pins'].update({'window_module.c':'0'*64}))
 reject('nonzero-rc',lambda x:x['commands'][0].update(rc=2))
 reject('missing-stderr',lambda x:x['commands'][0]['raw'].pop('raw/00-frozen.stderr'))
 reject('raw-sha-drift',lambda x:x['commands'][0]['raw']['raw/00-frozen.stdout.txt'].update(sha256='0'*64))
 reject('missing-dependencies',lambda x:x.update(dependencies_before={}))
 reject('missing-frozen-stage',lambda x:x['commands'].pop(0))
 verify(oh);return cases
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('host');p.add_argument('oh');p.add_argument('--negative',action='store_true');a=p.parse_args()
 result={'host':verify(a.host),'oh':verify(a.oh)}
 if a.negative:result['negative_cases']=negative_checks(a.host,a.oh)
 print(json.dumps(result,indent=2))
