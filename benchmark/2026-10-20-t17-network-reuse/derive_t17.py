"""Offline exact T16->T17 executor derivation; no device operations."""
import argparse,hashlib,json
from pathlib import Path
b=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);a=p.parse_args()
src=a.repo/'benchmark/2026-10-20-t15-player-load-reuse/executor.py';raw=src.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='05099f6cdd68ca9903833ca88a1748803b69d28e79a493f8c573c4fffee3884b'
s=raw.decode().replace('.t16-5cd-before-','.t17-5cd-before-').replace('/data/local/tmp/t16-5cd-','/data/local/tmp/t17-5cd-')
s=s.replace('5cd R8 CAS derivation.','5cd R9 routing CAS derivation.')
old="pre=parent_guard+fg(RT+'/run.sh',expected,meta,label)"
assert s.count(old)==1
new="""network_guard=fg(RT+'/libandroid_native_network_compat.so','f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e','644:20011300:20011300',dlabel)
if not a.recovery_no_parent:network_guard+=f'test "$(stat -L -c %d:%i {RT}/libandroid_native_network_compat.so)" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/libandroid_native_network_compat.so)"\\n'
parent_guard+=network_guard
pre=parent_guard+fg(RT+'/run.sh',expected,meta,label)"""
s=s.replace(old,new);(b/'executor.py').write_text(s)
print(hashlib.sha256(s.encode()).hexdigest())
