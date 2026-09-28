"""Exercise the offline gate with real AArch64 ELF inputs; never deploy."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from audit_closure import audit

p = argparse.ArgumentParser()
p.add_argument('--sigchain', type=Path, required=True)
p.add_argument('--libc', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
libc_sha = hashlib.sha256(a.libc.read_bytes()).hexdigest()
pool = {'libc.so': {'path': str(a.libc.resolve()), 'sha256': libc_sha}}
checks = {}
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    shutil.copyfile(a.sigchain, root / 'libsigchain.so')
    positive = audit(root, ['libsigchain.so'], pool)
    assert positive['passed'], positive
    checks['complete_explicit_pool_passes'] = True
    missing = audit(root, ['libsigchain.so', 'libart.so'], pool)
    assert not missing['passed'] and missing['missing'] == ['libart.so']
    checks['missing_generation_member_rejected'] = True
    absent = audit(root, ['libsigchain.so'], {})
    assert not absent['passed'] and absent['unresolved_needed']
    checks['implicit_host_library_search_refused'] = True
    wrong = {'libc.so': dict(pool['libc.so'], sha256='0' * 64)}
    mismatch = audit(root, ['libsigchain.so'], wrong)
    assert not mismatch['passed'] and mismatch['unresolved_needed']
    checks['wrong_platform_sha_rejected'] = True
    false_absence = {'libc.so': dict(pool['libc.so'], soname=[])}
    assert not audit(root, ['libsigchain.so'], false_absence)['passed']
    checks['false_absent_soname_declaration_rejected'] = True
    shutil.copyfile(a.sigchain, root / 'libwrong.so')
    soname = audit(root, ['libwrong.so'], pool)
    assert not soname['passed'] and any(e['error'] == 'SONAME mismatch' for e in soname['errors'])
    checks['wrong_soname_rejected'] = True
receipt = {'checks': checks, 'passed': all(checks.values()),
           'sigchain_sha256': hashlib.sha256(a.sigchain.read_bytes()).hexdigest(),
           'libc_sha256': libc_sha, 'scope': 'Host gate controls only; not target generation admission'}
a.out.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
