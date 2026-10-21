#!/usr/bin/env python3
"""Assemble a complete, NOT-approved candidate package from the read-only r3 deploy package.

Only watchdog.sh (candidate revision) and reentry-common.sh (r4 common) change; every other member is
copied byte-for-byte from benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root.
The two binary members absent from that checkout (screen-gate, decoder-probe.jpeg) are taken from
--blob-dir and must match the r3 members.tsv SHA exactly. The pin chain is then recomputed:
entry.sh literal watchdog pin -> members.tsv -> startup.env (STARTUP_MEMBERS_SHA) ->
startup.expected.sha256 -> ../MANIFEST.sha256. startup.env is DISABLED and marked unapproved: an
outer-loop approval and a fresh device generation are required before any placement.

usage: assemble-payload.py WATCHDOG COMMON BLOB_DIR OUT_PACKAGE_DIR
"""
import hashlib, json, re, shutil, sys
from pathlib import Path

wd, common, blobs, out = (Path(a).resolve() for a in sys.argv[1:5])
here = Path(__file__).resolve().parent
repo = here.parents[3]
base = repo / 'benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root'
sha = lambda b: hashlib.sha256(b).hexdigest()
members = [l.split() for l in (base / 'payload/members.tsv').read_text().splitlines()]
want = {n: s for s, n, _m in members}
assert want['watchdog.sh'].startswith('8bf74a08') and want['reentry-common.sh'].startswith('43d7b073')
if out.exists():
    sys.exit(f'refuse: {out} exists')
pay = out / 'payload'; pay.mkdir(parents=True)
data = {}
for f in sorted((base / 'payload').iterdir()):
    data[f.name] = f.read_bytes()
for name in ('screen-gate', 'decoder-probe.jpeg'):
    b = (blobs / name).read_bytes()
    assert sha(b) == want[name], (name, sha(b), want[name])
    data[name] = b
old_wd = want['watchdog.sh']
data['watchdog.sh'] = wd.read_bytes(); data['reentry-common.sh'] = common.read_bytes()
entry = data['entry.sh'].decode()
assert entry.count(old_wd) == 1, 'entry.sh watchdog pin not unique'
data['entry.sh'] = entry.replace(old_wd, sha(data['watchdog.sh'])).encode()
rows = []
for s, n, m in members:
    rows.append(f'{sha(data[n])} {n} {m}')
data['members.tsv'] = ('\n'.join(rows) + '\n').encode()
env = data['startup.env'].decode()
env, k = re.subn(r"^STARTUP_MEMBERS_SHA='[0-9a-f]{64}'$", f"STARTUP_MEMBERS_SHA='{sha(data['members.tsv'])}'", env, flags=re.M); assert k == 1
env, k = re.subn(r"^STARTUP_ENABLED='1'$", "STARTUP_ENABLED='0'", env, flags=re.M); assert k == 1
env, k = re.subn(r"^STARTUP_APPROVED_BY='[^']*'$", "STARTUP_APPROVED_BY='UNAPPROVED-T36-candidate'", env, flags=re.M); assert k == 1
data['startup.env'] = env.encode()
data['startup.expected.sha256'] = (sha(data['startup.env']) + '\n').encode()
for n, b in sorted(data.items()):
    (pay / n).write_bytes(b)
man = ''.join(f'{sha(b)}  payload/{n}\n' for n, b in sorted(data.items()))
(out / 'MANIFEST.sha256').write_text(man)
changed = sorted(n for n, b in data.items() if not (base / 'payload' / n).is_file() or (base / 'payload' / n).read_bytes() != b)
info = dict(schema='t36-candidate-package/v1', base='deploy-package-r3-root', approved=False, startup_enabled=0,
            watchdog_sha256=sha(data['watchdog.sh']), reentry_common_sha256=sha(data['reentry-common.sh']),
            members_tsv_sha256=sha(data['members.tsv']), startup_env_sha256=sha(data['startup.env']),
            manifest_sha256=sha(man.encode()), payload_files=len(data), changed_vs_r3=changed,
            blobs_from_outside_r3_checkout={n: sha(data[n]) for n in ('screen-gate', 'decoder-probe.jpeg')},
            files={n: sha(b) for n, b in sorted(data.items())})
(out / 'package.json').write_text(json.dumps(info, indent=2) + '\n')
print(json.dumps({k: info[k] for k in ('watchdog_sha256', 'members_tsv_sha256', 'startup_env_sha256', 'manifest_sha256', 'payload_files', 'changed_vs_r3')}))
