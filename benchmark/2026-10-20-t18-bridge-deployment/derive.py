"""Exact T17 donor, adding the bridge as one fifth CAS artifact; offline only."""
import argparse,hashlib
from pathlib import Path
DONOR='07e8e501fbf71e70883722fe3f03d47dac665f8cf13c144e8c1f00926195f549'
def derive(raw):
 assert hashlib.sha256(raw).hexdigest()==DONOR,'T17 donor drift'
 s=raw.decode().replace('.t17-5cd-before-','.t18-5cd-before-').replace('/data/local/tmp/t17-5cd-','/data/local/tmp/t18-5cd-').replace('5cd R9 routing CAS derivation.','5cd R9 plus AudioTrack bridge CAS derivation.')
 def change(old,new):
  nonlocal s
  assert s.count(old)==1,old
  s=s.replace(old,new)
 change("ad=json.loads(a.admission.read_text())",'''candidate=json.loads((here/'bridge-candidate.json').read_text())
BRIDGE='liboh_adapter_bridge.so'
BBEFORE='d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b'
BAFTER=candidate['after_sha256']
assert candidate['path']==BRIDGE and candidate['before_sha256']==BBEFORE
assert isinstance(BAFTER,str) and re.fullmatch('[0-9a-f]{64}',BAFTER) and BAFTER!=BBEFORE,'candidate pin required'
assert candidate['build_status']=='PRODUCTION_BUILD_VERIFIED' and candidate['production_refs'],'production closure required'
for ref in candidate['production_refs']:
 assert not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts
 assert sha_file(a.repo/ref['path'])==ref['sha256'],'production receipt drift'
ad=json.loads(a.admission.read_text())
assert ad['bridge_candidate_sha256']==sha_file(here/'bridge-candidate.json'),'candidate admission drift'
assert re.fullmatch(r'[0-7]{3,4}:20011300:20011300',ad['bridge_metadata']),'fresh bridge metadata required'
assert ad['bridge_label']=='u:object_r:appdat:s0','bridge label' '''.rstrip())
 change("('libttmplayer.so',PAFTER)]", "('libttmplayer.so',PAFTER),(BRIDGE,BAFTER)]")
 change("expected=sha(before)\napply_plan=None",'''bactual=read('sha256sum '+RT+'/'+BRIDGE).split()[0]
bmeta=read('stat -c %a:%u:%g '+RT+'/'+BRIDGE).strip();assert bmeta==ad['bridge_metadata'],'bridge metadata drift'
blabel=read('ls -Zd '+RT+'/'+BRIDGE).split()[0];assert blabel==ad['bridge_label'],'bridge label drift'
expected=sha(before)
apply_plan=None''')
 change(" assert apply_plan['compat_before_absent'] is True",''' assert apply_plan['compat_before_absent'] is True
 assert apply_plan['bridge_path']==BRIDGE and apply_plan['bridge_before_sha']==BBEFORE and apply_plan['bridge_after_sha']==BAFTER
 assert apply_plan['bridge_candidate_sha256']==sha_file(here/'bridge-candidate.json')
 assert (bmeta,blabel)==(apply_plan['bridge_metadata'],apply_plan['bridge_label'])
 assert bactual in (BBEFORE,BAFTER),'foreign bridge bytes' ''')
 change(" assert pactual==PBEFORE,'player before drift'", " assert pactual==PBEFORE,'player before drift'\n assert bactual==BBEFORE,'bridge before drift'")
 change("pre+=fg(RT+'/'+DSO,DSHA",'''pre+=fg(RT+'/'+BRIDGE,bactual,bmeta,blabel)
if not a.recovery_no_parent:
 private_bridge=f'/proc/{a.parent}/root/data/local/tmp/asx/{BRIDGE}'
 # /proc/PID/root is the intentional, identity-bound namespace link.
 pre+=fg(private_bridge,bactual,bmeta,blabel)[len(pathguard(private_bridge)):]
 pre+=f'test "$(stat -L -c %d:%i {RT}/{BRIDGE})" = "$(stat -L -c %d:%i {private_bridge})"\\n'
pre+=fg(RT+'/'+DSO,DSHA''')
 change(" player_backup=RT+'/'+PLAYER+'.t18-5cd-before-'+apply_plan['boot'][:8]", " player_backup=RT+'/'+PLAYER+'.t18-5cd-before-'+apply_plan['boot'][:8]\n bridge_backup=RT+'/'+BRIDGE+'.t18-5cd-before-'+apply_plan['boot'][:8]")
 change("(PLAYER,player_backup,PBEFORE,pmeta,plabel,pactual)]:", "(PLAYER,player_backup,PBEFORE,pmeta,plabel,pactual),(BRIDGE,bridge_backup,BBEFORE,bmeta,blabel,bactual)]:")
 change("if apply_plan is not None:plan['origin_apply_plan_sha256']", "plan.update(bridge_path=BRIDGE,bridge_before_sha=BBEFORE,bridge_after_sha=BAFTER,bridge_metadata=bmeta,bridge_label=blabel,bridge_candidate_sha256=sha_file(here/'bridge-candidate.json'))\nif apply_plan is not None:plan['origin_apply_plan_sha256']")
 change("def swap(name,source,digest,fmeta,flabel,preimage):",'''if a.mode=='apply':
 bridge=a.inputs/BRIDGE;assert sha(bridge.read_bytes())==BAFTER
 board.send(bridge,stage+'/'+BRIDGE);shell(f'test "$(sha256sum {stage}/{BRIDGE} | cut -d\\' \\' -f1)" = {BAFTER}\\n')
def swap(name,source,digest,fmeta,flabel,preimage):''')
 change('# All three original backups are complete and verified before the first target swap.', '''if a.mode=='apply':
 bridge_backup=RT+'/'+BRIDGE+'.t18-5cd-before-'+a.boot[:8]
 script+=pathguard(bridge_backup)+f'test ! -e {q(bridge_backup)}\\ncp -p {RT}/{BRIDGE} {q(bridge_backup)}\\n'+fg(bridge_backup,BBEFORE,bmeta,blabel)
# All four original backups are complete and verified before the first target swap.
if a.mode!='rollback' or bactual!=BBEFORE:script+=swap(BRIDGE,bridge_backup if a.mode=='rollback' else stage+'/'+BRIDGE,BBEFORE if a.mode=='rollback' else BAFTER,bmeta,blabel,bactual)''')
 change('player_backup=player_backup),indent=2)', 'player_backup=player_backup,bridge_backup=bridge_backup),indent=2)')
 return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);a=p.parse_args()
 result=derive((a.repo/'benchmark/2026-10-20-t17-network-reuse/executor.py').read_bytes());(Path(__file__).parent/'executor.py').write_text(result)
 print(hashlib.sha256(result.encode()).hexdigest())
