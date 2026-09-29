#!/usr/bin/env python3
"""Copy the existing OH compile/link rules into a private two-object build graph."""
from pathlib import Path
import json,posixpath,re,shlex
E=Path(__file__).resolve().parent
K=Path('/Users/zhaoyue/orca/workspaces/oh61-bms-kit-b79')
O=K/'out/wukong100'; O.mkdir(parents=True,exist_ok=True)
t=E/'inputs/toolchain.ninja'
with t.open() as f:
 rules=[]
 for line in f:
  if line.startswith('rule solink_module'):break
  rules.append(line)
t.write_text(''.join(rules))
# Reuse cxx/solink rules; only remove the post-link mini-debug packaging wrapper.
text=t.read_text(); solink=next(x for x in text.splitlines() if x.startswith('  command = /usr/bin/env') and 'gcc_solink_wrapper' in x)
new='  command = '+solink.split(' -- ',1)[1]+' && ../../prebuilts/clang/ohos/linux-x86_64/llvm/bin/llvm-strip -o ${output_dir}/${target_output_name}${output_extension} ${root_out_dir}/lib.unstripped/${output_dir}/${target_output_name}${output_extension}'
text=text.replace(solink,new)
(O/'rules.ninja').write_text(text)
files=set(); recipes={}
def add(p):
 if p.startswith('-'):return
 p=posixpath.normpath('out/wukong100/'+p)
 if p.startswith('../'):raise ValueError(p)
 files.add(p)
for line in (E/'remote-compile-deps.txt').read_text().splitlines():
 if line.startswith('    '):add(line.strip())
for name,needle in [('libbms','base_bundle_installer.o'),('installs','installd_operator.o')]:
 raw=(E/f'inputs/{name}.ninja').read_text();lines=raw.splitlines(); globals=[];obj=[];link=[]
 for line in lines:
  if line.startswith('build '):break
  globals.append(line)
 for i,line in enumerate(lines):
  if line.startswith('build ') and ((': cxx ' in line and needle in line.split(':')[0]) or ': solink ' in line):
   block=[line];j=i+1
   while j<len(lines) and lines[j].startswith('  '):block.append(lines[j]);j+=1
   if ': cxx ' in line:obj=block
   else:link=block
 assert obj and link,name
 # Keep exact explicit inputs; generated dependency stamps are not build targets here.
 for block in [obj,link]:
  block[0]=re.split(r' \|\|? ',block[0])[0]
  for token in shlex.split(block[0].split(': ',1)[1])[1:]:add(token)
 for line in link[1:]:
  if line.strip().startswith(('libs =','solibs =')):
   for token in shlex.split(line.split('=',1)[1]):add(token)
 narrow='\n'.join(globals+obj+link)+'\n'
 extra=E/'apk-route-build-edges.txt'
 if name=='libbms' and extra.exists():narrow=narrow.replace('build bundlemanager/bundle_framework/libbms.z.so',extra.read_text()+'\nbuild bundlemanager/bundle_framework/libbms.z.so')
 (O/f'{name}.ninja').write_text(narrow)
 target=link[0].split(':')[0][6:];object_=obj[0].split(':')[0][6:]
 recipes[name]={'target':target,'object':object_,'source':obj[0].split(': cxx ')[1].split()[0]}
 add(object_)
for p in ['../../foundation/bundlemanager/bundle_framework/services/bundlemgr/libbms.map','../../build/config/sanitizers/cfi.versionscript']:
 add(p)
# Full musl headers/libraries and matching C++ headers avoid replacing ABI inputs with SDK guesses.
files.update(['out/wukong100/obj/third_party/musl/usr','prebuilts/clang/ohos/linux-x86_64/llvm/include','prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4','prebuilts/clang/ohos/linux-x86_64/llvm/lib/aarch64-linux-ohos'])
(E/'copy-paths.txt').write_text('\n'.join(sorted(files))+'\n')
(E/'recipes.json').write_text(json.dumps(recipes,indent=2)+'\n')
(O/'build.ninja').write_text('root_out_dir = .\npool build_toolchain_link_pool\n  depth = 1\ninclude rules.ninja\nsubninja libbms.ninja\nsubninja installs.ninja\n')
print(len(files),'copy paths; recipes',recipes)
