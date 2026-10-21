import json,os,subprocess,hashlib,time,sys
from pathlib import Path
src=Path(sys.argv[1]);out=Path(sys.argv[2]);r=json.loads((src/'receipt.json').read_text());step=next(x for x in r['steps'] if x['tag']=='baseline-compile');a=step['argv'];a.insert(2,'-fdebug-compilation-dir=/opt/build-trees/oh610_lts_source/out/wukong100');env=dict(os.environ);env.update(step['env']);out.mkdir(exist_ok=True)
(out/'argv.json').write_text(json.dumps({'argv':a,'cwd':step['cwd'],'env':step['env'],'start':time.time()},indent=2))
with (out/'stdout').open('wb') as o,(out/'stderr').open('wb') as e:q=subprocess.run(a,cwd=step['cwd'],env=env,stdout=o,stderr=e)
obj=Path(step['cwd'])/a[a.index('-o')+1];b=obj.read_bytes();(out/'zip_file.o').write_bytes(b);result={'rc':q.returncode,'object_sha256':hashlib.sha256(b).hexdigest(),'expected':'2e2a6247d73b981cc530653a411f7b29f531eabac19a1c564e8c30391eb8481b','end':time.time()};result['match']=result['object_sha256']==result['expected'];(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
