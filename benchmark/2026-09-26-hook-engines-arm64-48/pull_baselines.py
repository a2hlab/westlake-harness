"""Read-only board61 handoff. Run through orb -m a2hlab bash -lc."""
from pathlib import Path
import sys,json,hashlib,struct,gzip
root=Path(__file__).resolve().parent
p=root.parent/'2026-09-26-operator-clamp-48/scripts/warm48.py'
sys.argv=[str(p),'handoff','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
x['R']=Path.home()/'a2hlab/board'/x['S']/'engines48';x['R'].mkdir(exist_ok=True)
rt=x['rt'];dev=x['dev'];recv=x['recv']
names=['libbytehook.so','libshadowhook.so','libjato.so','libhotfix-opt.so'];prefix=rt+'/lib/arm64-v8a/'
state=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo GUARD; test -f /data/local/tmp/operator45/stop && test -f /data/local/tmp/operator45/fresh48/stop && test ! -d /data/local/tmp/operator45/fresh48/lock && echo STOPPED; echo MAP_COUNT; cat /proc/sys/vm/max_map_count',10)
(root/'board-state.txt').write_text(state)
assert not state.split('APP\n')[1].split('PARENT')[0].strip()
assert not state.split('PARENT\n')[1].split('GUARD')[0].strip()
assert 'STOPPED' in state and '1048576' in state
before=dev('sha256sum '+' '.join(prefix+n for n in names)+'; stat -c "%i %s %n" '+' '.join(prefix+n for n in names),15)
(root/'board-hashes-before.txt').write_text(before)
items=[]
for name in names:
 recv(prefix+name,root/name,25)
 b=(root/name).read_bytes();sha=hashlib.sha256(b).hexdigest()
 assert sha+'  '+prefix+name in before,name
 assert b[:4]==b'\x7fELF' and b[4:6]==bytes([2,1])
 assert struct.unpack_from('<H',b,18)[0]==183,name
 items.append(dict(name=name,board_path=prefix+name,app_namespace_path='/data/local/tmp/asx/lib/arm64-v8a/'+name,sha256=sha,bytes=len(b),elf='ELF64 little-endian AArch64 (e_machine=183)',shared_path=str(root/name)))
after=dev('sha256sum '+' '.join(prefix+n for n in names),15)
(root/'board-hashes-after.txt').write_text(after)
for item in items:assert item['sha256']+'  '+item['board_path'] in after
baseline=json.loads((root.parent/'2026-09-26-operator-clamp-48/evidence/deployment/boot-manifest.json').read_text())['expected']
baseline.update(json.loads((root.parent/'2026-09-26-operator-clamp-48/evidence/deployment/patches.json').read_text())['expected'])
baseline.update({'webview-t-lib/libwebview_bionic_shim.so':'85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a','lib/arm64-v8a/libnpth.so':'9966e2966057c4d7d31f81232decf58da046898b9a2be900df675d44d016a107','run.sh':'ffb324e4a6950d53d4bf991ba93f1be9e2592780c92ddcf70467e3c3bf429e15'})
s=dev('sha256sum '+' '.join(rt+'/'+n for n in baseline),20);(root/'hollow-clamp-state-hashes.txt').write_text(s)
for n,h in baseline.items():assert h+'  '+rt+'/'+n in s,n
mapping={}
for round_name in ('clamp-r3','clamp-r4'):
 found=[]
 for f in (root.parent/'2026-09-26-operator-clamp-48/evidence'/round_name/'faults').glob('*.maps*'):
  text=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text()
  found.extend(l for l in text.splitlines() if any('/'+n in l for n in names))
 mapping[round_name]=found
(root/'crash-maps-excerpts.json').write_text(json.dumps(mapping,indent=2))
(root/'manifest.json').write_text(json.dumps(dict(board=x['S'],runtime=rt,files=items,baseline_components_reverified=len(baseline),scope='read-only retrieval, no deployment or process start'),indent=2))
print(json.dumps(items,indent=2),flush=True)
