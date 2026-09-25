from common30 import *
import hashlib
recv('/system/lib64/libc++_shared.so',R/'board-libcxx.so')
nm=A/'toolchains/ohos-sdk/native/llvm/bin/llvm-nm';rows=[]
for tag,p in [('board',R/'board-libcxx.so'),('apk',pathlib.Path.home()/'a2hlab/app-inputs/toutiao/lib/arm64-v8a/libc++_shared.so')]:
 text=subprocess.check_output([str(nm),'-D','--defined-only',str(p)],text=True)
 (R/(tag+'-libcxx-exports.txt')).write_text(text)
 rows.append({'provider':tag,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'ndk1_exports':sum('__ndk1' in x for x in text.splitlines()),'shared_weak_count_destructor':[s for s in text.splitlines() if 'shared_weak_countD2Ev' in s]})
(R/'libcxx-providers.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
