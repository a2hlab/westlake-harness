"""Machine receipt gate; screenshot interpretation remains human review."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
expected={'runtime':{'sha256_12':'68b7fb016253','files':119},'boot':{'sha256_12':'8fe2e5fd7d65','files':36}}
for name in ['apply2.json','apply4.json']:
    d=json.loads((root/name).read_text())
    assert d['status']=='active_verified',name
    assert len(d['plan']['expected'])==312,name
    assert d['fingerprints']==expected,name
    assert d['verification']['maps']['passed'],name
    assert d['verification']['parent']!=d['verification']['child'],name
one=json.loads((root/'apply2.json').read_text());two=json.loads((root/'apply4.json').read_text())
assert one['boot_id']!=two['boot_id'],'reboot not demonstrated'
assert one['plan']['bundle_sha256']==two['plan']['bundle_sha256'],'bundle changed'
assert json.loads((root/'baseline-replay.json').read_text())['status']=='baseline_restored'
print('two boots: 312 identities, parent/child, single ART, both fingerprints; screenshots require human review')

rollback=json.loads((root/'rollback.json').read_text())
assert rollback['status']=='rolled_back'
assert rollback['rollback_fingerprints']['runtime']['sha256_12']=='73ecf422dba2'
assert rollback['rollback_fingerprints']['boot']['sha256_12']=='0876029078e2'
for group,keys in [('controls2',['helloworld','zigzag']),('samples',['aegis','fd-gallery','markor','opencamera']),('catima',['fd-catima']),('after-reboot',['helloworld'])]:
    for key in keys:
        records=list((root/'evidence'/group).rglob(key+'/record.json'))
        assert len(records)==1,(group,key)
        rec=json.loads(records[0].read_text())
        assert any(x.get('captured') and x.get('scheduled_seconds')==20 for x in rec['screenshots']),(group,key)
for number in range(1,4):
    assert len(list((root/'evidence'/('noice-'+str(number))).rglob('noice/record.json')))==1

final=json.loads((root/'rollback4.json').read_text())
assert final['status']=='rolled_back'
assert final['rollback_fingerprints']==rollback['rollback_fingerprints']
assert final['boot_id']==two['boot_id']
assert len(final['plan']['baseline'])==312
print('follow-up window: same post-reboot bundle, HW t20 captured, final U5 rollback verified')
