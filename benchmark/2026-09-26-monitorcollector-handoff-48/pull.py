"""Read-only, bounded HDC handoff of the exact r5 arm64 monitorcollector-lib baseline."""
from pathlib import Path
import sys,json,hashlib,struct,gzip
root=Path(__file__).resolve().parent
old=root.parent/'2026-09-26-operator-enginecheck-48'
p=old/'scripts/warm48.py';sys.argv=[str(p),'monitorcollector-lib-handoff','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
x['R']=Path.home()/'a2hlab/board'/x['S']/'monitorcollector-lib-handoff48';x['R'].mkdir(exist_ok=True)
dev=x['dev'];recv=x['recv'];rt=x['rt'];remote=rt+'/lib/arm64-v8a/libmonitorcollector-lib.so'
state=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo GUARD; test -f /data/local/tmp/operator45/stop && test -f /data/local/tmp/operator45/fresh48/stop && test ! -d /data/local/tmp/operator45/fresh48/lock && echo STOPPED; echo MAP_COUNT; cat /proc/sys/vm/max_map_count',10)
(root/'board-state.txt').write_text(state)
assert not state.split('APP\n')[1].split('PARENT')[0].strip()
assert not state.split('PARENT\n')[1].split('GUARD')[0].strip()
assert 'STOPPED' in state and '1048576' in state
before=dev('sha256sum '+remote+'; stat -c "%i %s %a %u %g %n" '+remote,10);(root/'board-before.txt').write_text(before)
recv(remote,root/'libmonitorcollector-lib.so',20)
b=(root/'libmonitorcollector-lib.so').read_bytes();sha=hashlib.sha256(b).hexdigest()
assert sha=='f3918bdc42b60a19edc3b80c4bd1c1cadc972eba286e5f1b1447505a6bff1793'
assert sha+'  '+remote in before
assert b[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',b,18)[0]==183
maps=[]
for f in (old/'evidence/engine-r5/faults').glob('*.maps*'):
 s=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()
 maps.extend(l for l in s.splitlines() if l.endswith('/libmonitorcollector-lib.so'))
assert maps and all(l.split()[4]=='137146' for l in maps)
assert '137146 '+str(len(b))+' ' in before
(root/'r5-maps-excerpts.txt').write_text('\n'.join(maps)+'\n')
after=dev('sha256sum '+remote,10);(root/'board-after.txt').write_text(after);assert sha+'  '+remote in after
expected={}
for l in (old/'evidence/final-check/final-component-hashes.txt').read_text().splitlines():
 h,path=l.split(maxsplit=1);assert path.startswith(rt+'/');expected[path]=h
s=dev('sha256sum '+' '.join(expected),20);(root/'hollow-clamp-engines-hashes.txt').write_text(s)
for path,h in expected.items():assert h+'  '+path in s,path
m=dict(board=x['S'],board_actual_path=remote,app_namespace_path='/data/local/tmp/asx/lib/arm64-v8a/libmonitorcollector-lib.so',sha256=sha,bytes=len(b),inode=137146,architecture='ELF64 little-endian AArch64',shared_path=str(root/'libmonitorcollector-lib.so'),r5_failure='musl sigaction ELF0x111954; caller under investigation',baseline_components_reverified=len(expected),scope='read-only file handoff; no start, deployment or data reset')
(root/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps(m,indent=2))
