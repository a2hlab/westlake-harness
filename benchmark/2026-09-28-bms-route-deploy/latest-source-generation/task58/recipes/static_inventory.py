from pathlib import Path
import importlib.util,hashlib,json
R=Path.cwd();T=Path(__file__).resolve().parents[1];W=R/'bms/src/.work/b6-task58';src=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-bms/benchmark/2026-09-29-b6-static-diff/compare.py')
spec=importlib.util.spec_from_file_location('compare',src);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.ROOT=T/'static';m.ROOT.mkdir(exist_ok=True);m.LLVM=Path('/opt/homebrew/opt/llvm/bin')
for kind,name in [('host','appspawn-x'),('child','libwestlake_android_child.z.so'),('runtime-provider','libwestlake_android_runtime_provider.so')]:
 f=W/'candidate'/name;m.INPUTS[kind][1]=(f,hashlib.sha256(f.read_bytes()).hexdigest())
r,objects=m.stage1();m.stage2(r,objects)
(T/'static-tool.json').write_text(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'source':'$ORCA/workspaces/westlake-harness-bms/benchmark/2026-09-29-b6-static-diff/compare.py'},indent=2)+'\n')
print({k:v['functions']['core_counts'] for k,v in r['artifacts'].items()})
