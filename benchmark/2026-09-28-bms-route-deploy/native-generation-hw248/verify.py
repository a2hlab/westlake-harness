"""B6 current-generation evidence gates; missing child proof never passes."""
from pathlib import Path
import json,re,subprocess,sys
r=Path(__file__).resolve().parent
d=json.loads((r/'results.json').read_text())
def child_accepted(proof):
 return bool(proof and proof.get('libsigchain.so')==d['sigchain_sha256'] and proof.get('child_plugin')==d['child_plugin_sha256'] and proof.get('appspawn')==d['appspawn_sha256'] and proof.get('mapped_new_sigchain'))
which=sys.argv[1]
if which=='caller':
 subprocess.run([sys.executable,str(r.parent/'sigchain-bridge/verify.py'),'caller'],check=True)
elif which=='symbols':
 s=(r/'bridge-new-elf.txt').read_text();check=json.loads((r/'bridge-identity-check.json').read_text())
 exports={line.split()[-1] for line in s.splitlines() if re.search(r'\bFUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+',line)}
 required=set(check['required']);assert required<=exports
 assert all(not required<=exports-{name} for name in required)
 assert re.search(r'Build ID: [0-9a-f]{40}',s) and 'Library soname: [libsigchain.so]' in s
elif which=='negative':
 good={'libsigchain.so':d['sigchain_sha256'],'child_plugin':d['child_plugin_sha256'],'appspawn':d['appspawn_sha256'],'mapped_new_sigchain':True}
 assert child_accepted(good)
 for key in good:
  bad=dict(good);bad[key]=False if key=='mapped_new_sigchain' else 'old-generation'
  assert not child_accepted(bad)
 assert not child_accepted(None)
 assert not d['candidate_child_sigchain_mapping_observed'] and d['lit_delta']==0
elif which=='identity':
 assert d['identity_gate_passed'] and d['candidate_child_sigchain_mapping_observed'],'no successful HelloWorld child mapping proof'
elif which=='wikipedia':
 assert d['wikipedia_retested'] and d.get('wikipedia_own_ui_signed',False),'Wikipedia gate not reached'
elif which=='regression':
 assert not d['regressions'] and d['quick'].get('accepted',False),'candidate HelloWorld failed; quick acceptance not reached'
elif which=='null':
 assert d['npe_retested'] and d['null_check_mode']=='npe','no repaired-generation NPE evidence'
elif which=='nextwall':
 assert d['status']=='advanced','pre-ART bring-up failure is not advanced past getTheme'
else:raise ValueError(which)
print(which+': passed')
