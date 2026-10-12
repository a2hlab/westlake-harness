#!/usr/bin/env python3
"""Build the explicit non-seal source fingerprint from pinned local evidence.

No board transport, no restored package compilation, and no authorization is
created. Historical capture epochs remain attached to their source records;
reviewed control templates are never described as a live measured seal.
"""
import collections
import hashlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import observations

HERE = Path(__file__).resolve().parent
WS = observations.workspace_root(HERE)
MAIN = WS / 'westlake-harness'
PREFIX = 'benchmark/2026-10-12-v1-seal-execution/'
INPUTS = {
    'baseline': ('benchmark/2026-10-12-toutiao-recovery-readonly/archive-1950/index.json', 'a72230ee970e5c15e81dc4f078934c04c3ff73f4bdc4ebbb1db3257b4b886626'),
    'runtime': ('benchmark/2026-10-12-toutiao-recovery-readonly/runtime-archive-2016/index.json', '4de43531569a8206b1aac718ed750bda32748052464479cafe6694ba1f653929'),
    'closure': (PREFIX + 'restore-runtime-closure/index.json', 'd7fcc146e0eb9b3e3cbcaa8154a5c453ac787a09f956b267deb655cb78ec7579'),
    'live_scripts': (PREFIX + 'restore-live-scripts/index.json', '8b316354abd5295d8918ef316cb9ec50e8a79b599b7980794c1838218729153b'),
    'controls': (PREFIX + 'capture-feed-package/plan.enabled.json', '20acc9ac00a48bf928aa57b519f1b255fe19ee013b21c3fa0e0d12c18ab644e7'),
    'target_identity': (PREFIX + 'exact-realization-inputs/target-identity.json', 'a7d9ae13a29e84aeb13a00c6afab7e3b089f43ef0a33c8f8c72be05e50d42fab'),
}
DECLARATION = {'baseline': 319, 'controls': 24, 'runtime': 460, 'stage': 3}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2) + '\n')


def portable(path):
    return '$WORKSPACES/' + str(Path(path).resolve().relative_to(WS.resolve()))


def resolve(path):
    need(isinstance(path, str) and path.startswith('$WORKSPACES/'), 'source must use WORKSPACES')
    return WS / path[len('$WORKSPACES/'):]


def pin(path):
    return {'path': portable(path), 'sha256': sha(path)}


def main():
    docs, paths = {}, {}
    for name, (relative, expected) in INPUTS.items():
        path = MAIN / relative
        need(sha(path) == expected, 'input drift: ' + name)
        paths[name], docs[name] = path, read(path)
    request = read(HERE / 'request.example.json')
    for ref in [*request['v6'].values(), request['user_approval']]:
        need(sha(resolve(ref['path'])) == ref['sha256'], 'reviewed request input drift')
    binding_path = resolve(request['v6']['binding']['path'])
    binding = read(binding_path)
    rows = {}
    checked, unavailable = [], []

    def add(target, digest, source, group, kind, evidence, source_record=None):
        need(isinstance(target, str) and target.startswith('/') and '..' not in target.split('/'), 'unsafe source target')
        need(observations.SHA.fullmatch(digest), 'invalid source digest')
        row = {'groups': [group], 'target': target, 'sha256': digest,
               'provenance': {'kind': kind, 'evidence': pin(evidence)}}
        if source_record:
            row['provenance']['source_record'] = source_record
        if source:
            path = resolve(source)
            if path.is_file():
                need(not path.is_symlink() and sha(path) == digest, 'source bytes drift: ' + target)
                row['source'] = {'path': source, 'sha256': digest}
                checked.append(target)
            else:
                need(group == 'baseline', 'route source unavailable: ' + target)
                row['source_locator'] = {'path': source, 'sha256': digest, 'local_available': False}
                unavailable.append(target)
        if target in rows:
            old = rows[target]
            need(old['sha256'] == digest and group not in old['groups'], 'conflicting/duplicate source target: ' + target)
            old['groups'].append(group)
            old.setdefault('additional_provenance', []).append(row['provenance'])
        else:
            rows[target] = row

    for row in docs['baseline']['files']:
        add(row['target'], row['sha256'], row['source'], 'baseline', 'measured', paths['baseline'])
    live = {row['target']: row for row in docs['live_scripts']['files']}
    need(len(live) == 3 and {Path(t).name for t in live} == {'run.sh', 'preseed_metasec48.sh', 'prepare_jit50.sh'}, 'live script set')
    replacement_audit = []
    for archived in docs['runtime']['files']:
        row = live.get(archived['target'], archived)
        if archived['target'] in live:
            need(row['sha256'] == archived['observed_sha256'], 'live script differs from archived observation')
            evidence = paths['live_scripts']
            replacement_audit.append({'target': row['target'], 'archive_template_sha256': archived['sha256'], 'actual_readback_sha256': row['sha256']})
        else:
            need(archived.get('matches') is True and archived['observed_sha256'] == row['sha256'], 'runtime not measured at source SHA')
            evidence = paths['runtime']
        add(row['target'], row['sha256'], row['source'], 'runtime', 'measured', evidence)
    for row in docs['closure']['files']:
        need(row.get('observed') is True, 'closure item not observed')
        add(row['target'], row['sha256'], row['source'], 'runtime', 'measured', paths['closure'])
    for row in docs['controls']['members']:
        need(row['source'].startswith('$PACKAGE/payload/'), 'unexpected control source')
        source = paths['controls'].parent / row['source'].removeprefix('$PACKAGE/')
        add(row['target'], row['sha256'], portable(source), 'controls', 'reviewed-template', paths['controls'])
    for row in binding['stage_files']:
        evidence_ref = row['metadata_evidence']
        evidence = resolve(evidence_ref['path'])
        need(sha(evidence) == evidence_ref['sha256'], 'stage evidence drift')
        observed = [r for r in read(evidence)['files'] if r['target'] == row['target']]
        need(len(observed) == 1 and observed[0].get('observed') is True and observed[0]['sha256'] == row['source']['sha256'], 'stage measured source mismatch')
        add(row['target'], row['source']['sha256'], row['source']['path'], 'stage', 'measured', evidence,
            {'basis': 'historical donor stage; not current target placement', 'binding': pin(binding_path)})
    counts = dict(collections.Counter(group for row in rows.values() for group in row['groups']))
    need(counts == DECLARATION, 'complete source declaration mismatch: ' + str(counts))
    fingerprint = {'schema': 'exact-source-fingerprint/v1', 'status': 'candidate/not_sealed',
                   'serial': docs['baseline']['serial'], 'boot_id': None,
                   'declaration': DECLARATION, 'files': sorted(rows.values(), key=lambda row: row['target']),
                   'measurement_epochs': {name: {'evidence': pin(paths[name]),
                       'boot_id': docs[name].get('boot_id', docs[name].get('boot_before')),
                       'basis': 'historical source evidence, not a simultaneous current-board seal'}
                       for name in ('baseline', 'runtime', 'closure', 'live_scripts')},
                   'note': 'Composite candidate fingerprint only. Controls are reviewed templates; measured files retain their actual evidence epochs. No seal or signed deployment authority is asserted.'}
    fp_path = HERE / 'source-fingerprint.json'
    write(fp_path, fingerprint)
    request['source_identity'] = {'kind': 'candidate-fingerprint', 'path': fp_path.name, 'sha256': sha(fp_path)}
    request['source_seal'] = None
    request['parameter_evidence'] = pin(paths['target_identity'])
    identity = docs['target_identity']
    request['parameters'] = {'serial': identity['serial'], 'boot_id': identity['boot_before'],
                            'host_uid': identity['host_uid'], 'host_gid': identity['host_gid'],
                            'control_root': binding['attempt_root'], 'window_id': None}
    validated = observations.validate(request['parameter_evidence'], HERE, request['parameters'], 'placement')
    need(validated['synthetic'] is False, 'actual request requires nonsynthetic observation')
    request_path = HERE / 'request.5cd.placement.json'
    write(request_path, request)
    report = {'schema': 'exact-realization-input-build/v1', 'status': 'PASS', 'builder': pin(Path(__file__)),
              'inputs': {name: pin(path) for name, path in paths.items()},
              'fingerprint': pin(fp_path), 'request': pin(request_path),
              'declaration': counts, 'unique_source_targets': len(rows),
              'locally_rehashed_source_rows': len(checked), 'baseline_local_bytes_unavailable': unavailable,
              'actual_script_replacements': replacement_audit,
              'provenance_counts': dict(collections.Counter(row['provenance']['kind'] for row in rows.values())),
              'target_observation_validated': True, 'source_seal': None, 'execution_enabled': False,
              'device_calls': 0, 'network_calls': 0, 'compiler_invoked': False}
    (HERE / 'evidence').mkdir(exist_ok=True)
    write(HERE / 'evidence/input-build.json', report)
    print(json.dumps({k: report[k] for k in ('status', 'declaration', 'unique_source_targets', 'locally_rehashed_source_rows', 'provenance_counts', 'fingerprint', 'request')}))


if __name__ == '__main__':
    main()
