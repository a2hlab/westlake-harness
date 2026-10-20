#!/usr/bin/env python3
"""Reproduce the narrow 61b successor; never edits the frozen T30 source."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

ORIGIN = "benchmark/2026-10-20-t30-request-recovery/deployment/final-01"
ORIGIN_SHA = "693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb"

def derive(source):
    assert hashlib.sha256(source.encode()).hexdigest() == ORIGIN_SHA
    s = source
    for old, new in [
        ("5cd T21", "61b T34"),
        ("5cd1e3dd00000000000000000923012c", "61b0657200000000000000000324012c"),
        ("20011300", "20011206"),
        ("PENDING_5CD", "EXTERNAL_REVIEW_REQUIRED_61B"),
        ("19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152",
         "91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e"),
        ("restore-v1-5cd-20261012", "icon-manual-20261019-r2"),
        ("t21-5cd", "t34-61b"),
        ("run5cd.before.reference.sh", "run61b.before.reference.sh"),
        ("run5cd.after.wid29.reference.sh", "run61b.after.reference.sh"),
    ]:
        assert old in s, old
        s = s.replace(old, new)
    def change(old, new):
        nonlocal s
        assert s.count(old) == 1, (old, s.count(old))
        s = s.replace(old, new)
    change("('out','apply-plan','repo','inputs','admission')",
           "('out','apply-plan','repo','inputs','admission','data','origin-admission')")
    change("a.out,a.repo,a.inputs,a.admission,a.start",
           "a.out,a.repo,a.inputs,a.admission,a.start,a.data")
    change("here=Path(__file__).resolve().parent", """here=a.data.resolve()
params=json.loads((here/'parameters.json').read_text())
assert params['status']=='FRESH_DATA_BOUND_NOT_AUTHORIZED','fresh data not reviewed'
assert params['serial']=='61b0657200000000000000000324012c' and params['uid']==20011206
REFERENCE_WID=params['run_derivation']['wid']
assert isinstance(REFERENCE_WID,int) and 0<REFERENCE_WID<2147483648
assert params['runtime']=='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
""")
    change("assert ad['holder']==a.holder and ad['window_start']==a.start and ad['boot']==a.boot",
           """assert ad['holder']==a.holder and ad['window_start']==a.start and ad['boot']==a.boot
assert re.fullmatch(r'inner\\(cc-video\\) [1-9][0-9]* [^ ]+',a.holder),'only delegated cc-video holder'
assert ad['deployment_scope']=='T34_61B_VIDEO'
assert ad['fresh_data_sha256']==sha_file(here/'fresh.json')
assert ad['wid']==REFERENCE_WID
assert ad['directory_identities']==params['directory_identities']
assert ad['protected_directories']==params['protected_directories']
assert ad['physical_only']==a.recovery_no_parent
if a.recovery_no_parent:
 assert ad['parent'] is None and ad['host'] is None,'physical recovery must not claim live identities'
else:
 assert str(ad['parent']['pid'])==a.parent and str(ad['parent']['birth'])==a.birth and ad['parent']['uid']==0,'admitted exact parent'
""")
    change("assert a.apply_plan and sha_file(a.apply_plan)==ad['origin_apply_plan_sha256'],'original apply-plan admission'",
           """assert a.apply_plan and sha_file(a.apply_plan)==ad['origin_apply_plan_sha256'],'original apply-plan admission'
 assert a.origin_admission and sha_file(a.origin_admission)==json.loads(a.apply_plan.read_text())['admission_sha256'],'original apply admission'
 origin_ad=json.loads(a.origin_admission.read_text())
 assert origin_ad['deployment_scope']=='T34_61B_VIDEO' and origin_ad['approved_by']=='outer(codex)'
 for key in ('executor_sha256','parameters_sha256','source_pins_sha256','readonly_inputs_sha256','fresh_data_sha256','holder','window_start'):
  assert origin_ad[key]==ad[key],('origin admission drift',key)
""")
    change("m=matches[0];return data[:m.start()]+b'export WL_PARENT_ID=29\\n'+data[m.end():],int(m[1])",
           "m=matches[0];return data[:m.start()]+('export WL_PARENT_ID=%d\\n'%REFERENCE_WID).encode()+data[m.end():],int(m[1])".replace("%d\n", "%d\\n"))
    change("'original_reference_wid':29", "'original_reference_wid':REFERENCE_WID")
    change("=='5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79'", "")
    change("params['run_derivation']['after_wid29_reference_sha256']", "params['run_derivation']['after_sha256']")
    change("assert wid=='29','fresh WID differs from exact admitted baseline; re-review required'",
           "assert wid==str(REFERENCE_WID),'fresh WID differs from reviewed 61b data'")
    change("for data in [before,after]:assert data.count(b'export WL_PARENT_ID=29\\n')==1",
           "for data in [before,after]:assert data.count(('export WL_PARENT_ID=%d\\n'%REFERENCE_WID).encode())==1".replace("%d\n", "%d\\n"))
    change("assert origin_wid=='29'", "assert origin_wid==str(REFERENCE_WID)")
    change("assert sha(normalized) in (sha(origin_before),sha(origin_after)),(actual,'foreign run.sh beyond admitted WID value')",
           """assert ad['recovery_run_sha256']==actual and ad['recovery_wid']==current_wid,'fresh recovery run binding'
 assert sha(normalized) in (sha(origin_before),sha(origin_after)),(actual,'foreign run.sh beyond one approved WID')
""")
    # No-parent recovery must not dereference an absent host/parent.
    begin = s.index("host=ad['host'];")
    end = s.index("for provider in ad['providers']:", begin)
    host_block = s[begin:end]
    s = s[:begin] + "if not a.recovery_no_parent:\n" + "".join(" "+line+"\n" for line in host_block.rstrip().splitlines()) + s[end:]
    # Pin all write-parent directories and reject shared directory aliases.
    change("board.ready()\nif a.recovery_no_parent:", """def directory_guard():
 dirs=ad['directory_identities']; protected=ad['protected_directories']
 required={RT,RT+'/lib',RT+'/lib/arm64-v8a',RT+'/webview-t-lib'}
 assert set(dirs)==required and len(set(dirs.values()))==len(dirs),'directory alias'
 assert set(protected)=={'/system/lib64','/data/local/tmp/asx','/data/local/tmp/asx/lib','/data/local/tmp/asx/lib/arm64-v8a','/data/local/tmp/asx/webview-t-lib'},'protected root inventory'
 text=''
 for path,identity in dirs.items():
  assert re.fullmatch(r'[0-9]+:[0-9]+',identity),'directory dev:inode'
  text+=pathguard(path)+f'test -d {q(path)}\\ntest "$(stat -L -c %d:%i {q(path)})" = {q(identity)}\\n'
 for path,identity in protected.items():
  if identity is None:text+=f'test ! -e {q(path)}; test ! -L {q(path)}\\n'
  else:
   assert re.fullmatch(r'[0-9]+:[0-9]+',identity) and identity not in dirs.values(),'shared directory alias'
   text+=f'test -d {q(path)}\\ntest "$(stat -L -c %d:%i {q(path)})" = {q(identity)}\\n'
 return text
board.ready()
shell(directory_guard())
if a.recovery_no_parent:""")
    change("pre=parent_guard+fg", "pre=directory_guard()+parent_guard+fg")
    change("shell(pre)\nplan=", """hap='/data/app/el1/bundle/public/org.westlake.imehost/entry.hap'
pre+=pathguard(hap)+f'test "$(sha256sum {hap} | cut -d\\' \\' -f1)" = b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0\\n'
shell(pre)
plan=""")
    change("if dso_present:pre+=pathguard(absence_backup)",
           "if dso_present or any((actual!=sha(before),mactual!=MBEFORE,pactual!=PBEFORE,bactual!=BBEFORE,sactual!=SBEFORE)):pre+=pathguard(absence_backup)")
    # Any mutated state requires all five backups, not only the currently changed file.
    change("else:assert current==digest,'missing backup for changed target'",
           "else:assert not dso_present and actual==sha(before) and mactual==MBEFORE and pactual==PBEFORE and bactual==BBEFORE and sactual==SBEFORE,'missing backup after any mutation'")
    change("+before_guard+f'mv {q(tmp)} {q(dst)}", "+directory_guard()+before_guard+f'mv {q(tmp)} {q(dst)}")
    change("swap('run.sh',stage+'/run.sh',sha(new)", "swap('run.sh',backup if a.mode=='rollback' else stage+'/run.sh',sha(new)")
    change("script+=fg(RT+'/'+DSO,DSHA,", "script+=directory_guard()+fg(RT+'/'+DSO,DSHA,")
    change("'physical_only':a.recovery_no_parent", "'physical_only':a.recovery_no_parent,'deployment_scope':'T34_61B_VIDEO','parameters_sha256':sha_file(here/'parameters.json'),'directory_identities':ad['directory_identities']")
    change("assert apply_plan['compat_before_absent'] is True",
           """assert apply_plan['compat_before_absent'] is True
 assert apply_plan['deployment_scope']=='T34_61B_VIDEO'
 assert apply_plan['parameters_sha256']==sha_file(here/'parameters.json')
 assert apply_plan['directory_identities']==ad['directory_identities']
""")
    compile(s, "executor61b.py", "exec")
    return s

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    original=(a.repo/ORIGIN/'executor.py').read_text()
    result=derive(original)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'executor61b.py').write_text(result)
    (a.out/'executor.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),result.splitlines(True),fromfile=ORIGIN+'/executor.py',tofile='deployment/executor61b.py')))
    for name in ('bridge-candidate.json','shim-candidate.json','executor-source-pins.json'):
        (a.out/name).write_bytes((a.repo/ORIGIN/name).read_bytes())
    (a.out/'derivation.json').write_text(json.dumps({'origin':ORIGIN+'/executor.py','origin_sha256':ORIGIN_SHA,'derived_sha256':hashlib.sha256(result.encode()).hexdigest(),'status':'OFFLINE_REVIEW_REQUIRED','device_calls':0},indent=2)+'\n')

if __name__=='__main__':main()
