#!/usr/bin/env python3
"""Offline G20 peer evidence replay. Writes only a caller-selected new output dir.

No device, subprocess, git, signature, registry or candidate mutation.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

CARD = 'benchmark/2026-10-21-commercial-game/gles-transaction-package'
OLD = 'benchmark/2026-10-03-u13-final-assembly/evidence/native-v3.json'
PINS = {
    'exception-comparison.json': '99dba69e53fcca6cca8be75df31b6228aae3d39d3069e3259bcd4597fa62e0dc',
    'exceptions.unsigned.json': '4f22913b6500f1ebd08ffcbc86e94c0e416579807a82f02eda10cac54cd5fc33',
    'n1-current-source-attestation.json': '3a47b4a85917a67fabd50517c51dc19918eb199e1be657af66ceb39bacfc858d',
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def normalized(v):
    if isinstance(v, dict):
        return {k: normalized(x) for k, x in v.items()
                if k not in ('line', 'issue_id', 'disposition', 'exception')}
    if isinstance(v, list):
        return list(map(normalized, v))
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--workspaces', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    repo = a.repo.resolve()
    ws = (a.workspaces or repo.parent).resolve()
    card = repo / CARD
    sources = []
    for name, expected in PINS.items():
        p = card / name
        assert sha(p) == expected, name
        sources.append({'path': CARD + '/' + name, 'sha256': sha(p), 'bytes': p.stat().st_size})
    comp = read(card / 'exception-comparison.json')
    unsigned = read(card / 'exceptions.unsigned.json')['exceptions']
    attest = read(card / 'n1-current-source-attestation.json')
    assert attest['outer_approved'] is False and attest['payload_changes'] == []
    evidence = []
    for alias, expected in attest['evidence_pins'].items():
        p = Path(alias.replace('$WORKSPACES', str(ws)).replace('$G20', str(card)))
        assert sha(p) == expected, alias
        evidence.append({'alias': alias, 'sha256': expected, 'bytes': p.stat().st_size})
    assert len(evidence) == 27
    old = read(repo / OLD)
    sources.append({'path': OLD, 'sha256': sha(repo / OLD)})
    registry_path = repo / 'knowledge/gates/native-predeploy-exceptions.json'
    registry = read(registry_path)['exceptions']
    sources.append({'path': str(registry_path.relative_to(repo)), 'sha256': sha(registry_path)})
    approved = {(e['gate'], e['package_manifest_sha256'], e['inputs_sha256'], e['issue_id'])
                for e in registry if e.get('approved_by') and e.get('approved_at')}
    proposal = {(e['package'], e['gate'], e['issue_id']): e for e in unsigned}
    assert len(proposal) == len(unsigned) == 318
    assert all(e['approved_by'] is None and e['approved_at'] is None for e in unsigned)
    rows, line_deltas = [], []
    for package, item in comp['packages'].items():
        assert (item['N1_findings'], item['N1_unmatched_findings'], item['N2_findings'],
                item['N2_changed_object_review']) == (55, 2, 104, 4)
        for row in item['rows']:
            key = (package, row['gate'], row['issue_id'])
            original = proposal[key]
            assert original['package_manifest_sha256'] == item['package_manifest_sha256']
            assert original['inputs_sha256'] == item['inputs_sha256']
            bound = dict(gate=row['gate'], package_manifest_sha256=item['package_manifest_sha256'],
                         inputs_sha256=item['inputs_sha256'], finding=row['finding'])
            issue = hashlib.sha256(json.dumps(bound, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            assert issue == row['issue_id']
            ref = row['old_approval_reference']
            if ref:
                assert (row['gate'], ref['package_manifest_sha256'], ref['inputs_sha256'], ref['issue_id']) in approved
            evidence_refs = [CARD + '/exception-comparison.json', CARD + '/target-coverage.json',
                             CARD + '/transaction-plan.json']
            if row['gate'] == 'N1':
                evidence_refs.append(CARD + '/n1-current-source-attestation.json')
                detail = row['finding'].get('detail', {})
                rationale = ('Current source/artifact attestation binds this finding to the G20 package. '
                             'This retains a bounded initialization/namespace uncertainty, not proof of safe runtime resolution.')
                if not row['exact_finding_match']:
                    matches = [o for o in old['gates']['N1']['findings'] if normalized(o) == normalized(row['finding'])]
                    assert len(matches) == 1
                    old_ev = matches[0]['detail']['evidence']
                    new_ev = detail['evidence']
                    delta = {'package': package, 'issue_id': issue, 'function': detail['function'],
                             'old_line': old_ev['line'], 'current_line': new_ev['line'],
                             'text': new_ev['text'], 'same_finding_except_line': True}
                    line_deltas.append(delta)
                    assert 'RTLD_NOLOAD' in new_ev['text']
                    rationale += ' The unmatched historical key is only a line-number change; the same NOLOAD operation remains.'
                if row['finding'].get('profile') == 'u10-1-resident-compat':
                    rationale += ' Historical U10.1/015aa3a6 identity is not inherited; current artifact/source pins govern.'
            elif row['review_class'] == 'REVIEW_CHANGED_OBJECTS':
                evidence_refs.extend([CARD + '/n1-current-source-attestation.json',
                                      'benchmark/2026-10-21-commercial-game/gles-loader-candidate/results.json',
                                      'benchmark/2026-10-21-commercial-game/gles-loader-candidate/build-01-receipt.json'])
                rationale = ('The historical finding remains, but the listed object-byte changes require this new decision. '
                             'Existing Boat public bytes are the observed current baseline; only the paired loader aliases '
                             'change for G20. Domain provider selection and uncovered-directory closure are not proven.')
            else:
                rationale = ('Finding and inspected package/system-snapshot objects match the historical record; '
                             'this is evidence reuse under new manifest/input pins, not inherited approval or fresh '
                             'measurement of every system-snapshot provider.')
            removal = ('Valid only for the separately authorized bounded G20 GLES single-variable window on '
                       '5ea34a4500000000000000001123012c, with the exact package/inputs and paired aliases. '
                       'Expires at that window close; any package, source, provider, sidecar, namespace policy, '
                       'baseline or finding drift requires new review. Complete initialization/namespace evidence '
                       'or a verified fix removes the need for the exception. No freeze, permanent deployment, '
                       'game success or unique loader winner is asserted.')
            if 'stops inheriting libc' in original['removal_condition']:
                removal += (' Preserve the historical libc-inheritance, libshared_libz, DT_NEEDED and domain-path '
                            're-review triggers; this review does not newly prove that runtime inheritance.')
            rows.append({'package': package, 'gate': row['gate'], 'issue_id': issue,
                         'package_manifest_sha256': item['package_manifest_sha256'],
                         'inputs_sha256': item['inputs_sha256'], 'finding': row['finding'],
                         'review_class': row['review_class'], 'changed_objects': row['changed_objects'],
                         'historical_condition_reference_only': original['removal_condition'],
                         'recommended_reason': 'Proposed for this bounded G20 experiment only. ' + rationale,
                         'recommended_removal_condition': removal, 'evidence': evidence_refs,
                         'review_recommendation': 'ELIGIBLE_FOR_NEW_OUTER_BOUNDED_EXCEPTION_DECISION',
                         'authorization': 'NONE; suggestions must not be loaded as a signed registry'})
    assert len(line_deltas) == 4 and len(rows) == 318
    history = collections.Counter(e['removal_condition'] for e in unsigned)
    assert sum(n for s, n in history.items() if 'N10b single-variable' in s) == 46
    assert sum(n for s, n in history.items() if 'U10.1' in s) == 4
    result = {'status': 'EVIDENCE_REPLAY_PASS_UNSIGNED_RECOMMENDATIONS_ONLY', 'device_calls': 0,
              'signatures_created': 0, 'registry_modified': False, 'proposal_rows': 318,
              'attestation_pins_verified': 27, 'N1_line_only_deltas': line_deltas,
              'historical_conditions': [{'text': k, 'rows': v} for k, v in history.items()],
              'baseline_scope': {'observed_union': 319, 'original_package_targets': 285,
                                 'logical_changes': 2, 'planned_writes': 32, 'same_SHA_writes': 30,
                                 'source': CARD + '/transaction-plan.json',
                                 'verification': 'prior independent review retained; not rerun by this script'},
              'limits': ['No approval or device admission is generated.',
                         'Provider selection and unique runtime winner remain unknown.',
                         '100 N2 unchanged rows per package concern sealed package/snapshot objects, not a new whole-board scan.',
                         'G20 N1/N2 signed registry and actual gate pass remain outer work.'],
              'source_pins': sources}
    a.out.mkdir(parents=True, exist_ok=False)
    for name, obj in [('results.json', result), ('recommendations.json', rows),
                      ('attestation-pin-checks.json', evidence)]:
        (a.out / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': result['status'], 'rows': len(rows), 'pins': len(evidence),
                      'N1_line_deltas': len(line_deltas), 'signed': False}))


if __name__ == '__main__':
    main()
