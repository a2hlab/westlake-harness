from pathlib import Path
import subprocess,json,hashlib,re,os
R=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/clamp48';b=R/'build';tool=Path('/home/dspfac/a2hlab/source-closure/verify/out/host-tools/host/objects/bin/dex2oat')
names='core-oj core-libart core-icu4j conscrypt okhttp bouncycastle apache-xml framework adapter-runtime-bcp'.split()
files=[str(b/'fw'/f'{n}.jar') for n in names];locs=[f'/system/framework/{n}.jar' for n in names]
cmd=[str(tool),'--runtime-arg','-Xbootclasspath:'+':'.join(files),'--runtime-arg','-Xbootclasspath-locations:'+':'.join(locs)]
for f,l in zip(files,locs):cmd.extend(['--dex-file='+f,'--dex-location='+l])
cmd += ['--instruction-set=arm64','--compiler-filter=verify','--base=0x70000000','--image='+str(b/'boot/boot.art'),'--oat-file='+str(b/'boot/boot.oat'),'--oat-location=/system/framework/arm64/boot.oat','--android-root='+str(b/'boot'),'--runtime-arg','-Xms64m','--runtime-arg','-Xmx768m','-j4']
(b/'command.json').write_text(json.dumps(cmd,indent=2));(b/'tool-sha256.txt').write_text(hashlib.sha256(tool.read_bytes()).hexdigest()+'  '+str(tool)+'\n')
shim=Path.home()/'a2hlab/tools/libmap32bit.so'
env=dict(os.environ,LD_PRELOAD=str(shim))
(b/'host-env.json').write_text(json.dumps({'LD_PRELOAD':str(shim),'sha256':hashlib.sha256(shim.read_bytes()).hexdigest()},indent=2))
if (b/'boot-image.log').exists(): (b/'boot-image.log').rename(b/'boot-image-first-failure.log')
with (b/'boot-image.log').open('w') as f:subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1800)
expected={};versions={}
for p in sorted((b/'boot').glob('*')):
 if p.suffix not in ('.art','.oat','.vdex'):continue
 data=p.read_bytes();expected['boot/'+p.name]=hashlib.sha256(data).hexdigest()
 if p.suffix=='.oat':
  matches=re.findall(rb'oat\n([0-9]{3})\x00',data);assert matches and set(matches)=={b'247'},(p,matches)
  versions[p.name]=[s.decode() for s in matches]
assert len(expected)==27 and len(versions)==9
expected['fw/adapter-runtime-bcp.jar']=hashlib.sha256((b/'fw/adapter-runtime-bcp.jar').read_bytes()).hexdigest()
(R/'deployment/boot-manifest.json').write_text(json.dumps(dict(expected=expected,oat_versions=versions,command=cmd),indent=2))
print('BOOT_BUILD_PASS',len(expected),versions,flush=True)
