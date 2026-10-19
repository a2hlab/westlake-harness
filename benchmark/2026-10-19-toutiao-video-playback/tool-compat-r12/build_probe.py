#!/usr/bin/env python3
"""Local OH cross-build only. No deployment/connection. Persist every command."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--sdk',required=True);p.add_argument('--out',required=True);p.add_argument('--source-repo',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
 sdk=Path(a.sdk).resolve();out=Path(a.out).resolve();repo=Path(a.source_repo).resolve()
 cmd=[str(sdk/'llvm/bin/clang'),'--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-O0','-g','-fPIE','-pie','-Wall','-Wextra','-Werror','-Wl,--build-id=sha1',str(HERE/'probe.c'),'-o',str(out/'probe')]
 if not a.run:print(json.dumps({'command':cmd,'device_calls':0}));return
 if str(out).startswith(('/tmp/','/private/tmp/')):raise SystemExit('persistent OUT required')
 out.mkdir(parents=True,exist_ok=False);(out/'raw').mkdir()
 def step(name,argv):
  (out/'raw'/f'{name}.command.json').write_text(json.dumps(argv,indent=2)+'\n')
  with (out/'raw'/f'{name}.stdout.txt').open('wb') as o,(out/'raw'/f'{name}.stderr.txt').open('wb') as e:r=subprocess.run(argv,stdout=o,stderr=e)
  (out/'raw'/f'{name}.rc').write_text(str(r.returncode)+'\n')
  if r.returncode:raise SystemExit(name+' failed '+str(r.returncode))
 step('00-frozen',['python3',str(repo/'scripts/lab/check_frozen.py'),'--git',str(repo),'--registry',str(repo/'knowledge/frozen/frozen.json')])
 tools={n:{'path':str(sdk/q),'sha256':H(sdk/q)} for n,q in {'clang':'llvm/bin/clang','lld':'llvm/bin/ld.lld','readelf':'llvm/bin/llvm-readelf','libc':'sysroot/usr/lib/aarch64-linux-ohos/libc.so'}.items()}
 (out/'tools.json').write_text(json.dumps(tools,indent=2)+'\n')
 step('01-version',[str(sdk/'llvm/bin/clang'),'--version']);step('02-build',cmd)
 step('03-elf',[str(sdk/'llvm/bin/llvm-readelf'),'-h','-l','-d','-s',str(out/'probe')])
 marker=[]
 for line in (out/'raw/03-elf.stdout.txt').read_text().splitlines():
  f=line.split()
  if len(f)>=8 and f[-1]=='r12_marker' and f[3]=='FUNC':marker.append(int(f[1],16))
 if len(set(marker))!=1:raise SystemExit('marker not unique')
 receipt={'schema':'r12-probe-build-v1','source_sha256':H(HERE/'probe.c'),'recipe_sha256':H(__file__),'probe_sha256':H(out/'probe'),'probe_bytes':(out/'probe').stat().st_size,'marker_elf':marker[0],'build_rc':0,'tools':tools,'raw':{str(f.relative_to(out)):H(f) for f in sorted((out/'raw').iterdir())},'device_calls':0,'probe_execution':'NOT_EXECUTED'}
 (out/'build.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'out':str(out),'probe_sha256':receipt['probe_sha256'],'marker_elf':hex(marker[0])}))
if __name__=='__main__':main()
