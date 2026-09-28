"""B5 contract selectors over immutable device evidence; do not convert failure to PASS."""
from pathlib import Path
import json,hashlib,sys
r=Path(__file__).resolve().parent
def main(mode):
 for item in json.loads((r/'manifest.json').read_text()):
  p=(r/item['path']).resolve();assert p.is_relative_to(r)
  assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],str(p)
 data=json.loads((r/'results.json').read_text());trials=data['trials']
 for path,digest in data['runtime']['sources'].items():
  assert hashlib.sha256((r.parents[2]/path).read_bytes()).hexdigest()==digest,path
 assert data['key_count']==66 and data['selected_alias_count']==13
 assert data['deployed_boards']==['5ea34a4500000000000000001123012c']
 for key in ['wikipedia','helloworld','negative-retry']:
  t=trials[key];assert t['clicked'] and t['sample_span_seconds']>=15
  assert t['package'] in t['icon_id'] and t['sampled_pids']
 if mode=='wikipedia':
  t=trials['wikipedia']
  assert t['pids_after'],'Wikipedia exits after alias resolution: Activity.attach/getTheme/getApplicationInfo SIGSEGV; own-UI acceptance NOT met'
  # Human-labelled scenario stays pendingreview even when these machine prerequisites pass.
 elif mode=='alias':
  text=(r/'evidence/wikipedia/hilog-excerpt.txt').read_text()
  assert 'alias=org.wikipedia.DefaultIcon target=org.wikipedia.main.MainActivity ordinary=false' in text
  assert 'ClassNotFoundException' not in text
  fault=next((r/'evidence/wikipedia').glob('fault-*-excerpt.txt')).read_text()
  assert 'android.app.Activity.attach' in fault and 'android.app.ActivityThread.performLaunchActivity' in fault
  neg=(r/'evidence/negative-retry/hilog-excerpt.txt').read_text()
  assert 'Unable to instantiate activity ComponentInfo{org.a2hlab.b5aliasnegative/org.a2hlab.b5aliasnegative.MissingTarget}' in neg
 elif mode=='ordinary':
  t=trials['helloworld'];assert t['pids_after']==[28552]
  text=(r/'evidence/helloworld/hilog-excerpt.txt').read_text()
  assert 'target=null ordinary=true' in text
  assert 'Hello World!' in t['agent_visual_observation']
  # This records the agent's inspection of the hashed screenshot; outer has final visual authority.
 elif mode=='negative':
  t=trials['negative-retry'];assert not t['pids_after']
  text=(r/'evidence/negative-retry/hilog-excerpt.txt').read_text()
  for evidence in ['alias='+t['alias']+' target='+t['target'], 'ClassNotFoundException: Didn\'t find class "'+t['target']+'"', 'with pid 7151 exit with code:1']:
   assert evidence in text,evidence
  cleanup=data['negative_fixture_cleanup'];assert cleanup['bundle_absent'] and cleanup['fixture_library_dir_removed']
 else:raise ValueError(mode)
 print(mode+': passed; visual acceptance remains an outer-review decision')
if __name__=='__main__':main(sys.argv[1])
