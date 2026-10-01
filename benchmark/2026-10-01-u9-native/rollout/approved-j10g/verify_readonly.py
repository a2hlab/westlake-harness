"""Strict U9 readback via the master batch transport; never applies or rolls back."""
import argparse, importlib.util, json, os, re, shlex
from pathlib import Path
H=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('u9_hook',H/'native_window.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
s=importlib.util.spec_from_file_location('master_batch',h.M/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
def main():
 p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--hdc-cmd',required=True);a=p.parse_args()
 plan=h.u.prepare(h.package(),h.W/'westlake-generation-u8-j9-t7e/native')
 services=h.service_hashes(a.serial);wanted={**plan['expected'],**services}
 board=b.Board(a.serial,a.hdc_cmd,str(h.W/'westlake-inputs/tools/board_note.sh'),'cx-t0',a.out/'readonly-final-device/commands');board.ready()
 rc,raw=board.shell('sha256sum '+' '.join(shlex.quote(v) for v in sorted(wanted))+' 2>/dev/null',required=False)
 got={m.group(2):m.group(1) for m in re.finditer(r'^([0-9a-f]{64})\s+(/\S+)$',raw,re.M)}
 absent=sorted(set(wanted)-set(got));diff={v:{'expected':sha,'actual':got.get(v)} for v,sha in wanted.items() if got.get(v)!=sha}
 core_diff={v:d for v,d in diff.items() if v in plan['expected']};service_diff={v:d for v,d in diff.items() if v in services}
 result=dict(identities=len(got),identity_assertions=len(plan['expected'])+len(services),core_identities=len(plan['expected']),service_assertions=len(services),overlapping_service_paths=sorted(set(plan['expected'])&set(services)),core_diff=core_diff,service_diff=service_diff,diff=diff,absent=absent,fingerprints=h.u.fingerprints(got,h.extended_refs(plan,a.serial)),boot_id=board.boot,transport='master bms Board read-only / explicit hdc-cmd; OrbStack unavailable')
 h.save(a.out/'final-u9.json',result)
 assert rc==0 and not diff and not absent, result
 print(json.dumps(result))

if __name__=='__main__':main()
