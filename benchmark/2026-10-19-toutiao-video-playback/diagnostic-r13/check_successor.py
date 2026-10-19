"""Offline exact-parent diff check. Does not import or execute the observer."""
import argparse, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);a=p.parse_args()
here=Path(__file__).resolve().parent
pins=json.loads((here/'evidence/parent-pins.json').read_text())['files']
expected={Path(r['path']).name:r['sha256'] for r in pins}
old='d6d9a233fd3b9bd2ff60a69eec78aa2e70eaf4d94b98e0cbb55fae90706fb229'
new='13c0b4bfcb0b8b83cd9d73df2be0ebffcb1cc5fea2eb420cb7b2f5629254a06a'
rows=[]
for name in ['core.py','identity.py','observe.py','observer.py','admission.disabled.example.json']:
    raw=(a.parent/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected[name], 'parent drift '+name
    wanted=raw.decode().replace('r11','r13').replace('R11','R13').replace(old,new)
    assert (here/name).read_text()==wanted, 'non-allowlisted delta '+name
    rows.append({'file':name,'only_version_labels_and_exact_server_pin':True})
# All eleven original tests are retained verbatim after the same label/pin change.
raw=(a.parent/'test_observer.py').read_bytes()
assert hashlib.sha256(raw).hexdigest()==expected['test_observer.py']
wanted=raw.decode().replace('r11','r13').replace('R11','R13').replace(old,new)
actual=(here/'test_observer.py').read_text();begin=actual.index('    def test_old_server_and_schema_refused(');end=actual.index('    def test_admission_fixed_values(',begin)
assert actual[:begin]+actual[end:]==wanted, 'original tests drift'
print(json.dumps({'status':'PASS','executable_and_template':rows,'original_tests_preserved':11,'new_negative_test_methods':1},indent=2))
