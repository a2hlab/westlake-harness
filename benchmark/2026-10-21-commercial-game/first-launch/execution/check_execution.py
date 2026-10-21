#!/usr/bin/env python3
"""Offline check of the G06 execution receipt (window-outer-01/02); never touches a device."""
import hashlib, json, os, re, sys
from pathlib import Path
D = Path(__file__).resolve().parent; ROOT = D.parents[3]
res = json.loads((D / 'results.json').read_text())
w1, w2 = res['windows']['window-outer-01'], res['windows']['window-outer-02']
assert w1['verdict'] == 'READ_ONLY_FAILURE_BEFORE_INSTALL' and w1['writes'] == 0
assert w2['after_lock'] == 0 and w2['smoke']['rc'] == 0 and w2['genshin_shard']['screenshots'] == 0
assert w2['restore']['status'] == 'RESTORED_NO_INSTALL' and res['runtime_verdict'].startswith('NOT_TESTED')
facts = (D / 'evidence/genshin-facts.txt').read_text().splitlines()
assert facts[-1] == w2['genshin_shard']['facts_total'], 'facts TOTAL must be verbatim'
ex = (D / 'evidence/install-hilog-bms-excerpt.txt').read_text()
for line in w2['first_fatal']['lines'][:3]:
    key = re.search(r'\[?([a-z_]+\.cpp[^\]]*)', line).group(1)
    assert key.split(')')[0] in ex, 'first-fatal line not in excerpt: ' + key
assert ex.index('CheckEndDir') < ex.index('APK extractor init failed') < ex.index('ExtractFiles(APK_NATIVE_SO) failed')
assert '9568260' in (D / 'evidence/install.txt').read_text()
own = w2['deployment_binding']['zip_extractor_owner']
assert own['dso'].startswith('/system/lib64/libinstalls.z.so') and w2['deployment_binding']['dsos']['/system/lib64/libinstalls.z.so']['sha256'].startswith('51e1b525')
for r in res['public_refs']:
    b = (ROOT / r['alias']).read_bytes()
    assert hashlib.sha256(b).hexdigest() == r['sha256'] and len(b) == r['size'], r['alias']
priv = 0
for r in res['private_refs']:
    p = Path(r['alias'].replace('$HOME', os.path.expanduser('~')))
    if p.exists():
        b = p.read_bytes(); assert hashlib.sha256(b).hexdigest() == r['sha256'] and len(b) == r['size'], r['alias']; priv += 1
for p in list(D.rglob('*.json')) + list(D.rglob('*.txt')) + [D / 'README.md']:
    assert '/Users/' not in p.read_text(errors='replace'), 'user path in ' + str(p)
print('G06 EXECUTION_RECEIPT_OK public', len(res['public_refs']), 'private rehashed', priv)
