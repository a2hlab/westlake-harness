"""Mechanical T18 -> T21 sixth-artifact transaction; no device access."""
import argparse, hashlib
from pathlib import Path
DONOR = '57affbe0281bf3523c799b3a5973fb9f5946451a170d010e89d0d4d417b01f6a'
DONOR_REL = 'benchmark/2026-10-20-t18-bridge-deployment/executor.py'
def derive(raw):
 assert hashlib.sha256(raw).hexdigest() == DONOR, 'T18 donor drift'
 s=raw.decode().replace('.t18-5cd-before-', '.t21-5cd-before-').replace('/data/local/tmp/t18-5cd-', '/data/local/tmp/t21-5cd-').replace('5cd R9 plus AudioTrack bridge CAS derivation.', '5cd T21 six-artifact CAS derivation.')
 def change(old,new):
  nonlocal s
  assert s.count(old)==1, old
  s=s.replace(old,new)
 change("ad=json.loads(a.admission.read_text())", '''shim_candidate=json.loads((here/'shim-candidate.json').read_text())
SHIM='webview-t-lib/libwebview_bionic_shim.so'
SHIM_INPUT='libwebview_bionic_shim.so'
SBEFORE='85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a'
SAFTER=shim_candidate['after_sha256']
assert shim_candidate['path']==SHIM and shim_candidate['before_sha256']==SBEFORE
assert isinstance(SAFTER,str) and re.fullmatch('[0-9a-f]{64}',SAFTER) and SAFTER!=SBEFORE,'shim candidate pin required'
assert shim_candidate['build_status']=='PRODUCTION_BUILD_VERIFIED' and shim_candidate['production_refs'],'shim production closure required'
for ref in shim_candidate['production_refs']:
 assert not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts
 assert sha_file(a.repo/ref['path'])==ref['sha256'],'shim production receipt drift'
ad=json.loads(a.admission.read_text())
assert ad['shim_candidate_sha256']==sha_file(here/'shim-candidate.json'),'shim candidate admission drift'
assert re.fullmatch(r'[0-7]{3,4}:20011300:20011300',ad['shim_metadata']),'fresh shim metadata required'
assert ad['shim_label']=='u:object_r:appdat:s0','shim label' ''')
 change("(BRIDGE,BAFTER)]:", "(BRIDGE,BAFTER),(SHIM_INPUT,SAFTER)]:")
 change("expected=sha(before)\napply_plan=None", '''sactual=read('sha256sum '+RT+'/'+SHIM).split()[0]
smeta=read('stat -c %a:%u:%g '+RT+'/'+SHIM).strip();assert smeta==ad['shim_metadata'],'shim metadata drift'
slabel=read('ls -Zd '+RT+'/'+SHIM).split()[0];assert slabel==ad['shim_label'],'shim label drift'
expected=sha(before)
apply_plan=None''')
 change(" assert apply_plan['compat_before_absent'] is True", ''' assert apply_plan['compat_before_absent'] is True
 assert apply_plan['shim_path']==SHIM and apply_plan['shim_before_sha']==SBEFORE and apply_plan['shim_after_sha']==SAFTER
 assert apply_plan['shim_candidate_sha256']==sha_file(here/'shim-candidate.json')
 assert (smeta,slabel)==(apply_plan['shim_metadata'],apply_plan['shim_label'])
 assert sactual in (SBEFORE,SAFTER),'foreign shim bytes'
 assert apply_plan['compat_absence_marker_sha256']==sha(b'ABSENT\\n')''')
 change(" assert bactual==BBEFORE,'bridge before drift'", " assert bactual==BBEFORE,'bridge before drift'\n assert sactual==SBEFORE,'shim before drift'")
 change("pre+=fg(RT+'/'+DSO,DSHA", '''pre+=fg(RT+'/'+SHIM,sactual,smeta,slabel)
if not a.recovery_no_parent:
 private_shim=f'/proc/{a.parent}/root/data/local/tmp/asx/{SHIM}'
 pre+=fg(private_shim,sactual,smeta,slabel)[len(pathguard(private_shim)):]
 pre+=f'test "$(stat -L -c %d:%i {RT}/{SHIM})" = "$(stat -L -c %d:%i {private_shim})"\\n'
pre+=fg(RT+'/'+DSO,DSHA''')
 change(" bridge_backup=RT+'/'+BRIDGE+'.t21-5cd-before-'+apply_plan['boot'][:8]", " bridge_backup=RT+'/'+BRIDGE+'.t21-5cd-before-'+apply_plan['boot'][:8]\n shim_backup=RT+'/'+SHIM+'.t21-5cd-before-'+apply_plan['boot'][:8]\n absence_backup=RT+'/'+DSO+'.t21-5cd-before-'+apply_plan['boot'][:8]+'.absent'\n assert apply_plan['compat_absence_marker']==absence_backup\n if dso_present:pre+=pathguard(absence_backup)+f'test -f {q(absence_backup)}\\ntest \"$(sha256sum {q(absence_backup)} | cut -d\\\' \\\' -f1)\" = {sha(b\"ABSENT\\\\n\")}\\n'")
 # Avoid backslashes in Python f-string expressions on supported Python versions.
 s=s.replace('{sha(b"ABSENT\\\\n")}', '{apply_plan["compat_absence_marker_sha256"]}')
 change("(BRIDGE,bridge_backup,BBEFORE,bmeta,blabel,bactual)]:", "(BRIDGE,bridge_backup,BBEFORE,bmeta,blabel,bactual),(SHIM,shim_backup,SBEFORE,smeta,slabel,sactual)]:")
 change("if apply_plan is not None:plan['origin_apply_plan_sha256']", '''plan.update(shim_path=SHIM,shim_before_sha=SBEFORE,shim_after_sha=SAFTER,shim_metadata=smeta,shim_label=slabel,shim_candidate_sha256=sha_file(here/'shim-candidate.json'),compat_absence_marker=RT+'/'+DSO+'.t21-5cd-before-'+(apply_plan['boot'] if apply_plan else a.boot)[:8]+'.absent',compat_absence_marker_sha256=sha(b'ABSENT\\n'))
if apply_plan is not None:plan['origin_apply_plan_sha256']''')
 change("def swap(name,source,digest,fmeta,flabel,preimage):", '''if a.mode=='apply':
 shim=a.inputs/SHIM_INPUT;assert sha(shim.read_bytes())==SAFTER
 board.send(shim,stage+'/'+SHIM_INPUT);shell(f'test "$(sha256sum {stage}/{SHIM_INPUT} | cut -d\\' \\' -f1)" = {SAFTER}\\n')
def swap(name,source,digest,fmeta,flabel,preimage):''')
 change('# All four original backups are complete and verified before the first target swap.', '''if a.mode=='apply':
 shim_backup=RT+'/'+SHIM+'.t21-5cd-before-'+a.boot[:8]
 script+=pathguard(shim_backup)+f'test ! -e {q(shim_backup)}\\ncp -p {RT}/{SHIM} {q(shim_backup)}\\n'+fg(shim_backup,SBEFORE,smeta,slabel)
 absence_backup=plan['compat_absence_marker']
 script+=pathguard(absence_backup)+f'test ! -e {q(absence_backup)}\\n(set -C; printf "ABSENT\\\\n" > {q(absence_backup)})\\nchmod 600 {q(absence_backup)}\\ntest "$(sha256sum {q(absence_backup)} | cut -d\\' \\' -f1)" = {plan["compat_absence_marker_sha256"]}\\n'
# Six preimages: five verified file backups plus the compat ABSENT receipt.
if a.mode!='rollback' or sactual!=SBEFORE:script+=swap(SHIM,shim_backup if a.mode=='rollback' else stage+'/'+SHIM_INPUT,SBEFORE if a.mode=='rollback' else SAFTER,smeta,slabel,sactual)''')
 change('bridge_backup=bridge_backup),indent=2)', 'bridge_backup=bridge_backup,shim_backup=shim_backup,compat_absence_marker=absence_backup),indent=2)')
 # compat_absence_marker is already present in plan; avoid duplicate kwargs.
 s=s.replace('shim_backup=shim_backup,compat_absence_marker=absence_backup)', 'shim_backup=shim_backup)')
 return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);a=p.parse_args()
 data=derive((a.repo/DONOR_REL).read_bytes());compile(data,'executor.py','exec')
 (Path(__file__).parent/'executor.py').write_text(data)
 print(hashlib.sha256(data.encode()).hexdigest())
