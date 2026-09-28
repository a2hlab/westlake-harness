"""Offline contract evidence gates. A rejected candidate must not become LIT."""
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parent
D=json.loads((R/'results.json').read_text())
def loaded(proof,expected):
 rows={Path(x.split()[1]).name:x.split()[0] for x in proof.splitlines() if len(x.split())==2}
 return all(rows.get(k)==v for k,v in expected.items())
def acceptance(proof,expected,alive,visual):
 return {'passed':loaded(proof,expected) and alive and visual,'lit_delta':int(loaded(proof,expected) and alive and visual)}
def check(which):
 c=D['candidate'];expected={'framework.jar':c['framework_sha256'],'boot-framework.oat':c['boot_framework_oat_sha256'],'oh-adapter-runtime.jar':c['runtime_sha256']};proof=(R/c['proof']).read_text()
 if which=='caller':
  s=(R/D['caller']['evidence']).read_text();assert '->getTheme()' in s and '.catch Ljava/lang/NullPointerException;' in s and 'invoke-super' in s
  assert D['caller']['getTheme_line']<D['caller']['catch_NPE_line']<D['caller']['super_attach_line']
 elif which=='null':
  assert D['null_check_mode']=='sigsegv';s=(R/D['null_check_evidence']).read_text();assert 'SIGSEGV' in s and 'ContextWrapper.getApplicationInfo' in s
  s=(R/'null-check-root/b5-wikipedia-signal-hilog.txt').read_text();assert s.index('19:07:35.276 27515 27515 I C02d11/DfxSignalHandler')<s.index('19:07:35.946 27515 27515 W C03f07/MUSL-SIGCHAIN')
 elif which=='negative':
  assert loaded(proof,expected),'positive hash control must match real child'
  trials=[]
  for name,digest in expected.items():
   bad=proof.replace(digest,'0'*64);v=acceptance(bad,expected,True,True);assert v=={'passed':False,'lit_delta':0};trials.append({'mismatched':name,**v})
  rollback=next((R/'evidence/rollback-baseline/helloworld').glob('child-proof-*.sha256')).read_text();assert not loaded(rollback,expected)
  assert not acceptance(proof,expected,False,True)['passed']
  (R/'negative-results.json').write_text(json.dumps({'positive_child':6826,'candidate_hashes_matched':True,'single_artifact_mismatches':trials,'real_rollback_rejected':True,'dead_child_rejected':True},indent=2)+'\n')
 elif which=='wikipedia':
  assert c['currently_active'] and c['guard_execution_proven'],'no active validated B6 fix'
  assert acceptance(proof,expected,D['wikipedia']['alive_15s'],D['wikipedia']['outer_acceptance'])['passed']
 elif which=='regression':
  assert not D['regressions'],'HelloWorld regressed under rejected B6 candidate'
  assert D['quick']['final_fix_regression_gate']=='passed'
 elif which=='nextwall':
  assert D['status']=='advanced' and c['guard_execution_proven'] and D['next_blocker'],'earlier regression is not advancement'
  assert D['lit_delta']==0
 else:raise ValueError(which)
 print(which+': passed')
if __name__=='__main__':check(sys.argv[1])
