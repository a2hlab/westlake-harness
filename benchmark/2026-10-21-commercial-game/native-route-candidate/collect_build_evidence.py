#!/usr/bin/env python3
"""Read completed builds; record real ELF/tool outputs and dependency identities."""
import argparse,hashlib,json,re,shlex,subprocess,os,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;W=D.parents[3];MAIN=Path(os.environ.get('G26_MAIN',W/'westlake-harness'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def alias(s):
 for p,a in sorted([(str(D),'$G26'),(str(W),'$WORKSPACES'),(str(Path.home()),'$HOME')],key=lambda x:-len(x[0])):s=s.replace(p,a)
 return s
def run(O,n,a,env=None):
 dump(O/(n+'.argv.json'),a)
 with (O/(n+'.stdout')).open('wb') as o,(O/(n+'.stderr')).open('wb') as e:r=subprocess.run(a,stdout=o,stderr=e,env=env)
 (O/(n+'.rc')).write_text(str(r.returncode)+'\n');assert r.returncode==0,(n,r.returncode)
 return (O/(n+'.stdout')).read_text()
def sym(s):
 rows=[]
 for l in s.splitlines():
  q=l.split()
  if len(q)>=8 and re.fullmatch(r'\d+:',q[0]):
   rows.append({'name':q[7],'type':q[3],'bind':q[4],'visibility':q[5],'defined':q[6]!='UND','size':int(q[2],0)})
 return rows
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',required=True,type=Path);x=a.parse_args();O=x.out.resolve();O.mkdir(parents=True,exist_ok=False)
 RE=shutil.which('llvm-readelf');OB=shutil.which('llvm-objdump');assert RE and OB
 builds={'host-baseline':D/'.private/host-baseline-01','host-candidate':D/'.private/host-candidate-01','anl-baseline':D/'.private/anl-production-01/baseline','anl-candidate':D/'.private/anl-production-01/candidate'};facts={};inputs={}
 for n,B in builds.items():
  p=B/('appspawn-x-candidate1' if n.startswith('host') else 'libapp_native_loader.so')
  dyn=run(O,n+'-dynamic',[RE,'-d','-W',str(p)]);sy=run(O,n+'-dynsym',[RE,'--dyn-syms','-W',str(p)]);run(O,n+'-versions',[RE,'--version-info','-W',str(p)])
  facts[n]={'path':alias(str(p)),'sha256':sha(p),'bytes':p.stat().st_size,'needed':re.findall(r'\(NEEDED\).*?\[(.*?)\]',dyn),'dynsym':sym(sy),'textrel':bool(re.search(r'\(TEXTREL\)',dyn))}
  for l in (B/'link.stdout').read_text().splitlines():
   name=l.strip().split('(',1)[0];f=Path(name)
   if f.is_file():inputs[alias(str(f))]={'sha256':sha(f),'bytes':f.stat().st_size,'role':'actual-link-trace'}
  for dep in B.glob('*.d'):
   txt=dep.read_text().replace('\\\n',' ');txt=txt.split(':',1)[1]
   for name in shlex.split(txt):
    f=Path(name)
    if not f.is_absolute():f=D/f
    assert f.is_file(),name
    inputs[alias(str(f))]={'sha256':sha(f),'bytes':f.stat().st_size,'role':'compile-dependency'}
  run(O,n+'-disassembly',[OB,'-d','--no-show-raw-insn',str(p)])
 comparisons={}
 for k in ['host','anl']:
  old=facts[k+'-baseline'];new=facts[k+'-candidate'];signature=lambda rows:sorted((r['name'],r['type'],r['bind'],r['visibility'],r['size'] if r['type'] in ('OBJECT','TLS') else None,r['defined']) for r in rows)
  comparisons[k]={'dynamic_abi_equal':signature(old['dynsym'])==signature(new['dynsym']),'needed_order_equal':old['needed']==new['needed'],'dynamic_symbols':len(new['dynsym']),'needed_count':len(new['needed']),'textrel':new['textrel']};assert comparisons[k]['dynamic_abi_equal'] and comparisons[k]['needed_order_equal'] and not new['textrel']
  env=dict(os.environ,PATH='/opt/homebrew/bin:'+os.environ['PATH']);run(O,k+'-abi-diff',['python3',str(MAIN/'scripts/lab/abi_diff.py'),'--old',str(builds[k+'-baseline']/('appspawn-x-candidate1' if k=='host' else 'libapp_native_loader.so')),'--new',str(builds[k+'-candidate']/('appspawn-x-candidate1' if k=='host' else 'libapp_native_loader.so')),'--json',str(O/(k+'-abi-diff.json'))],env)
 # Exact game and existing provider, no modification or execution of either.
 C=Path.home()/'.local/share/westlake/commercial-game-20261021/g21-rollout-01/candidate/native/payload/android/lib64'
 provider={}
 for rel in ['libmediandk.so','westlake_native/libwestlake_native_abi.so','westlake_native/libandroid.so','westlake_native/libGLESv2.so','westlake_native/libz.so']:
  p=C/rel;n=rel.replace('/','-');dy=run(O,n+'-dynamic',[RE,'-d','-W',str(p)]);sy=run(O,n+'-dynsym',[RE,'--dyn-syms','-W',str(p)])
  provider[rel]={'path':alias(str(p)),'sha256':sha(p),'needed':re.findall(r'\(NEEDED\).*?\[(.*?)\]',dy),'dynsym':sym(sy)}
 game=D.parent/'exact-static/.private/g04-01/scan/members/lib/arm64-v8a/libyuanshen.so';gy=run(O,'yuanshen-dynsym',[RE,'--dyn-syms','-W',str(game)])
 gs=sym(gy);ps=provider['westlake_native/libwestlake_native_abi.so']['dynsym'];matches=[]
 for n in ['__register_atfork','__FD_SET_chk','__FD_ISSET_chk']:
  imp=[r for r in gs if r['name'].split('@')[0]==n and not r['defined']];exp=[r for r in ps if r['name'].split('@')[0]==n and r['defined']];assert len(imp)==len(exp)==1 and imp[0]['name'].endswith('@LIBC') and exp[0]['name'].endswith('@@LIBC');matches.append({'symbol':n,'import':imp[0],'export':exp[0]})
 dump(O/'elf-facts.json',{'builds':facts,'comparisons':comparisons,'providers':provider,'game_sha256':sha(game),'core_libc_matches':matches,'runtime_binding':'UNKNOWN'})
 dump(O/'actual-inputs.json',inputs)
 print(json.dumps(comparisons));print('actual input paths',len(inputs))
if __name__=='__main__':main()
