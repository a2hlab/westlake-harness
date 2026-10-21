#!/usr/bin/env python3
import argparse,json,hashlib,re,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
def run(out,n,a):
 (out/(n+'.argv.json')).write_text(json.dumps(a,indent=2)+'\n')
 with (out/(n+'.stdout')).open('wb') as o,(out/(n+'.stderr')).open('wb') as e:r=subprocess.run(a,stdout=o,stderr=e)
 (out/(n+'.rc')).write_text(str(r.returncode)+'\n')
 if r.returncode:raise RuntimeError(n+' rc='+str(r.returncode))
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);x=p.parse_args();O=x.out.resolve();O.mkdir(parents=True,exist_ok=False)
 fixtures=O/'fixtures';fixtures.mkdir()
 pkgs=set(re.findall(r'"([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)"',(D/'tests/anl_probe.c').read_text()))
 for pkg in pkgs|{'common'}:
  q=fixtures/pkg;q.mkdir(exist_ok=True);(q/'libnative.so').touch();(q/'libflutter.so').touch()
 for v in ['baseline','candidate']:
  S=D/'sources'/v;A=S/'anl';H=S/'host';source=(H/'candidate-stock-host.c').read_text();body=source[source.index('static int NamespaceNameOwned'):source.index('static uint8_t HexNibble')]
  probe=O/(v+'-host.c');probe.write_text((D/'tests/host_preamble.c').read_text()+body+(D/'tests/host_main.c').read_text())
  for kind,src in [('anl',D/'tests/anl_probe.c'),('host',probe)]:
   name=v+'-'+kind;binary=O/name
   argv=['cc','-std=c11','-D_GNU_SOURCE','-DCANDIDATE='+str(int(v=='candidate')),'-Wno-unused-function','-Wno-unused-parameter','-I'+str(D/'tests/include'),'-I'+str(A),'-I'+str(A/'include'),'-I'+str(H),str(src),'-o',str(binary)]
   run(O,name+'-compile',argv);run(O,name+'-run',[str(binary),str(fixtures)] if kind=='anl' else [str(binary)])
 (O/'results.json').write_text(json.dumps({'status':'PASS','variants':['baseline','candidate'],'anl_domain_cases_per_variant':37,'host_route_cases_per_variant':50,'source_pins':{str(f.relative_to(D)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (D/'sources').rglob('*') if f.is_file()},'boundary':'actual production C/functions, fake OH namespace callbacks; not runtime binding evidence'},indent=2)+'\n')
 print('PASS baseline/candidate actual ANL + host')
if __name__=='__main__':main()
