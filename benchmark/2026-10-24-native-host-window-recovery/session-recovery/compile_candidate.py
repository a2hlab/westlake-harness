#!/usr/bin/env python3
"""Local Mac cross-compile only. Reads sealed stage; outputs exclusively in this task."""
import argparse, hashlib, json, subprocess, sys, time, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
sys.path.insert(0,str(REPO/'scripts/lab'))
import lab_paths

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',required=True,type=Path);p.add_argument('--reader',required=True,type=Path);p.add_argument('--source-binding',type=Path);p.add_argument('--unit',choices=['wmc','input','stage','core','reader'],required=True);a=p.parse_args()
 stage=a.stage.resolve();reader=a.reader.resolve()
 out=ROOT/'.private'/('cross-'+a.unit+'-'+uuid.uuid4().hex);out.mkdir(parents=True,exist_ok=False)
 original_path=stage/'linux-compile.argv.json'
 if a.unit in ('input','stage'):
  if not a.source_binding:raise RuntimeError('Exact Input/stage source closure required')
  binding=a.source_binding.resolve();closure=binding/'.private/source-closure'
  for entry in json.loads((binding/'file-closure.json').read_text()):
   assert sha(closure/entry['destination'])==entry['sha256']
  original_path=binding/(a.unit+'.compile.argv.json')
  original=json.loads(original_path.read_text())
  cmd=[x.replace('$ORIGINAL_ROOT_0',str(closure/'ORB_WS')).replace('$ORIGINAL_ROOT_1',str(closure/'ORB_WS')) for x in original]
  cmd=[x.replace(str(closure/'ORB_WS/toolchains'),str(stage/'inputs/ORB_WS/toolchains')) for x in cmd]
 else:
  original=json.loads(original_path.read_text());cmd=original.copy()
 sources={'wmc':ROOT/'candidate/oh_window_manager_client.cpp','input':ROOT/'candidate/oh_input_bridge.cpp','stage':ROOT/'candidate/session_stage_adapter.cpp','core':ROOT/'candidate/session_recovery.cpp','reader':reader/'host_window_record_reader.cpp'}
 cmd[0]=str(stage/'mac-tools/clang++')
 for flag,value in [('-c',sources[a.unit]),('-o',out/(a.unit+'.o')),('-MF',out/(a.unit+'.d'))]:cmd[cmd.index(flag)+1]=str(value)
 cmd[1:1]=['-I'+str(ROOT/'candidate'),'-I'+str(reader), '-resource-dir', str(stage/'inputs/ORB_WS/toolchains/ohos-sdk/native/llvm/lib/clang/15.0.4')]
 pins={str(x):sha(x) for x in list((ROOT/'candidate').glob('*'))+[reader/'host_window_record_reader.h',reader/'host_window_record_reader.cpp'] if x.is_file()}
 receipt={'argv':cmd,'cwd':str(out),'source_pins':pins,'original_argv_sha256':sha(original_path),'compiler_sha256':sha(Path(cmd[0])),'changes':['Use pinned Mac T29 compiler for local candidate cross-compile, not a Linux baseline reproduction.','Prepend candidate/t1 includes; keep original restored clang-15 libcxx-ohos -isystem unchanged; select staged Clang15 resources for copied Mac driver.','Replace source/object/dep paths only; remaining flags and include order from the selected original per-unit argv.','Input/stage use source-binding-02 exact per-unit argv and all 452 closure pins; core/reader derive WMC flags as new units.'],'start_epoch':time.time()}
 (out/'command.json').write_text(json.dumps(receipt,indent=2)+'\n')
 with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
  try:rc=subprocess.run(cmd,cwd=out,stdout=stdout,stderr=stderr,timeout=120).returncode
  except subprocess.TimeoutExpired:rc=124
 receipt.update(rc=rc,end_epoch=time.time(),stdout_sha256=sha(out/'stdout'),stderr_sha256=sha(out/'stderr'))
 if rc==0:receipt['object_sha256']=sha(out/(a.unit+'.o'))
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(out);print('rc',rc);print((out/'stderr').read_text()[-6000:]);return rc
if __name__=='__main__':sys.exit(main())
