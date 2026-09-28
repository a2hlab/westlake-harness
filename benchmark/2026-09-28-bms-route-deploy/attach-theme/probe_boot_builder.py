"""Offline feasibility only: build an unchanged boot cohort with the recovered host tool."""
from pathlib import Path
import subprocess,json,hashlib,os
r=Path(__file__).resolve().parent
root=Path('/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b6')
out=root/'baseline-boot-probe-map32';out.mkdir(exist_ok=False)
tool=Path('/Users/zhaoyue/workspace/hanbin_adapter/out/host-tools/dex2oat64')
f=Path('/Users/zhaoyue/orca/workspaces/westlake-bms-suite/.bridge-payload/pr03-74e6-portable/android/framework')
names=['core-oj','core-libart','core-icu4j','okhttp','bouncycastle','apache-xml','adapter-mainline-stubs','framework','oh-adapter-framework']
args=[str(tool),'--android-root=/system','--instruction-set=arm64','--base=0x70000000','--compiler-filter=speed','--runtime-arg','-Xms64m','--runtime-arg','-Xmx512m','--runtime-arg','-Xverify:none','--image='+str(out/'boot.art'),'--oat-file='+str(out/'boot.oat')]
for name in names:args+=['--dex-file='+str(f/(name+'.jar')),'--dex-location=/system/android/framework/'+name+'.jar']
p=subprocess.run(args,stdout=(out/'stdout.log').open('w'),stderr=(out/'stderr.log').open('w'),timeout=180,env=dict(os.environ,LD_PRELOAD='/home/zhaoyue/a2hlab/tools/libmap32bit.so'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'command':args,'tool_sha256':sha(tool),'return_code':p.returncode,'deployed':False,'vm_output':str(out),'outputs':{p.name:sha(p) for p in out.glob('boot*')},'oat_versions':{p.name:p.read_bytes()[p.read_bytes().index(b'oat\n')+4:][:3].decode() for p in out.glob('*.oat') if b'oat\n' in p.read_bytes()}}
(r/'boot-builder-probe.json').write_text(json.dumps(result,indent=2)+'\n');print(result);print((out/'stderr.log').read_text()[-2000:])
