import copy,json
from t146_patch import fixture, patch_module, SYNTH_BASELINE_SHA, SYNTH_CANDIDATE_SHA
from pathlib import Path
import execute_v6 as m
from recovery_lineage import select_main
P=Path(__file__).resolve().parent
source=fixture('execute-20261025-031657-eafd14','0060-baseline-s30-identity-before','stdout')
original=m.parse_identity(source.read_text());before=copy.deepcopy(original)
main,descendants=select_main(original)
assert (main['pid'],main['birth'],main['parent'])==(7331,16865,5537)
assert descendants[0]['lineage_to_main']==[8080,7331]
assert original==before
checks=['actual7331_main8080_descendant_full_identity_preserved']
for name,edit in [
 ('two_direct_main_children',lambda x:x['processes'][-1].update(parent=5537)),
 ('unproven_lineage',lambda x:x['processes'][-1].update(parent=99999)),
 ('wrong_descendant_uid',lambda x:x['processes'][-1].update(uid=0)),
 ('wrong_main_uid',lambda x:x['processes'][-2].update(uid=0)),
 ('cyclic_lineage',lambda x:x['processes'][-1].update(parent=8080)),
]:
 data=copy.deepcopy(original);edit(data)
 try:select_main(data)
 except RuntimeError:checks.append(name)
 else:raise AssertionError(name)
data=copy.deepcopy(original);data['processes'].pop();assert select_main(data)[1]==[];checks.append('single_direct_main')
print(json.dumps({'synthetic_or_record_replay_only':True,'passed':len(checks),'checks':checks,'input_sha256':m.digest(source)}))
