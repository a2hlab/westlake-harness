from pathlib import Path
import sys,json,hashlib,shutil
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'deploy','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
R=x['R'];rt=x['rt'];dev=x['dev'];hdc=x['hdc'];recv=x['recv'];root=p.parents[1];d=R/'deployment';d.mkdir(exist_ok=True)
old=R.parent/'enginecheck48/deployment'
for n in ['boot-manifest.json','patches.json','engines.json']:shutil.copy2(old/n,d/n)
orig={'libmonitorcollector-lib.so':'f3918bdc42b60a19edc3b80c4bd1c1cadc972eba286e5f1b1447505a6bff1793','libsscronet.so':'38f0dd424fabd2b92a08e0a6eb372bc464dd424b370aba23c88e39ba6374866f'}
new={'libmonitorcollector-lib.so':'8c97ef7cd666517e92c0a79a9471518afff0133a891f775d5291a557cdbacf31','libsscronet.so':'5ba487778a6a3be4a633b7ba5e90e0ff4e1bb6693d28c970f0e8025eb88fdb79'}
files={'libmonitorcollector-lib.so':'libmonitorcollector-lib.R5NEUTER48.so','libsscronet.so':'libsscronet.R1GUARD48.so'}
pre=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo STOP; test -f /data/local/tmp/operator45/stop && test -f /data/local/tmp/operator45/fresh48/stop && test ! -d /data/local/tmp/operator45/fresh48/lock && echo STOPPED; cat /proc/sys/vm/max_map_count',10);(d/'preflight.txt').write_text(pre)
assert not pre.split('APP\n')[1].split('PARENT')[0].strip();assert not pre.split('PARENT\n')[1].split('STOP')[0].strip();assert 'STOPPED' in pre and '1048576' in pre
baseline={}
for l in (root.parent/'2026-09-26-operator-enginecheck-48/evidence/final-check/final-component-hashes.txt').read_text().splitlines():
 h,n=l.split(maxsplit=1);baseline[n]=h
s=dev('sha256sum '+' '.join(baseline),20);(d/'baseline-before.txt').write_text(s)
for n,h in baseline.items():assert h+'  '+n in s,n
prefix=rt+'/lib/arm64-v8a/';backup='/data/local/tmp/operator45-crashes/merged48-original';candidate='/data/local/tmp/operator45-crashes/merged48-candidate'
s=dev('sha256sum '+' '.join(prefix+n for n in orig)+'; stat -c "%i %s %a %u %g %n" '+' '.join(prefix+n for n in orig),10);(d/'original-hashes.txt').write_text(s)
for n,h in orig.items():assert h+'  '+prefix+n in s,n
assert 'CREATED' in dev('test ! -e '+backup+' && test ! -e '+candidate+' || exit 9; mkdir -p '+backup+' '+candidate+'; echo CREATED',10)
for n,h in orig.items():
 dev('cp -p '+prefix+n+' '+backup+'/'+n,10);recv(backup+'/'+n,d/'original'/n,15);assert hashlib.sha256((d/'original'/n).read_bytes()).hexdigest()==h
for n,h in new.items():
 f=root/'out'/files[n];assert hashlib.sha256(f.read_bytes()).hexdigest()==h
 hdc(['file','send',f.name,candidate+'/'+n],f.parent,20)
s=dev('sha256sum '+' '.join(candidate+'/'+n for n in new),10);(d/'candidate-hashes.txt').write_text(s)
for n,h in new.items():assert h+'  '+candidate+'/'+n in s
s=dev('set -e; '+ '; '.join('cp '+candidate+'/'+n+' '+prefix+n for n in new)+'; sha256sum '+' '.join(prefix+n for n in new)+'; stat -c "%i %s %a %u %g %n" '+' '.join(prefix+n for n in new),15);(d/'deployed-hashes.txt').write_text(s)
for n,h in new.items():assert h+'  '+prefix+n in s
baseline.update({prefix+n:h for n,h in new.items()})
s=dev('sha256sum '+' '.join(baseline),20);(d/'baseline-after.txt').write_text(s)
for n,h in baseline.items():assert h+'  '+n in s,n
j=json.loads((d/'engines.json').read_text());j['expected'].update({'lib/arm64-v8a/'+n:h for n,h in new.items()});j['merged_original']=orig;j['merged_backup']=backup;(d/'engines.json').write_text(json.dumps(j,indent=2))
print('DEPLOYED_MERGED_PATCHES',json.dumps(new),flush=True)
