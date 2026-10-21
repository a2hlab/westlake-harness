#!/usr/bin/env python3
"""Validate this static inventory; optional exact local evidence replay, no device calls."""
import argparse,hashlib,json,os,re
from pathlib import Path
D=Path(__file__).resolve().parent
R=next(p for p in D.parents if (p/'scripts/lab').is_dir())
def read(n):return json.loads((D/n).read_text())
def resolve(s):
 roots={'$REPO':R,'$MAIN':Path(os.environ.get('G34_MAIN',str(R.parent/'westlake-harness'))),'$WORKSPACES':Path(os.environ.get('WORKSPACES',str(R.parent))),'$HOME':Path.home()}
 key,sep,rest=s.partition('/')
 if key not in roots or not sep:raise ValueError(s)
 return roots[key]/rest
PAT=re.compile(r'\s*\d+:\s+([0-9a-f]+)\s+(\d+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\S+)\s+(\S+)')
def symbols(p):
 out=[]
 for line,t in enumerate(p.read_text().splitlines(),1):
  m=PAT.match(t)
  if m:
   _,size,typ,bind,vis,idx,name=m.groups();out.append(dict(name=name,type=typ,binding=bind,visibility=vis,section=idx,size=int(size),line=line))
 return out

def main():
 a=argparse.ArgumentParser();a.add_argument('--sources',action='store_true');args=a.parse_args()
 r=read('results.json');m=read('provider-matrix.json');rows=m['imports'];ps={p['id']:p for p in m['providers']}
 assert len(rows)==439 and len(ps)==8
 assert sum(x['binding']!='WEAK' for x in rows)==434
 assert [x['import'] for x in rows if x['status']=='EXCLUDED_BY_SCOPE']==['__assert2@LIBC']
 assert sum(x['status']=='WEAK_UNRESOLVED_STATIC' for x in rows)==3
 assert not any(x['status']=='NO_NAMED_PROVIDER_IN_REVIEW_SET' for x in rows)
 assert not r['new_fix_keys'] and r['runtime_winner']=='UNKNOWN'
 assert ps['native-abi']['artifact']['sha256']==r['candidate_sha256']=='4296f8052b6ccc130df83366717903695eba38fcde19c462ee64521414696f0b'
 assert next(x for x in rows if x['import']=='__strncpy_chk2@LIBC')['providers']==[dict(provider='android-liblog',export='__strncpy_chk2@@LIBC',type='FUNC',size=196,line=101,version_relation='EXPLICIT_VERSION_MATCH')]
 for x in rows:
  assert all(y['provider'] in ps for y in x['providers'])
 if args.sources:
  idx=read('evidence-index.json');refs=idx['references']+idx['new_local_commands']
  for x in refs:
   b=resolve(x['path']).read_bytes();assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256'],x['path']
  raw=next(x for x in refs if x['path'].endswith('/yuanshen-dynsym.stdout'))
  imps=[s for s in symbols(resolve(raw['path'])) if s['section']=='UND']
  defs={k:[s for s in symbols(resolve(v['symbol_evidence']['path'])) if s['section']!='UND' and s['binding'] in ('GLOBAL','WEAK') and s['visibility'] in ('DEFAULT','PROTECTED')] for k,v in ps.items()}
  assert len(imps)==len(rows)
  for actual,row in zip(imps,rows):
   assert (actual['name'],actual['binding'],actual['line'],actual['type'])==(row['import'],row['binding'],row['line'],row['type'])
   if row['status']=='EXCLUDED_BY_SCOPE':continue
   expected=[]
   for k,ss in defs.items():
    for s in ss:
     if s['name'].split('@')[0]==actual['name'].split('@')[0]:
      req=actual['name'].split('@',1)[1] if '@' in actual['name'] else None
      ver=s['name'].split('@')[-1] if '@' in s['name'] else None
      rel='EXPLICIT_VERSION_MATCH' if req and req==ver else ('UNVERSIONED_DEFINITION_PLATFORM_RESOLUTION_UNKNOWN' if req and not ver else ('VERSION_DIFFERENT' if req else 'NAME_ONLY_NO_IMPORT_VERSION'))
      expected.append(dict(provider=k,export=s['name'],type=s['type'],size=s['size'],line=s['line'],version_relation=rel))
   assert row['providers']==expected,actual['name']
  print('PASS exact evidence SHA/size and 439-row symbol replay; no runtime validation')
 else:print('PASS public static inventory consistency; no runtime validation')
if __name__=='__main__':main()
