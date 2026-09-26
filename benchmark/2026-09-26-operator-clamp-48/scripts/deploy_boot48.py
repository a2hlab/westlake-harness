from pathlib import Path
import sys,json,tarfile,hashlib
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'deploy','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
R=x['R'];rt=x['rt'];d=R/'deployment';build=R/'build';dev=x['dev'];hdc=x['hdc'];manifest=json.loads((d/'boot-manifest.json').read_text());expected=manifest['expected']
assert expected['fw/adapter-runtime-bcp.jar']=='ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e'
archive=d/'clamp-fw-boot.tar'
with tarfile.open(archive,'w') as f:
 for name in expected:
  assert hashlib.sha256((build/name).read_bytes()).hexdigest()==expected[name]
  f.add(build/name,arcname=name)
remote='/data/local/tmp/operator45-crashes/clamp48-candidate'
pre=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo STOP; test -f /data/local/tmp/operator45/stop && test -f /data/local/tmp/operator45/fresh48/stop && echo STOPPED; test -f /data/local/tmp/operator45-crashes/clamp48-original/original-fw-boot.tar && echo BACKUP',10)
assert not pre.split('APP\n')[1].split('PARENT')[0].strip();assert not pre.split('PARENT\n')[1].split('STOP')[0].strip();assert 'STOPPED' in pre and 'BACKUP' in pre
assert 'CREATED' in dev('test ! -e '+remote+' || exit 9; mkdir -p '+remote+'; echo CREATED',10)
hdc(['file','send',archive.name,remote+'/clamp-fw-boot.tar'],d,50)
s=dev('tar -xf '+remote+'/clamp-fw-boot.tar -C '+remote+'; sha256sum '+' '.join(remote+'/'+n for n in expected),35)
for n,h in expected.items():assert h+'  '+remote+'/'+n in s,n
(d/'candidate-hashes.txt').write_text(s)
# The exact-original backup exists. The app and its VM parent are both stopped.
cmd='set -e; '+ '; '.join('cp '+remote+'/'+n+' '+rt+'/'+n for n in expected)+'; chown -R 20010053:20010053 '+rt+'/boot; chown 20010053:20010053 '+rt+'/fw/adapter-runtime-bcp.jar; sha256sum '+' '.join(rt+'/'+n for n in expected)
s=dev(cmd,40)
for n,h in expected.items():assert h+'  '+rt+'/'+n in s,n
(d/'deployed-hashes.txt').write_text(s)
print('DEPLOYED_JAR_AND_BOOT',len(expected),'verified',flush=True)
