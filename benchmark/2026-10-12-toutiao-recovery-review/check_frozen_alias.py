#!/usr/bin/env python3
"""Validate exact archived alias bytes and identity-binding-only changes."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ATTEMPT = HERE / '.artifacts/exe-alias-0cc5a5bd'
ROOT = ATTEMPT / 'frozen'
ALIAS = ROOT / 'benchmark/2026-10-12-recovery-exe-alias'
BASE = ROOT / 'benchmark/2026-10-12-recovery-executor/payload'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ALIAS / 'manifest.json').read_text())
    checks = []
    for row in manifest['files']:
        path = ROOT / row['path']
        matches = sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
        assert matches, row['path']
        checks.append(dict(path=row['path'], sha256=sha(path), matches=matches))
    old = "/data/local/tmp/asx/asx-spawner|'/data/local/tmp/asx/asx-spawner (deleted)'"
    new = old + "|/data/local/tmp/asx/appspawn-x|'/data/local/tmp/asx/appspawn-x (deleted)'"
    delta = []
    for name in ['launch-common.sh', 'watchdog.sh', 'route-b-owner.sh']:
        before = (BASE / name).read_text()
        after = (ALIAS / 'candidate' / name).read_text()
        assert before.count(old) == 1 and after == before.replace(old, new)
        delta.append(dict(file=name, occurrences=1, base_sha256=sha(BASE / name),
                          candidate_sha256=sha(ALIAS / 'candidate' / name)))
    old_watch = sha(BASE / 'watchdog.sh')
    old_helper = sha(BASE / 'route-b-owner.sh')
    assert old_watch == '9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072'
    assert old_helper == '80a263d930a67c48fa92f5caa7b6266ee13ff75079ff5ba880e9576da72dbdc4'
    entry = (BASE / 'entry.sh').read_text()
    expected = entry.replace(old_watch, sha(ALIAS / 'candidate/watchdog.sh')).replace(old_helper, sha(ALIAS / 'candidate/route-b-owner.sh'))
    assert (ALIAS / 'candidate/entry.sh').read_text() == expected
    policy = (BASE / 'startup.env').read_text()
    assert (ALIAS / 'candidate/startup.env').read_text() == policy.replace(sha(BASE / 'members.tsv'), sha(ALIAS / 'candidate/members.tsv'))
    assert (ALIAS / 'candidate/startup.expected.sha256').read_text().strip() == sha(ALIAS / 'candidate/startup.env')
    parent_evidence = HERE.parents[2] / 'westlake-harness/benchmark/2026-10-12-v1-seal-execution/posttap-diagnostics/parent-identity.stdout.txt'
    assert sha(ALIAS / 'evidence/parent-identity.txt') == sha(parent_evidence)
    result = dict(commit='0cc5a5bdd9f5c390a9324916189d726daa63a637', manifest_rows=checks,
                  archive_sha256=sha(ATTEMPT / 'frozen.tar'),
                  manifest_sha256=sha(ALIAS / 'manifest.json'), exact_path_only_delta=delta,
                  entry_only_two_binding_changes=True, policy_only_members_binding_change=True,
                  old_watchdog_sha256=old_watch, old_helper_sha256=old_helper,
                  parent_source_sha256=sha(parent_evidence),
                  approved_scope='independent offline exact-alias correction; outer must rebind actual placement preimages/auth/policy',
                  device_calls=0, board_authorization=False, ui_accepted=False, seal_signed=False)
    (HERE / 'frozen-alias-review-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'manifest': len(checks), 'exact_delta_functions': len(delta), 'bindings': 'PASS', 'exit': 0}))


if __name__ == '__main__':
    main()
