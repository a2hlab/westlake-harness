from pathlib import Path
import sys,json,hashlib,subprocess,shutil
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'aot'));from inspect_oat import inspect
ws=Path.home()/'a2hlab/ws/out-speed-delivery50';bundle=ws/'speed-clamp';record=json.loads((bundle/'build.json').read_text());assert record['returncode']==0
lock=json.loads((root.parent/'2026-09-26-toutiao-speed-aot/speed-lock.json').read_text());inp=json.loads((ws/'input-files.json').read_text());lock['inputs']={n:v for n,v in inp.items() if n.startswith(('fw/','boot/'))};lock['artifacts']=record['artifacts'];lock['libart_sha256']=inp['libart.so']['sha256'];lock['compiler_sha256']=record['compiler_sha256']
oat=inspect(bundle/'toutiao.odex');assert oat['oat_version']=='247' and oat['dex_file_count']==21 and oat['metadata']['compiler-filter']=='speed';assert oat['metadata']['classpath']=='PCL[]'
lock['current_build_record']=record;lock['current_oat']=oat
(root/'aot/speed-lock.json').write_text(json.dumps(lock,indent=2));R=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/speed-delivery50';r=R/'build';r.mkdir(exist_ok=True)
for n in ['build.json','build.log']:shutil.copy2(bundle/n,r/n)
(r/'oat.json').write_text(json.dumps(oat,indent=2));stage=ws/'inputs'
cmd=['bash',str(root/'aot/apply_speed_aot.sh'),str(stage),'--framework-report',str(R/'preflight/framework-report.json'),'--bundle',str(bundle)]
subprocess.run(cmd+['--dry-run'],stdout=(r/'dry-run.txt').open('w'),check=True)
subprocess.run(cmd,stdout=(r/'applied.txt').open('w'),check=True)
print(json.dumps(oat,indent=2));print('PREPARED',stage)
