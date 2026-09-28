"""B6 #33 evidence checks: pre-ART loader rejection is never NPE success."""
from pathlib import Path
import json,sys
from symbol_gate import check as symbol_check
r=Path(__file__).resolve().parent;d=json.loads((r/'results.json').read_text())
def accept(child_proof,expected,alive,own_ui):
 return bool(child_proof and child_proof.get('libsigchain.so')==expected and alive and own_ui)
def verify(which):
 if which=='caller':
  p=r/'../attach-theme'/d['caller']['evidence'];s=p.read_text();assert '->getTheme()' in s and '.catch Ljava/lang/NullPointerException;' in s and 'invoke-super' in s
 elif which=='symbols':
  g=d['symbols'];assert symbol_check(g['required'],g['new_exports'])['passed'];assert len(g['required'])==4
  trials={n:symbol_check(g['required'],set(g['new_exports'])-{n}) for n in g['required']}
  assert all(x['missing']==[n] and not x['deploy_allowed'] for n,x in trials.items())
  bindings=json.loads((r/'bindings.json').read_text())['bindings'];assert all(bindings[n]['owner'].endswith('/libsigchain.so') for n in g['required']);assert bindings['sigaction']['owner'].endswith('/ld-musl-aarch64.so.1')
  (r/'negative-symbols.json').write_text(json.dumps(trials,indent=2)+'\n')
 elif which=='negative':
  sha=d['candidate']['sha256'];assert accept({'libsigchain.so':sha},sha,True,True)
  assert not accept({'libsigchain.so':d['candidate']['old_sha256']},sha,True,True)
  assert not accept(None,sha,True,True)
  assert not accept({'libsigchain.so':sha},sha,False,True)
  for a in d['attempts'].values():
   assert not accept(a['child_sha_proof'],sha,a['alive_15s'],False)
   s=(r/a['hilog']).read_text();assert 'LOAD_ERROR:8' in s and 'FAIL_SEALED_PROVIDER' in s and 'exit with code:123' in s
  assert d['lit_delta']==0
  (r/'negative-artifact.json').write_text(json.dumps({'old_sha_rejected':True,'absent_child_proof_rejected':True,'dead_child_rejected':True,'real_loader_refusal':'two exit123 attempts; zero LIT'},indent=2)+'\n')
 elif which=='null':
  assert d['null_check_retest']['npe_proven'] and d['null_check_mode']=='npe','candidate refused before ART; no NPE retest evidence'
 elif which=='wikipedia':
  assert d['candidate']['child_loaded'] and d['candidate']['currently_active'],'candidate not admitted by sealed loader'
  assert d['attempts']['wikipedia']['alive_15s']
 elif which=='regression':
  assert not d['regressions'] and d['quick']['accepted'],'HelloWorld regressed; final-fix quick not reached'
 elif which=='nextwall':
  assert d['status']=='advanced' and d['next_blocker'],'pre-ART rejection is not progress past getTheme'
 else:raise ValueError(which)
 print(which+': passed')
if __name__=='__main__':verify(sys.argv[1])
