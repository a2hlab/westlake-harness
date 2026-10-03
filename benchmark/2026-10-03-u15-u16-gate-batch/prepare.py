import copy
import json
from pathlib import Path
import shutil
import subprocess

from core import digest, encoded, append_rows, patch_bytes
from strict_findings import canonical, differences, finding, issue_id

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = REPO.parent
MASTER = WS / 'westlake-harness'
BENCH = 'benchmark/2026-10-03-u15-u16-gate-batch'
NATIVE = 'knowledge/gates/native-predeploy-exceptions.json'
IMAGE = 'knowledge/gates/image-provenance-exceptions.json'
APPROVALS = {
    'u15': 'benchmark/2026-10-03-u15-review/outer-approval-packet.json',
    'u16-first': 'benchmark/2026-10-03-u16-review/outer-approval-packet.json',
    'u16-second': 'benchmark/2026-10-03-u16-review/outer-approval-packet-2.json'
}


def load(path):
    return json.loads(Path(path).read_text())


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))


def snapshot(path, relative):
    destination = HERE / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)
    return dict(path=str(path.relative_to(MASTER)) if path.is_relative_to(MASTER) else '$WORKSPACES/' + str(path.relative_to(WS)),
        sha256=digest(path.read_bytes()), snapshot=relative)


def append_change(name, before, rows, target):
    after = append_rows(before, rows)
    save('rows/' + name + '.json', rows)
    patch = patch_bytes(before, after, target)
    patch_file = 'patches/' + name + '.patch'
    (HERE / patch_file).parent.mkdir(parents=True, exist_ok=True)
    (HERE / patch_file).write_bytes(patch)
    return dict(name=name, kind='append-exceptions', target=target, before_sha256=digest(before),
        after_sha256=digest(after), rows='rows/' + name + '.json', rows_sha256=digest(encoded(rows)),
        added=len(rows), patch=patch_file, patch_sha256=digest(patch)), after


def u15_rows(registry, approval):
    comparison = load(MASTER / 'benchmark/2026-10-03-u15-outer-review-packet/registry-comparison.json')
    if comparison['count'] != 204 or comparison['strictly_equal'] != 198 or comparison['different'] != 6:
        raise ValueError('U15 count differs from signed204')
    rows = []
    proof = []
    for item in comparison['rows']:
        before, after = item['old_finding'], item['new_finding']
        changed = differences(before, after)
        if changed != item['differences'] or any(not row['path'].endswith('/line') for row in changed):
            raise ValueError('U15 unauthorized finding drift')
        for version in ['old', 'new']:
            if issue_id(item['gate'], item[version + '_finding'], item[version + '_manifest_sha256'], item[version + '_inputs_sha256']) != item[version + '_issue_id']:
                raise ValueError('U15 issue ID mismatch')
        sources = [row for row in registry if row['gate'] == item['gate'] and row['issue_id'] == item['old_issue_id']
            and row['package_manifest_sha256'] == item['old_manifest_sha256'] and row['inputs_sha256'] == item['old_inputs_sha256']]
        if len(sources) != 1 or not sources[0].get('approved_by'):
            raise ValueError('Missing unique approved U14 source')
        row = copy.deepcopy(sources[0])
        row.update(package_manifest_sha256=item['new_manifest_sha256'], inputs_sha256=item['new_inputs_sha256'],
            issue_id=item['new_issue_id'], approved_by='outer(claude)', approved_at=approval['signed_at'],
            reason='Signed U15 204-row rebind: ' + ('explicitly reviewed line-only change' if changed else 'all finding fields strictly identical'),
            evidence=[APPROVALS['u15'], 'benchmark/2026-10-03-u15-outer-review-packet/registry-comparison.json'],
            auto_from=dict(package_manifest_sha256=item['old_manifest_sha256'], inputs_sha256=item['old_inputs_sha256'], issue_id=item['old_issue_id']))
        rows.append(row)
        proof.append(dict(gate=item['gate'], old_issue_id=item['old_issue_id'], new_issue_id=item['new_issue_id'],
            strict_equal=not changed, differences=changed))
    save('evidence/u15-204-proof.json', proof)
    return rows, comparison


def u16_rows(u15, comparison, approval, packet):
    report = load(MASTER / 'benchmark/2026-10-03-u16-final-assembly/common/native-report.json')
    before = {(item['gate'], canonical(item['new_finding'])): item for item in comparison['rows']}
    source = {(row['gate'], row['issue_id']): row for row in u15}
    signed = {row['issue_id']: row for row in packet['decisions'] if 'finding' in row}
    manifest, inputs = packet['native_manifest_sha256'], packet['native_inputs_sha256']
    rows, proofs = [], []
    matched, direct = 0, 0
    for gate, details in report['gates'].items():
        for item in details['findings']:
            semantic = finding(item)
            identifier = issue_id(gate, item, manifest, inputs)
            if identifier != item['issue_id']:
                raise ValueError('U16 final ID mismatch')
            old = before.get((gate, canonical(semantic)))
            if old is not None:
                previous = source[gate, old['new_issue_id']]
                row = copy.deepcopy(previous)
                row['auto_from'] = dict(package_manifest_sha256=previous['package_manifest_sha256'], inputs_sha256=previous['inputs_sha256'], issue_id=previous['issue_id'])
                row['reason'] = 'Strictly identical to signed U15 finding; every evidence line/sequence is retained'
                matched += 1
            elif identifier in signed and finding(signed[identifier]['finding']) == semantic:
                previous = signed[identifier]
                row = dict(gate=gate, reason='Signed U16 exact scope: ' + previous['previous_signed_scope'],
                    removal_condition='Any finding/source/object drift requires new outer review; remove when the finding is fixed')
                direct += 1
            else:
                raise ValueError('Unapproved U16 finding: ' + identifier)
            row.update(issue_id=identifier, package_manifest_sha256=manifest, inputs_sha256=inputs,
                approved_by='outer(claude)', approved_at=approval['signed_at'],
                evidence=[APPROVALS['u16-first'], APPROVALS['u16-second'],
                    'benchmark/2026-10-03-u16-second-review/native-transfer.json',
                    BENCH + '/evidence/u16-208-proof.json'])
            rows.append(row)
            proofs.append(dict(gate=gate, new_issue_id=identifier, classification='strict-inherited' if old else 'explicit-signed',
                old_issue_id=old['new_issue_id'] if old else previous['old_issue_id'],
                scope_id=None if old else previous['id'], semantic_sha256=digest(canonical(semantic).encode()),
                differences=[]))
    if (len(rows), matched, direct) != (208, 202, 6):
        raise ValueError('Expected208=202strict+6signed')
    save('evidence/u16-208-proof.json', proofs)
    return rows


def image_row(approval, packet):
    original = packet['decisions'][0]
    context = WS / 'westlake-inputs/generations/u16-bt-bake-8593-f6f5-v3-20261003T162410-42707/oatdump-u16-20261003T165228-158533/run1.lines-132700-132753.txt'
    expected = 'e358fa5747480aafdd424ab6ad26b22770dba1d904429e300acd1ee7f678f249'
    if digest(context.read_bytes()) != expected:
        raise ValueError('PendingFuture context hash mismatch')
    lines = context.read_text().splitlines()
    header = next(index for index, line in enumerate(lines) if '0x700d51c8: java.lang.Class "sun.nio.ch.PendingFuture"' in line)
    sentinel = next(index for index, line in enumerate(lines) if 'CANCELLED: 0x7003e360' in line)
    if not header < sentinel or any('java.lang.Class "' in line for line in lines[header + 1:sentinel]):
        raise ValueError('CANCELLED owner header differs')
    supplement = snapshot(context, 'evidence/run1.lines-132700-132753.txt')
    save('evidence/object-owner-supplement.json', dict(context=supplement, first_original_line=132700,
        class_header_line=132700 + header, static_field_line=132700 + sentinel,
        class_address='0x700d51c8', class_name='sun.nio.ch.PendingFuture', CANCELLED='0x7003e360',
        signed_packet_unmodified=True, run2_owner_header_locally_available=False,
        limitation='Fresh supplementary run1 context; original two-run excerpts and outer signature establish the shared chain'))
    return dict(id='U16-REPRO-BACKTRACE-001', status='approved', classification='verified-with-exception',
        approval=dict(authority='outer claude', board='app-lighting', entry=90, timestamp=approval['signed_at']),
        scope=approval['decisions'][0]['scope'], reason=approval['decisions'][0]['basis'],
        object=dict(file='boot.art', reference_sha256=original['run1_boot_art_sha256'],
            reproduced_sha256=original['run2_boot_art_sha256'], object='sun.nio.ch.PendingFuture.CANCELLED.backtrace[0] long[2] element0',
            file_offset_start='0x3e3b8', file_offset_end_exclusive='0x3e3c0', observed_changed_offsets=original['byte_offsets']),
        input_jars=original['input_jars'], outputs=original['outputs'], frozen_oatdump_sha256=original['frozen_oatdump_sha256'],
        evidence={APPROVALS['u16-second']: digest((MASTER / APPROVALS['u16-second']).read_bytes()),
            'benchmark/2026-10-03-u16-second-review/image-review.json': digest((MASTER / 'benchmark/2026-10-03-u16-second-review/image-review.json').read_bytes()),
            BENCH + '/evidence/run1.lines-132700-132753.txt': expected},
        guard=dict(other_26_files_must_match_reference=True, boot_art_outside_field_must_be_identical=True,
            exact_nine_inputs_required=True, preserve_selected_run1=True),
        removal_condition='Any new input, output pair or out-of-range delta needs independent approval; no tool/source changes authorized')


def static_changes(approvals, packet):
    changes = []
    classes15 = load(MASTER / 'benchmark/2026-10-03-u15-outer-review-packet/classes.json')['classes']
    for version, folder in [('u15', '2026-10-03-u15-on-u14-base'), ('u16', '2026-10-03-u16-final-assembly')]:
        bundle = load(MASTER / 'benchmark' / folder / 'common/bundle.json')
        root = REPO / 'benchmark' / folder / '.artifacts'
        root = sorted(root.glob('common-*'))[-1] if version == 'u15' else root / 'common'
        policy_source = root / bundle['static_checks']['policy']['source']
        before = policy_source.read_bytes()
        if digest(before) != bundle['static_checks']['policy']['sha256']:
            raise ValueError('Authorized policy preimage drift')
        snapshot(policy_source, f'inputs/static-{version}-before.json')
        policy = json.loads(before)
        report_path = MASTER / 'benchmark' / folder / ('common/evidence/static.json' if version == 'u15' else 'common/static-report.json')
        report = load(report_path)
        relevant = [row for row in report['members'] if row['kind'] == 'DEX-JAR' and row['status'] == 'REJECT']
        for member in relevant:
            descriptors = [row['descriptor'] for row in classes15 if row['jar'].endswith(Path(member['target']).name)] if version == 'u15' else [row['descriptor'] for row in packet['decisions'] if row['category'] == 'jar-exact-add']
            expected_count = 8 if member['target'].endswith('adapter-mainline-stubs.jar') else 5
            if len(descriptors) != expected_count:
                raise ValueError('Exact class list differs')
            policy['jars'][member['target']] = dict(candidate_sha256=member['candidate_sha256'],
                deployed_sha256=member['deployed_sha256'], allow_add=descriptors, approved_by='outer(claude)',
                evidence=[APPROVALS['u15'] if version == 'u15' else APPROVALS['u16-second']])
        if version == 'u16':
            member = next(row for row in report['members'] if row['target'].endswith('/westlake_flutter/libandroid.so'))
            signed_delta = packet['native_transfer']['static_allowance']
            if member['delta_sha256'] != signed_delta['delta_sha256'] or member['open_site_delta'] != signed_delta['delta']:
                raise ValueError('Flutter signed delta mismatch')
            policy['native'][member['target']] = dict(candidate_sha256=member['candidate_sha256'], deployed_sha256=member['deployed_sha256'],
                delta_sha256=member['delta_sha256'], approved_by='outer(claude)', evidence=[APPROVALS['u16-first'], APPROVALS['u16-second']])
        after = encoded(policy)
        save(f'inputs/static-{version}-after.json', policy)
        patch = patch_bytes(before, after, bundle['static_checks']['policy']['source'])
        patch_path = f'patches/static-{version}.patch'
        (HERE / patch_path).write_bytes(patch)
        changes.append(dict(name='static-' + version, kind='derive-static-policy',
            target=BENCH + f'/.artifacts/applied-static/static-policy-{version}-approved.json',
            before_sha256=None, after_sha256=digest(after), original_policy_name=bundle['static_checks']['policy']['source'],
            original_policy=dict(path='$WORKSPACES/' + str(policy_source.relative_to(WS)), sha256=digest(before)),
            preimage_snapshot=f'inputs/static-{version}-before.json', preimage_snapshot_sha256=digest(before),
            candidate_snapshot=f'inputs/static-{version}-after.json', patch=patch_path, patch_sha256=digest(patch)))
    return changes


def main():
    approvals = {key: load(MASTER / path) for key, path in APPROVALS.items()}
    references = [snapshot(MASTER / path, 'inputs/' + key + '-approval.json') for key, path in APPROVALS.items()]
    if any(approval['signer'] != 'outer(claude)' for approval in approvals.values()):
        raise ValueError('Missing outer signature')
    packet_path = MASTER / 'benchmark/2026-10-03-u16-second-review/outer-approval-packet.json'
    packet = load(packet_path)
    if digest(packet_path.read_bytes()) != '240662979e46d63abdf5dd6a5818368313a90513afa8facc90c33660040753fa':
        raise ValueError('Signed packet changed')
    original = (MASTER / NATIVE).read_bytes()
    registry = json.loads(original)['exceptions']
    rows15, comparison = u15_rows(registry, approvals['u15'])
    rows16 = u16_rows(rows15, comparison, approvals['u16-second'], packet)
    change15, native15 = append_change('native-u15-204', original, rows15, NATIVE)
    change16, native16 = append_change('native-u16-208', native15, rows16, NATIVE)
    change_image, image = append_change('image-u16-1', (MASTER / IMAGE).read_bytes(), [image_row(approvals['u16-second'], packet)], IMAGE)
    static = static_changes(approvals, packet)
    commands = [
        ['python3', 'scripts/lab/check_frozen.py', '--git'],
        ['python3', 'benchmark/2026-10-01-native-gate-landing/test_predeploy_hook.py'],
        ['python3', 'benchmark/2026-10-02-t8-executor-support/test_static_checks.py']
    ]
    prerequisites = references + [dict(path=command[1], sha256=digest((MASTER / command[1]).read_bytes())) for command in commands]
    prerequisites += [dict(path='scripts/lab/' + name, sha256=digest((MASTER / 'scripts/lab' / name).read_bytes())) for name in
        ['board_note.sh', 'deployment_native_gate.py', 'native_predeploy.py', 'native_gate_common.py', 'generation_static_checks.py', 'generation_bundle.py']]
    plan = dict(schema='signed-gate-batch/v1', execution_enabled=False, rollout_ready=False,
        stages=[dict(name='native-u15', changes=[change15]), dict(name='native-u16', changes=[change16]),
            dict(name='image-u16', changes=[change_image]), dict(name='static-policy', changes=static)],
        prerequisites=prerequisites, selftests=commands,
        new_evidence_prerequisites=[dict(path=BENCH + '/' + name, sha256=digest((HERE / name).read_bytes())) for name in
            ['evidence/u16-208-proof.json', 'evidence/run1.lines-132700-132753.txt', 'evidence/object-owner-supplement.json']],
        local_prerequisites=[dict(path=name, sha256=digest((HERE / name).read_bytes())) for name in ['apply_batch.py', 'core.py']],
        serials=['5ea34a4500000000000000001123012c', '5cd1e3dd00000000000000000923012c', '61b0657200000000000000000324012c'],
        counts=dict(u15_native=204, u16_native=208, u16_inherited=202, u16_explicit=6, image=1, u15_allow_add=13, u16_allow_add=8,
            native_before=len(registry), native_after=len(json.loads(native16)['exceptions']), image_before=len(load(MASTER / IMAGE)['exceptions']), image_after=len(json.loads(image)['exceptions'])))
    save('change-plan.json', plan)
    save('results.json', dict(prepared=True, applied=False, gate_registry_applied=False, counts=plan['counts'],
        execution_enabled=False, rollout_ready=False, native_after_sha256=digest(native16), image_after_sha256=digest(image)))
    save('scope-projection.json', dict(first17='Four N1 plus two shifted N1 transfer into the final208; exact Flutter static delta carries four opens, M1 calls and strings remain signature-referenced review evidence, not fictitious registry rows',
        second26='1 image row + same17 transferred scopes +8 exact class additions; no partial-only manifest rows added',
        u15='204 native rows +13 exact class additions; ANL/host bytes and signed paired condition unchanged',
        signed_packets_unchanged=True, authorized_bundles_unchanged=True, new_gate_schemas=False))
    print('PREPARED native204+208 (202strict+6signed), image+1, static13+8 exact classes; no target writes')


if __name__ == '__main__':
    main()
