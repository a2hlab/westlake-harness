from pathlib import Path
import sys,json,hashlib,shutil
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'deploy','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
R=x['R'];rt=x['rt'];dev=x['dev'];hdc=x['hdc'];recv=x['recv'];root=p.parents[1];d=R/'deployment';d.mkdir(exist_ok=True)
for n in ['boot-manifest.json','patches.json']:shutil.copy2(R.parent/'clamp48/deployment'/n,d/n)
orig={'libbytehook.so':'238e7bc3e0c36247de86fe80453d596503ec0c45bc3ece578fc351d638506d61','libshadowhook.so':'88351a015be00254f961d5c559187513f8a657a40fb9d13f50b5d0733d7e9cbf'}
new={'libbytehook.so':'fbb761a0f0d16342f9c63ff94af52b7d6377fda2def7c3f14950139907ea1baa','libshadowhook.so':'34378f5c2e2f7f4b418a332018916d488fcbabdf68109836bc83b74bc6f53e3c'}
pre=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo STOP; test -f /data/local/tmp/operator45/stop && test -f /data/local/tmp/operator45/fresh48/stop && test ! -d /data/local/tmp/operator45/fresh48/lock && echo STOPPED; cat /proc/sys/vm/max_map_count',10);(d/'preflight.txt').write_text(pre)
assert not pre.split('APP\n')[1].split('PARENT')[0].strip();assert not pre.split('PARENT\n')[1].split('STOP')[0].strip();assert 'STOPPED' in pre and '1048576' in pre
baseline=json.loads((d/'boot-manifest.json').read_text())['expected'];baseline.update(json.loads((d/'patches.json').read_text())['expected']);baseline.update({'webview-t-lib/libwebview_bionic_shim.so':'85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a','lib/arm64-v8a/libnpth.so':'9966e2966057c4d7d31f81232decf58da046898b9a2be900df675d44d016a107','run.sh':'ffb324e4a6950d53d4bf991ba93f1be9e2592780c92ddcf70467e3c3bf429e15'})
s=dev('sha256sum '+' '.join(rt+'/'+n for n in baseline),20);(d/'baseline-before.txt').write_text(s)
for n,h in baseline.items():assert h+'  '+rt+'/'+n in s,n
prefix=rt+'/lib/arm64-v8a/';backup='/data/local/tmp/operator45-crashes/enginecheck48-original';candidate='/data/local/tmp/operator45-crashes/enginecheck48-candidate'
s=dev('sha256sum '+' '.join(prefix+n for n in orig)+'; stat -c "%i %s %a %u %g %n" '+' '.join(prefix+n for n in orig),10);(d/'original-hashes.txt').write_text(s)
for n,h in orig.items():assert h+'  '+prefix+n in s,n
assert 'CREATED' in dev('test ! -e '+backup+' && test ! -e '+candidate+' || exit 9; mkdir -p '+backup+' '+candidate+'; echo CREATED',10)
for n,h in orig.items():
 dev('cp -p '+prefix+n+' '+backup+'/'+n,10);recv(backup+'/'+n,d/'original'/n,15);assert hashlib.sha256((d/'original'/n).read_bytes()).hexdigest()==h
for n,h in new.items():
 f=root/'out'/n.replace('.so','.CLAMP48HOLLOW.so');assert hashlib.sha256(f.read_bytes()).hexdigest()==h
 hdc(['file','send',f.name,candidate+'/'+n],f.parent,20)
s=dev('sha256sum '+' '.join(candidate+'/'+n for n in new),10);(d/'candidate-hashes.txt').write_text(s)
for n,h in new.items():assert h+'  '+candidate+'/'+n in s
s=dev('set -e; '+ '; '.join('cp '+candidate+'/'+n+' '+prefix+n for n in new)+'; sha256sum '+' '.join(prefix+n for n in new)+'; stat -c "%i %s %a %u %g %n" '+' '.join(prefix+n for n in new),15)
(d/'deployed-hashes.txt').write_text(s)
for n,h in new.items():assert h+'  '+prefix+n in s
s=dev('sha256sum '+' '.join(rt+'/'+n for n in baseline),20);(d/'baseline-after.txt').write_text(s)
for n,h in baseline.items():assert h+'  '+rt+'/'+n in s,n
(d/'engines.json').write_text(json.dumps({'expected':{'lib/arm64-v8a/'+n:h for n,h in new.items()},'original':orig,'backup':backup,'runtime':rt},indent=2))
print('DEPLOYED_ENGINES',json.dumps(new),flush=True)
