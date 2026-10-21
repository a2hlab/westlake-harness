#!/usr/bin/env python3
"""Isolated replay of U13's first (U12 baseline) command pair; no staging."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
EXPECTED='2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def run(out,name,argv,cwd):
 dump(out/(name+'.argv.json'),{'argv':argv,'cwd':str(cwd)})
 with (out/(name+'.stdout')).open('wb') as so,(out/(name+'.stderr')).open('wb') as se:
  r=subprocess.run(argv,cwd=cwd,stdout=so,stderr=se)
 (out/(name+'.rc')).write_text(str(r.returncode)+'\n')
 if r.returncode:raise RuntimeError(name+' rc='+str(r.returncode))
def main():
 a=argparse.ArgumentParser();a.add_argument('--workspaces',type=Path,default=D.parents[3]);a.add_argument('--out',type=Path,required=True);a.add_argument('--variant',choices=['baseline','candidate'],required=True);a.add_argument('--baseline-receipt',type=Path);x=a.parse_args();W=x.workspaces.resolve();out=x.out.resolve();out.mkdir(parents=True,exist_ok=False)
 R=W/'westlake-harness-bms';ref=W/'westlake-harness/benchmark/2026-10-02-u13-single-native/host-build-receipt.json';r=json.loads(ref.read_text());oldsrc=R/'benchmark/2026-10-02-u12-private-zlib/inputs';src=D/'sources'/x.variant/'host'
 if x.variant=='candidate':
  b=json.loads(x.baseline_receipt.read_text());assert b['status']=='BASELINE_EXACT' and b['artifact']['sha256']==EXPECTED
 result={'variant':x.variant,'status':'INCOMPLETE','recipe_sha256':sha(__file__),'reference_sha256':sha(ref),'sources':{p.name:sha(p) for p in src.iterdir() if p.is_file()},'tools':{}}
 dump(out/'receipt.json',result)
 try:
  for p,h in r['toolchain'].items():
   actual=sha(p);assert actual==h,(p,actual,h);result['tools'][p]=actual
  oldout=R/'benchmark/2026-10-02-u13-single-native/.artifacts/host/baseline'
  for i,c in enumerate(r['commands'][:2]):
   argv=[s.replace('$WORKSPACES',str(W)).replace('$REPO',str(R)) for s in c['command']]
   argv=[s.replace(str(oldsrc),str(src)).replace(str(oldout),str(out)) for s in argv]
   if i==0:
    # Preserve recorded DWARF identities while compiling the isolated source bytes.
    argv[1:1]=['-fdebug-compilation-dir='+str(R),'-ffile-prefix-map='+str(src)+'='+str(oldsrc),'-fdebug-prefix-map='+str(src)+'='+str(oldsrc)]
   else:argv.append('-Wl,--trace')
   run(out,'compile' if i==0 else 'link',argv,D)
  p=out/'appspawn-x-candidate1';result['artifact']={'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
  if x.variant=='baseline':assert sha(p)==EXPECTED,('BASELINE_MISMATCH',sha(p),EXPECTED)
  result['status']='BASELINE_EXACT' if x.variant=='baseline' else 'CANDIDATE_BUILT_OFFLINE'
 except Exception as e:result['error']=str(e);raise
 finally:dump(out/'receipt.json',result)
if __name__=='__main__':main()
