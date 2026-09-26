"""Check captured runtime evidence, not just deployment configuration."""
from pathlib import Path
import json,re,sys
root=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/speed-delivery50'
checks=[]
for name in sys.argv[1:]:
 p=root/name;s=(p/'child.stderr').read_text(errors='replace');m=(p/'live.maps').read_text();st=(p/'jit-stat.txt').read_text()
 assert '20010053:20010053:700:directory' in st and 'NONSYMLINK' in st,name
 assert '[IMG] Loaded /data/local/tmp/asx/oat/arm64/toutiao.art' in s,name
 assert 'using app-private unlinked file with dual RW/RX views' in s,name
 assert 'using ART anonymous cache with RWX' not in s,name
 assert any('toutiao.odex' in l and l.split()[1]=='r-xp' for l in m.splitlines()),name
 lines=[l for l in m.splitlines() if '/code_cache/art-volatile/#' in l and '(deleted)' in l]
 inodes={l.split()[4] for l in lines};assert len(inodes)==1 and '0' not in inodes,name
 assert {'rw-s','r-xs'}.issubset({l.split()[1] for l in lines}),name
 checks.append({'name':name,'aot_image':True,'odex_rx':True,'file_jit':True,'anonymous_fallback':False,'inode':next(iter(inodes)),'directory':'20010053:20010053:700 nonsymlink'})
(root/'dynamic-check.json').write_text(json.dumps(checks,indent=2));print('PASS dynamic AOT/JIT',len(checks))
