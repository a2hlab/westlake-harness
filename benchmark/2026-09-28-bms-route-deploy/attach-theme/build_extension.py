"""Preserve original core images and rebuild only the two framework extensions."""
from pathlib import Path
import subprocess,json,hashlib,os
r=Path(__file__).resolve().parent
root=Path('/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b6')
out=root/'extension-boot';out.mkdir(exist_ok=False)
tool=Path('/Users/zhaoyue/workspace/hanbin_adapter/out/host-tools/dex2oat64')
f=Path('/Users/zhaoyue/orca/workspaces/westlake-bms-suite/.bridge-payload/pr03-74e6-portable/android/framework')
names=['core-oj','core-libart','core-icu4j','okhttp','bouncycastle','apache-xml','adapter-mainline-stubs','framework','oh-adapter-framework']
args=[str(tool),'--android-root=/system','--instruction-set=arm64','--base=0x70000000','--compiler-filter=speed','--runtime-arg','-Xms64m','--runtime-arg','-Xmx512m','--runtime-arg','-Xverify:none','--image='+str(out/'boot.art'),'--oat-file='+str(out/'boot.oat')]
args=[a for a in args if not a.startswith('--base=')]
args=[a.replace('/boot.art','/boot-framework.art').replace('/boot.oat','/boot-framework.oat') for a in args]
args += ['--boot-image='+str(f/'arm64/boot.art'),'--runtime-arg','-Xbootclasspath:'+':'.join(str(f/(n+'.jar')) for n in names[:7]),'--runtime-arg','-Xbootclasspath-locations:'+':'.join('/system/android/framework/'+n+'.jar' for n in names[:7])]
for name in names[7:]:args+=['--dex-file='+str(root/'framework-fixed-v2/framework.jar' if name=='framework' else f/(name+'.jar')),'--dex-location=/system/android/framework/'+name+'.jar']
p=subprocess.run(args,stdout=(out/'stdout.log').open('w'),stderr=(out/'stderr.log').open('w'),timeout=180,env=dict(os.environ,LD_PRELOAD='/home/zhaoyue/a2hlab/tools/libmap32bit.so'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'command':args,'tool_sha256':sha(tool),'return_code':p.returncode,'deployed':False,'vm_output':str(out),'outputs':{p.name:sha(p) for p in out.glob('boot*')},'oat_versions':{p.name:p.read_bytes()[p.read_bytes().index(b'oat\n')+4:][:3].decode() for p in out.glob('*.oat') if b'oat\n' in p.read_bytes()}}
(r/'build-extension.json').write_text(json.dumps(result,indent=2)+'\n');print(result);print((out/'stderr.log').read_text()[-2000:])
