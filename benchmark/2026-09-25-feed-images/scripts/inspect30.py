from common30 import *
import hashlib,collections
root=pathlib.Path.home()/'a2hlab/app-inputs/toutiao/lib/arm64-v8a'; readelf=A/'toolchains/ohos-sdk/native/llvm/bin/llvm-readelf'
# Only already-archived logs from this board, plus this task's baseline when available.
logs=list((R.parent/'touch25').glob('online-*/child.stderr'))+list(R.glob('baseline-*/child.stderr'))
fails=collections.defaultdict(list)
for p in logs:
 for i,s in enumerate(p.read_text(errors='replace').splitlines(),1):
  if '__ndk1' in s and 'symbol not found' in s:
   m=re.search(r'Error relocating .*?/(lib[^/ ]+\.so):',s)
   if m:fails[m[1]].append({'log':str(p),'line':i,'text':s})
rows=[]
for p in sorted(root.glob('*.so')):
 text=subprocess.check_output([str(readelf),'-d','--dyn-syms',str(p)],text=True)
 undefined=[s.split()[-1] for s in text.splitlines() if ' UND ' in s and '__ndk1' in s]
 rows.append({'library':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'needed':re.findall(r'NEEDED.*\[(.*?)\]',text),'undefined_ndk1_count':len(undefined),'first_ndk1':undefined[:4],'observed_failures':len(fails[p.name]),'example':fails[p.name][:1]})
(R/'elf-and-errors.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:
 if row['observed_failures'] or row['library'] in ['libbdheif.so','libttheif_dec.so','libgifimage.so','libimagepipeline.so','libstatic-webp.so']:print(row['library'],row['needed'],'ndk1',row['undefined_ndk1_count'],'errors',row['observed_failures'])
