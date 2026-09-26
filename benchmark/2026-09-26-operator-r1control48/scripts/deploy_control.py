"""Restore only original sscronet after original-instance cleanup; keep warm profile."""
from pathlib import Path
import sys,json,shutil,hashlib
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'deployment','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
r=x['r'];r.mkdir(parents=True,exist_ok=False);dev=x['dev'];recv=x['recv'];rt=x['rt'];R=x['R'];original='38f0dd424fabd2b92a08e0a6eb372bc464dd424b370aba23c88e39ba6374866f';guard='5ba487778a6a3be4a633b7ba5e90e0ff4e1bb6693d28c970f0e8025eb88fdb79'
pre=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo STOP; test -f /data/local/tmp/operator45/stop && test -f /data/local/tmp/operator45/fresh48/stop && test ! -d /data/local/tmp/operator45/fresh48/lock && echo STOPPED',10);(r/'preflight.txt').write_text(pre)
assert not pre.split('APP\n')[1].split('PARENT')[0].strip();assert not pre.split('PARENT\n')[1].split('STOP')[0].strip();assert 'STOPPED' in pre
for n in ['boot-manifest.json','patches.json','engines.json']:shutil.copy2(R.parent/'merged48/deployment'/n,r/n)
baseline={}
for l in (R.parent/'merged48/deployment/baseline-after.txt').read_text().splitlines():
 h,n=l.split(maxsplit=1);baseline[n]=h
before=dev('sha256sum '+' '.join(baseline),20);(r/'before-hashes.txt').write_text(before)
for n,h in baseline.items():assert h+'  '+n in before,n
f=rt+'/lib/arm64-v8a/libsscronet.so';b='/data/local/tmp/operator45-crashes/r1control48-original';source='/data/local/tmp/operator45-crashes/merged48-original/libsscronet.so'
h=dev('sha256sum '+source,10);assert original+'  '+source in h
assert 'CREATED' in dev('test ! -e '+b+' || exit 9; mkdir '+b+'; cp -p '+f+' '+b+'/libsscronet.R1GUARD48.so; echo CREATED',10)
recv(b+'/libsscronet.R1GUARD48.so',r/'original/libsscronet.R1GUARD48.so',15);assert hashlib.sha256((r/'original/libsscronet.R1GUARD48.so').read_bytes()).hexdigest()==guard
s=dev('set -e; cp '+source+' '+f+'; sha256sum '+f+'; stat -c "%i %s %a %u %g %n" '+f,15);(r/'restored-hash.txt').write_text(s);assert original+'  '+f in s
baseline[f]=original;after=dev('sha256sum '+' '.join(baseline),20);(r/'after-hashes.txt').write_text(after)
for n,h in baseline.items():assert h+'  '+n in after,n
j=json.loads((r/'engines.json').read_text());j['expected']['lib/arm64-v8a/libsscronet.so']=original;j['control_note']='Only sscronet restored; monitorcollector R5NEUTER48 retained; warm data preserved.';(r/'engines.json').write_text(json.dumps(j,indent=2));print('CONTROL_DEPLOYED',original)
