#!/usr/bin/env python3
"""Exact offline successor derivation; never invokes a board or grants admission."""
import argparse, difflib, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = 'benchmark/2026-10-21-t34-demo61b-video/'
DEST = BASE + 'guardian-r3-video/'
OLD_ROOT = '/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261019-r2'
NEW_ROOT = '/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3'
OLD_CFG = '91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e'
NEW_CFG = '7b9f2c0e6431a486f3138f8fca04e3c5aea2c21f4f8acb6f83e815735d998e4b'
CFG_PATH = '/system/etc/init/01_westlake_u13_toutiao.cfg'
REFERENCE = 'benchmark/2026-10-20-t33-demo61b-host/static/reference.json'
PACKAGE = BASE + 'reentry-retirement-01/deploy-package-r3-root/'
sha = lambda b: hashlib.sha256(b).hexdigest()
encode = lambda x: (json.dumps(x, indent=2, sort_keys=True)+'\n').encode()

def generate(repo, package):
    pins = json.loads((HERE/'donor-pins.json').read_text())
    for rel, digest in pins['main'].items():
        assert sha((repo/rel).read_bytes()) == digest, ('donor drift', rel)
    for rel, digest in pins['package'].items():
        assert sha((package/rel).read_bytes()) == digest, ('guardian source drift', rel)
    ref = json.loads((repo/REFERENCE).read_text())
    assert len(ref['controls']) == 18
    controls = {}
    for path in ref['controls']:
        assert path.startswith(OLD_ROOT+'/')
        name = path.removeprefix(OLD_ROOT+'/')
        assert '/' not in name
        controls[NEW_ROOT+'/'+name] = sha((package/'payload'/name).read_bytes())
    before = (package/'deploy-cfg/before-live-01_westlake_u13_toutiao.cfg').read_bytes()
    after = (package/'deploy-cfg/after-r3-01_westlake_u13_toutiao.cfg').read_bytes()
    assert sha(before) == OLD_CFG and sha(after) == NEW_CFG
    assert before.count((OLD_ROOT+'/boot-entry.sh').encode()) == 1
    assert before.replace((OLD_ROOT+'/boot-entry.sh').encode(), (NEW_ROOT+'/boot-entry.sh').encode()) == after
    chain = json.loads((package/'CHAIN.json').read_text())
    assert chain['new_root'] == NEW_ROOT and chain['live_init_cfg']['after_r3_sha256'] == NEW_CFG
    for path, digest in controls.items():
        assert chain['payload_manifest']['payload/'+path.rsplit('/',1)[1]] == digest
    assert controls[NEW_ROOT+'/watchdog.sh'] == '8bf74a08b71474e39e90fcdb012eed5e420f7352fa131cef2aa63b9c5bd80ef9'
    env = (package/'payload/startup.env').read_text()
    assert "STARTUP_ENABLED='1'" in env and "STARTUP_APPROVED_BY='outer(codex)'" in env
    ref['controls'] = controls
    assert ref['runtime'][CFG_PATH] == OLD_CFG
    ref['runtime'][CFG_PATH] = NEW_CFG
    out = {'deployment/guardian-reference.json': encode(ref)}
    diffs = []
    def copy(source, target, replacements=()):
        old = (repo/(BASE+source)).read_text(); new = old
        for a,b,count in replacements:
            assert new.count(a) == count, ('replacement count', source, a)
            new = new.replace(a,b)
        out[target] = new.encode()
        if new != old:
            diffs.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=BASE+source,tofile=DEST+target))
    copy('deployment/executor61b.py','deployment/executor61b.py',[(OLD_CFG,NEW_CFG,1),(OLD_ROOT,NEW_ROOT,1)])
    copy('deployment/prepare_data.py','deployment/prepare_data.py',[(OLD_CFG,NEW_CFG,1),("repo/'"+REFERENCE+"'","D/'guardian-reference.json'",1)])
    # The original binder's relative import selects this sibling deployment automatically.
    copy('bind_fresh.py','bind_fresh.py')
    for name in ('render_supplement.py','bridge-candidate.json','shim-candidate.json','executor-source-pins.json'):
        copy('deployment/'+name,'deployment/'+name)
    # Preserve the original full derivation, changing only its two existing parameters.
    copy('deployment/derive.py','deployment/derive.py',[(OLD_CFG,NEW_CFG,1),('icon-manual-20261019-r2','icon-manual-20261021-r3',1)])
    executor_sha = sha(out['deployment/executor61b.py'])
    copy('transport-01/file_transport.py','transport/file_transport.py',[(pins['main'][BASE+'deployment/executor61b.py'],executor_sha,1)])
    copy('window-driver-01/common.py','window-driver/common.py',[("REL/'transport-01/file_transport.py'","REL/'guardian-r3-video/transport/file_transport.py'",1),("REL/'deployment/executor61b.py'","REL/'guardian-r3-video/deployment/executor61b.py'",1)])
    for name in ('exec_driver.py','recover_driver.py'):
        copy('window-driver-01/'+name,'window-driver/'+name)
    copy('window-driver-01/test_driver.py','window-driver/test_driver.py',[("common.HERE.parents[2]","common.HERE.parents[3]",1)])
    hp = json.loads((repo/(BASE+'window-driver-01/helper-pins.json')).read_text())
    for old,new in [('transport-01/file_transport.py','transport/file_transport.py'),('deployment/executor61b.py','deployment/executor61b.py')]:
        del hp[BASE+old]; hp[DEST+new] = sha(out[new])
    out['window-driver/helper-pins.json'] = encode(hp)
    copy('test_offline.py','test_transaction.py',[("D.parents[1].parent/'westlake-harness'","D.parents[2]",1)])
    copy('transport-01/test_transport.py','transport/test_transport.py')
    out['mechanical.diff'] = ''.join(diffs).encode()
    out['baseline.json'] = encode({'status':'EXPECTED_R3_BASELINE_REQUIRES_FRESH_READBACK_AND_OUTER_ADMISSION','guardian_root':NEW_ROOT,'cfg_path':CFG_PATH,'cfg_sha256':NEW_CFG,'controls':controls,'control_count':18,'package':PACKAGE,'package_commit':'81cff91758','device_calls':0,'approved_by':None})
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--guardian-package',type=Path,required=True)
    p.add_argument('--check',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
    files=generate(a.repo,a.guardian_package)
    if a.check:
        for name,data in files.items():assert (HERE/name).read_bytes()==data, ('derived drift',name)
    else:
        assert a.out and not a.out.exists(),'new output directory required'
        for name,data in files.items():
            f=a.out/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
    print(json.dumps({'status':'EXACT_DERIVATION_CHECKED' if a.check else 'DERIVED_UNSIGNED','files':len(files),'device_calls':0}))
if __name__=='__main__':main()
