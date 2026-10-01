"""Rebind the approved U10 host source to the actual U9 plugin and runtime identity."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
S=R/'benchmark/2026-10-01-u10-native-shims'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def bind_macros(command,generation,child_sha,child_build_id):
 values={'WLASC_PLUGIN_GENERATION_SHA_HEX':generation,'WLAR_GENERATION_SHA_HEX':generation,
         'WLASC_PLUGIN_ELF_SHA256_HEX':child_sha,'WLASC_PLUGIN_BUILD_ID_HEX':child_build_id}
 seen=set(); result=[]
 for value in command:
  match=re.match(r'-D([^=]+)=',value)
  if match and match[1] in values:
   seen.add(match[1]);value='-D'+match[1]+'="'+values[match[1]]+'"'
  result.append(value)
 assert seen==set(values),'missing identity macro'
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--workspaces',type=Path,default=os.environ.get('WORKSPACES',R.parent));p.add_argument('--out',type=Path,required=True);p.add_argument('--base',type=Path);p.add_argument('--recipe',type=Path,default=S/'evidence/host-r2/build-receipt.json');a=p.parse_args()
 w=a.workspaces.resolve();base=a.base or w/'westlake-generation-u9-j10g-238ffc14/native';a.out.mkdir(parents=True,exist_ok=False)
 record=json.loads(a.recipe.read_text());m=json.loads((base/'package.json').read_text());child=base/'payload/runtime/libwestlake_android_child.z.so'
 sdk=Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native');compiler=sdk/'llvm/bin/clang'
 assert sha(compiler)==record['compiler_sha256'],'compiler drift'
 bid=subprocess.check_output([str(sdk/'llvm/bin/llvm-readelf'),'-n',str(child)],text=True);bid=re.search(r'Build ID: ([0-9a-f]+)',bid)[1]
 assert sha(child)==m['files']['payload/runtime/libwestlake_android_child.z.so']
 def expand(v):
  return v.replace('$REPO-deploy',str(w/'westlake-harness-bms-deploy')).replace('$REPO',str(R)).replace('$WORKSPACES',str(w)).replace('$OUT',str(a.out.resolve()))
 compile_command=[expand(v) for v in record['commands'][2]]
 link_command=[expand(v) for v in record['commands'][3]]
 objects=[]
 for value in link_command:
  if value.endswith('.o') and value!=compile_command[compile_command.index('-o')+1]:
   digest=sha(value);approved={o['sha256'] for o in record['reused_objects']}
   assert digest in approved,'reused object drift: '+value
   objects.append({'path':value.replace(str(w),'$WORKSPACES'),'sha256':digest})
 compile_command=bind_macros(compile_command,m['generation'],sha(child),bid)
 runs=[]
 for n in [1,2]:
  obj=a.out/f'host-{n}.o';exe=a.out/f'appspawn-x-{n}';cc=list(compile_command);oldobj=cc[cc.index('-o')+1];cc[cc.index('-o')+1]=str(obj)
  ld=[str(obj) if v==oldobj else v for v in link_command];ld[ld.index('-o')+1]=str(exe)
  with (a.out/f'build-{n}.log').open('w') as log:
   for command in [cc,ld]:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
  portable=lambda cmd:[v.replace(str(w),'$WORKSPACES').replace(str(R),'$REPO') for v in cmd]
  runs.append({'sha256':sha(exe),'commands':[portable(cc),portable(ld)]})
 assert runs[0]['sha256']==runs[1]['sha256'],'host repeat differs'
 result={'compiler_sha256':sha(compiler),'recipe_sha256':sha(a.recipe),'source_sha256':sha(S/'visibility/candidate-stock-host.c'),'header_sha256':sha(S/'visibility/resident-compat.h'),'runtime_generation':m['generation'],'child_sha256':sha(child),'child_build_id':bid,'reused_objects':objects,'runs':runs,'repeat_identical':True,'runtime_generation_reason':'Unchanged U9 frozen runtime-provider and child retain their ABI generation; bind the actual value, never invent a new provider identity.'}
 (a.out/'host-build-receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['runtime_generation','child_sha256','child_build_id','repeat_identical']}));print(runs[0]['sha256'])
if __name__=='__main__':main()
