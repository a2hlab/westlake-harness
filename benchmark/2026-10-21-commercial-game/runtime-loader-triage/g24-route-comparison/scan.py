#!/usr/bin/env python3
"""Offline comparison, derived from U15 replay_normal.py; never deploys/builds.
Uses actual ELF exports/version definitions, no NDK regex exemptions. Raw commands
and complete stdout/stderr are persisted (.gz for relocation stdout).
"""
import argparse,gzip,hashlib,json,re,subprocess,time
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--workspaces',type=Path,required=True);P.add_argument('--commercial',type=Path,required=True);P.add_argument('--out',type=Path,required=True);a=P.parse_args()
W=a.workspaces.resolve();C=a.commercial.resolve();O=a.out.resolve();R=O/'.private';R.mkdir(parents=True,exist_ok=True)
T=Path('/opt/homebrew/bin/llvm-readelf')
APP=W/'westlake-harness-t4/benchmark/2026-10-21-commercial-game/exact-static/.private/g04-01/scan/members/lib/arm64-v8a'
N=C/'g21-rollout-01/candidate/native';B=N/'payload/android/lib64'
POOL=W/'westlake-harness-bms-deploy/bms/src/.work/b68-generation/platform-pool/system/lib64'
MUSL=W/'westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1'
cache={}; receipts=[]
def alias(p):return str(p).replace(str(C),'$COMMERCIAL').replace(str(W),'$WORKSPACES')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def run(p,rel=False):
 key=sha(p);tag=key[:16]+('-reloc' if rel else '-elf');out=R/(tag+'.stdout'+('.gz' if rel else ''));err=R/(tag+'.stderr');cmd=[str(T),*(['-r','--wide'] if rel else ['-d','--dyn-syms','--version-info','--wide']),str(p)]
 receipt=R/(tag+'.json')
 if receipt.exists():
  rec=json.loads(receipt.read_text());assert rec['rc']==0 and rec['input_sha256']==key
 else:
  started=time.time()
  with err.open('wb') as e:
   if rel:
    with gzip.open(out,'wb') as f:
     proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=e)
     while b:=proc.stdout.read(1024*1024):f.write(b)
     rc=proc.wait()
   else:
    with out.open('wb') as f:rc=subprocess.run(cmd,stdout=f,stderr=e).returncode
  rec={'argv':cmd,'input_sha256':key,'rc':rc,'seconds':time.time()-started,'stdout':out.name,'stderr':err.name,'stdout_sha256':sha(out),'stderr_sha256':sha(err)};dump(receipt,rec)
  assert rc==0,(p,rc)
 receipts.append({'path':alias(receipt),'sha256':sha(receipt),'object':alias(p),'object_sha256':key,'rc':rec['rc']})
 return out
symre=re.compile(r'^\s*(\d+):\s+([0-9a-fA-F]+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)')
def elf(p):
 p=p.resolve()
 if p in cache:return cache[p]
 raw=run(p).read_text();imports=[];exports={}
 for l in raw.splitlines():
  m=symre.match(l)
  if not m:continue
  i,addr,size,typ,bind,vis,ndx,name=m.groups();base=name.split('@')[0];ver=name.split('@')[-1] if '@' in name else ''
  s=dict(index=int(i),symbol=base,version=ver,binding=bind,type=typ)
  if ndx=='UND':imports.append(s)
  elif bind in ('GLOBAL','WEAK','UNIQUE') and vis in ('DEFAULT','PROTECTED'):exports.setdefault(base,[]).append({'version':ver,'default':('@@' in name or '@' not in name)})
 d={'path':alias(p),'sha256':sha(p),'bytes':p.stat().st_size,'needed':re.findall(r'\(NEEDED\).*?\[(.*?)\]',raw),'imports':imports,'exports':exports,'has_verdef':"Version definition section" in raw}
 cache[p]=d;return d
MUSL_NAMES={'libc.so','libm.so','libdl.so','ld-musl-aarch64.so.1'}
def resolve(name,native,origin=None):
 if name in MUSL_NAMES:return MUSL
 # Model direct private/app/bridge/system owners. System provider children stay
 # in their system owner; this graph is an upper bound, not inherited visibility proof.
 system=origin is not None and (str(origin).startswith(str(POOL)) or origin==MUSL)
 dirs=([POOL,POOL/'platformsdk',POOL/'chipset-sdk-sp',POOL/'ndk'] if system else
       ([B/'westlake_native'] if native else [])+[APP,B,POOL,POOL/'platformsdk',POOL/'chipset-sdk-sp',POOL/'ndk'])
 for d in dirs:
  p=d/name
  if p.is_file():return p.resolve()
 return None

def closure(root,native):
 todo=[root];seen=set();edges=[];missing=[];paths=[]
 while todo:
  p=todo.pop(0).resolve()
  if p in seen:continue
  seen.add(p);paths.append(p)
  for n in elf(p)['needed']:
   q=resolve(n,native,p);edges.append({'from':alias(p),'needed':n,'to':alias(q) if q else None})
   if q and q not in seen:todo.append(q)
   if not q:missing.append({'consumer':alias(p),'needed':n})
 return paths,edges,missing

def matches(s,d):
 for e in d['exports'].get(s['symbol'],[]):
  if not s['version'] and e['default']:return True
  if s['version'] and (not d['has_verdef'] or e['version']==s['version']):return True
 return False

def relocation_order(p):
 out=run(p,True);sections={};section=None
 with gzip.open(out,'rt') as f:
  for line in f:
   m=re.match(r"Relocation section '([^']+)'",line)
   if m:section=m.group(1);sections[section]=[];continue
   cols=line.split()
   if section and len(cols)>=5 and re.fullmatch('[0-9a-fA-F]{8,}',cols[0]) and cols[2].startswith('R_'):
    # Relative-only entries have no symbol; dynsym-name match below excludes them.
    sections[section].append({'symbol':cols[4].split('@')[0],'section':section,'offset':cols[0],'type':cols[2]})
 return [r for sec in sorted(sections,key=lambda x:('plt' not in x,list(sections).index(x))) for r in sections[sec]]

apps=sorted(APP.glob('*.so'));assert len(apps)==32
musl=elf(MUSL);abi=elf(B/'westlake_native/libwestlake_native_abi.so')
# Root dependency closure determines providers; unrelated app libraries are NOT global.
report={};abi_exports=set(abi['exports']);summary={}
for p in apps:
 e=elf(p);order=relocation_order(p);byname={s['symbol']:s for s in e['imports'] if s['binding']!='WEAK'}
 ordered=[];seen=set()
 for r in order:
  if r['symbol'] in byname and r['symbol'] not in seen:ordered.append({**byname[r['symbol']],**r});seen.add(r['symbol'])
 row={'elf':e,'strong_imports_without_observed_relocation':[s for k,s in byname.items() if k not in seen],'routes':{}}
 for mode,native,seam in [('current',False,False),('native_cluster',True,False),('single_atfork',False,True)]:
  paths,edges,missing=closure(p,native);providers=[elf(q) for q in paths]+[musl]+([abi] if native else [])
  unresolved=[];covered_abi=[]
  for s in ordered:
   found=[d['path'] for d in providers if matches(s,d)]
   virtual=seam and s['symbol']=='__register_atfork' and s['version'] in ('','LIBC')
   if not found and not virtual:unresolved.append(s)
   if native and matches(s,abi) and not any(matches(s,d) for d in providers if d!=abi):covered_abi.append(s)
  row['routes'][mode]={'closure':[alias(q) for q in paths],'edges':edges,'unlocated_dependencies':missing,'unresolved':unresolved,'abi_only_covered':covered_abi,'first_unresolved':unresolved[0] if unresolved else None}
 report[p.name]=row
 print(p.name,[(k,len(v['unresolved'])) for k,v in row['routes'].items()],flush=True)
for mode in ['current','native_cluster','single_atfork']:
 misses=[(n,s['symbol'],s['version']) for n,r in report.items() for s in r['routes'][mode]['unresolved']]
 summary[mode]={'unresolved_import_pairs':len(misses),'distinct_symbols':len({(s,v) for n,s,v in misses}),'affected_elfs':len({n for n,s,v in misses}),'missing':misses}
dump(O/'scan-results.json',{'model':'version-aware DT_NEEDED closure upper-bound, namespace access and actual provider identity not inferred','summary':summary,'libraries':report})
dump(O/'provider-objects.json',list(cache.values()));dump(O/'command-index.json',receipts)
print('SUMMARY',json.dumps({k:{x:y for x,y in v.items() if x!='missing'} for k,v in summary.items()}),flush=True)
