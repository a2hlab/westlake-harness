from pathlib import Path
import json,importlib.util,subprocess
R=Path.cwd();O=R/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer';D=O/'5ea-base-recovery/dir-repair';D.mkdir();(D/'logs').mkdir();rows=json.loads((O/'ancestor-metadata-diff.json').read_text());assert len(rows)==10
s=importlib.util.spec_from_file_location('ex',R/'benchmark/2026-10-12-recovery-executor/executor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);serial='5ea34a4500000000000000001123012c';dev=m.Device({'serial':serial,'hdc':'/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','tools':{'driver':{'path':str(R/'scripts/lab/demo_seal_61b.py')}}},D/'logs')
assert subprocess.check_output(['bash','scripts/lab/board_note.sh','held',serial],text=True).startswith('outer(codex) ')
assert dev.shell('boot','cat /proc/sys/kernel/random/boot_id')=='b30e29aa-c26d-49b3-8bda-4ec6faa6b1a2'
script=['#!/system/bin/sh','set -eu'];paths=[]
for row in rows:
 p,before=row['5ea'].split(':',1);p2,after=row['5cd'].split(':',1);assert p==p2 and p.startswith('/system/android') and before.startswith('750:0:0:') and after=='755'+before[3:]
 src='/data/westlake-demo/u13/sources/seq1'+p[len('/system/android'):];paths.append((p,src,before,after))
 for x in (p,src):script+=['test ! -L '+m.q(x),'test -d '+m.q(x),'test "$(stat -c %a:%u:%g:%C '+m.q(x)+')" = '+m.q(before)]
 script+=['test "$(stat -c %d:%i '+m.q(p)+')" = "$(stat -c %d:%i '+m.q(src)+')"']
for p,src,before,after in paths:script+=['chmod 755 '+m.q(src),'test "$(stat -c %a:%u:%g:%C '+m.q(p)+')" = '+m.q(after)]
script+=['echo EXACT_10_DIRECTORY_METADATA_RESTORED'];script='\n'.join(script)+'\n';(D/'apply.sh').write_text(script);(D/'authorization.json').write_text(json.dumps({'approved_by':'outer(codex)','serial':serial,'boot_id':'b30e29aa-c26d-49b3-8bda-4ec6faa6b1a2','reason':'all319SHA equal but baseline app child errno13; compare actual31 ancestors against healthy5cd shows exact10 owner-only traverse differences','rows':rows,'scope':'source directory modes750->755 only; no file bytes or labels changes; no reboot'},indent=2)+'\n');print(dev.shell('exact-mode-repair',script));(D/'receipt.json').write_text(json.dumps({'status':'PASS','paths':paths},indent=2)+'\n')
