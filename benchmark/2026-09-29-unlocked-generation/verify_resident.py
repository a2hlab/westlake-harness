#!/usr/bin/env python3
"""Read-only final v3a identities, guarded by board lock and boot identity."""
import json,sys,shlex
from pathlib import Path
R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b
s='5ea34a4500000000000000001123012c'
state=R.parent/'westlake-generation-state'/s/'e36781a9-2ba1-4804-b8e5-2a1125c39a47-74d1d6d48210.json'
d=json.loads(state.read_text());p=Path(d['package_path']);m=json.loads((p/'package.json').read_text())
assert d['status']=='active_verified' and m['variant']=='v3a'
out=Path.home()/'a2hlab/board/b68-v3a-final-identities';out.mkdir(exist_ok=False)
bd=b.Board(s,str(R.parent/'westlake-inputs/tools/hdc_mac.sh'),'mac '+str(R.parent/'westlake-inputs/tools/board_note.sh'),'cx-t0',out/'commands');bd.ready();assert bd.boot==d['boot_id']
expected=dict(m['live_hashes']);expected['/proc/'+str(d['parent_pid'])+'/exe']=m['live_hashes']['/system/bin/appspawn-x'];expected.update(d['installer_before'])
_,text=bd.shell('sha256sum '+' '.join(map(shlex.quote,expected)))
actual={line.split()[1]:line.split()[0] for line in text.splitlines() if len(line.split())==2}
assert actual==expected
receipt={'status':'verified','boot_id':bd.boot,'package':str(p),'package_sha256':b.sha(p/'package.json'),'actual':actual,'parent_pid':d['parent_pid']}
b.save(out/'result.json',receipt);b.save(E/'v3a/resident-final.json',receipt);print('PASS v3a final identities',len(actual))
