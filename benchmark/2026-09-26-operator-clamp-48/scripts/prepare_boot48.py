"""Read actual BCP; preserve board fw+boot before any replacement. Run in a2hlab."""
from pathlib import Path
import sys,json,hashlib,shutil,tarfile
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'prebuild','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
R=x['R'];rt=x['rt'];dev=x['dev'];recv=x['recv'];d=R/'deployment';d.mkdir(exist_ok=True)
backup='/data/local/tmp/operator45-crashes/clamp48-original'
pre=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo STOP; test -f /data/local/tmp/operator45/stop && test -f /data/local/tmp/operator45/fresh48/stop && test ! -d /data/local/tmp/operator45/fresh48/lock && echo STOPPED; cat /proc/sys/vm/max_map_count',10)
(d/'preflight.txt').write_text(pre)
assert not pre.split('APP\n')[1].split('PARENT')[0].strip()
assert not pre.split('PARENT\n')[1].split('STOP')[0].strip()
assert 'STOPPED' in pre and '1048576' in pre
s=dev(f'test ! -e {backup} || exit 9; mkdir -p {backup}; cp -a {rt}/fw {rt}/boot {backup}/; sha256sum {backup}/fw/*.jar {backup}/boot/* > {backup}/SHA256SUMS; tar -cf {backup}/original-fw-boot.tar -C {backup} fw boot; cat {backup}/SHA256SUMS',50)
(d/'board-backup-hashes.txt').write_text(s)
recv(backup+'/original-fw-boot.tar',d/'original-fw-boot.tar',50)
recv(backup+'/SHA256SUMS',d/'SHA256SUMS.original',10)
original=d/'original';original.mkdir()
with tarfile.open(d/'original-fw-boot.tar') as f:
 assert all(m.name.startswith(('fw/','boot/')) or m.name in ('fw','boot') for m in f.getmembers())
 f.extractall(original,filter='data')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for line in s.splitlines():
 h,name=line.split(None,1);p=original/name.removeprefix(backup+'/');assert sha(p)==h,name
assert sha(original/'fw/adapter-runtime-bcp.jar')=='5731db00562e3b814cfb4d4e32703c40c9e8726a022b28da155fd040fb59019a'
patched=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-hollow48/benchmark/2026-09-26-operator-layout79fix-48/out/adapter-runtime-bcp.CLAMP48.jar')
assert sha(patched)=='ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e'
build=R/'build';build.mkdir();shutil.copytree(original/'fw',build/'fw');shutil.copy2(patched,build/'fw/adapter-runtime-bcp.jar');(build/'boot').mkdir()
shutil.copy2(R.parent/'hollow48/deployment/patches.json',d/'patches.json')
(d/'provenance.json').write_text(json.dumps(dict(board_backup=backup,runtime=rt,patched_jar=str(patched),patched_sha256=sha(patched),original_sha256=sha(original/'fw/adapter-runtime-bcp.jar')),indent=2))
print('BACKUP_AND_INPUTS_VERIFIED',backup,build,flush=True)
