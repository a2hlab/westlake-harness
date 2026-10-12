#!/usr/bin/env python3
"""Local original clang15 OH recipe, with immutable per-build raw receipts."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
 out=args.out.resolve()
 if out.exists():raise ValueError('new output required to preserve raw build logs')
 out.mkdir(parents=True)
 sdk=Path(os.environ.get('OH_NATIVE_SDK','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native'))
 cc=sdk/'llvm/bin/clang-15';ld=sdk/'llvm/bin/ld.lld';libc=sdk/'sysroot/usr/lib/aarch64-linux-ohos/libc.so'
 expected={cc:'6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1',ld:'489c6d6628a56c027eac4dceee87910f7ca28b0c5a0e5188c32cb0108c08a837',libc:'52595999ac564b16befc9d88cc484a5866938f7dcb87de617f50090102269ada'}
 for p,h in expected.items():assert sha(p)==h,str(p)
 host=Path(subprocess.check_output(['xcrun','--find','clang'],text=True).strip())
 host_sdk=Path(subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip())
 inputs=[cc,ld,libc,host,host_sdk/'usr/include/stdio.h',*sorted((HERE/'src').iterdir())]
 (out/'inputs.json').write_text(json.dumps([{'path':str(p),'sha256':sha(p)} for p in inputs],indent=2)+'\n')
 jobs=[('arm',[str(cc),'--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-O2','-fno-math-errno',str(HERE/'src/screen_gate_feed.c'),'-o',str(out/'screen-gate-feed'),'-lm']),
       ('host',[str(host),'-isysroot',str(host_sdk),'-O2','-fno-math-errno',str(HERE/'src/screen_gate_feed.c'),'-o',str(out/'screen-gate-host'),'-lm']),
       ('baseline-host',[str(host),'-isysroot',str(host_sdk),'-O2','-fno-math-errno',str(HERE/'src/baseline_feed.c'),'-o',str(out/'baseline-host'),'-lm'])]
 receipts=[]
 for name,argv in jobs:
  with (out/(name+'.stdout')).open('wb') as stdout,(out/(name+'.stderr')).open('wb') as stderr:
   completed=subprocess.run(argv,stdout=stdout,stderr=stderr)
  (out/(name+'.exit')).write_text(str(completed.returncode)+'\n')
  receipt={'name':name,'argv':argv,'rc':completed.returncode};receipts.append(receipt)
  (out/'commands.json').write_text(json.dumps(receipts,indent=2)+'\n')
  if completed.returncode:raise SystemExit(completed.returncode)
 outputs={name:sha(out/name) for name in ['screen-gate-feed','screen-gate-host','baseline-host']}
 (out/'outputs.json').write_text(json.dumps(outputs,indent=2)+'\n');print(json.dumps(outputs))
if __name__=='__main__':main()
