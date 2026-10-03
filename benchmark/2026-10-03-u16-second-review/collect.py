import copy
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import zipfile

from class_contracts import contract, parse_blocks
from strict_findings import canonical, differences, finding, issue_id, field_proof

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORKSPACES = REPO.parent
MASTER = WORKSPACES / 'westlake-harness'
ASSEMBLY = REPO / 'benchmark/2026-10-03-u16-final-assembly'
PRIOR = REPO / 'benchmark/2026-10-03-u16-assembly-draft'
RELEASE = WORKSPACES / 'westlake-inputs/generations/u16-bt-bake-8593-f6f5-v3-20261003T162410-42707'
DUMP = RELEASE / 'oatdump-u16-20261003T165228-158533'
MANIFEST = '570e82e05981c003d5c214bb24005d3dce4871233d1698bf2f98176725b8b7b9'
INPUTS = 'ff8f0be198fbc4057cb6a1c11922c4e99c2ac90ce88eaedf7177b472057d5f1c'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        return value.replace(str(WORKSPACES) + '/', '$WORKSPACES/').replace(str(Path.home()) + '/', '$HOME/')
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    return value


def load(path):
    return json.loads(Path(path).read_text())


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value), ensure_ascii=False, indent=2) + '\n')


def evidence(path, destination):
    target = HERE / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    return dict(path=portable(path), sha256=sha(path), snapshot=destination, snapshot_sha256=sha(target))


def require_equal(old, new, label):
    changed = differences(old, new)
    if changed:
        raise ValueError(label + ': ' + canonical(changed))
    return dict(equal=True, differences=[], semantic_sha256=hashlib.sha256(canonical(old).encode()).hexdigest())


def image_offsets(before, after):
    if len(before) != len(after):
        raise ValueError('Different image sizes')
    offsets = [index for index, (old_byte, new_byte) in enumerate(zip(before, after)) if old_byte != new_byte]
    if not offsets or any(not 0x3e3b8 <= offset < 0x3e3c0 for offset in offsets):
        raise ValueError('Unexpected boot.art byte difference')
    if before[:8] != b'art\n108\x00' or before[:16] != after[:16]:
        raise ValueError('Unexpected ART image header')
    return offsets


def image_review():
    receipts = [load(ASSEMBLY / f'receipts/paired-run{number}.json') for number in [1, 2]]
    require_equal(receipts[0]['input_jars'], receipts[1]['input_jars'], 'Nine paired inputs')
    if len(receipts[0]['input_jars']) != 9:
        raise ValueError('Need nine inputs')
    for name, expected in receipts[0]['input_jars'].items():
        if sha(RELEASE / 'jars9' / name) != expected:
            raise ValueError('JAR input mismatch: ' + name)
    pair_rows = []
    paired_receipts = []
    for number, receipt in enumerate(receipts, 1):
        if len(receipt['outputs']) != 27:
            raise ValueError('Expected27 run outputs')
        for name, expected in receipt['outputs'].items():
            if sha(RELEASE / f'run{number}' / name) != expected:
                raise ValueError('Actual output mismatch: ' + name)
        for field in ['dex2oat_exit_code', 'tee_exit_code', 'session_tee_exit_code', 'script_exit_code']:
            if receipt[field] != 0:
                raise ValueError('Compiler/session status not0')
        paired_receipts.append(evidence(ASSEMBLY / f'receipts/paired-run{number}.json', f'inputs/paired-run{number}.json'))
    for name in sorted(receipts[0]['outputs']):
        pair_rows.append(dict(name=name, run1_sha256=receipts[0]['outputs'][name], run2_sha256=receipts[1]['outputs'][name],
            identical=receipts[0]['outputs'][name] == receipts[1]['outputs'][name]))
    if [row['name'] for row in pair_rows if not row['identical']] != ['boot.art']:
        raise ValueError('Only boot.art may differ')
    inventory = {}
    for line in (DUMP / 'SHA256SUMS').read_text().splitlines():
        digest, filename = line.split(None, 1)
        inventory[Path(filename).name] = dict(sha256=digest, remote_path=filename.strip())
    records = []
    for number in [1, 2]:
        record = dict(run=number, pieces=[])
        for suffix in ['argv.txt', 'excerpt.txt', 'status.json']:
            name = f'run{number}.{suffix}'
            if sha(DUMP / name) != inventory[name]['sha256']:
                raise ValueError('Returned dump hash mismatch: ' + name)
            record['pieces'].append(evidence(DUMP / name, 'evidence/object-chain/' + name))
        status = load(DUMP / f'run{number}.status.json')
        require_equal(status, dict(oatdump_exit_code=0, tee_exit_code=0), 'Dump status')
        text = (DUMP / f'run{number}.excerpt.txt').read_text()
        for marker in ['CANCELLED: 0x7003e360', 'backtrace: 0x7003e380',
                       '0x7003e380: java.lang.Object[] length:2', '0: 0x7003e3a8',
                       '1: 0x700d51c8   Class: sun.nio.ch.PendingFuture', '0x7003e3a8: long[] length:2']:
            if marker not in text:
                raise ValueError('Missing actual object-chain field: ' + marker)
        record.update(status=status, full_log=inventory[f'run{number}.log'], full_log_locally_read=False)
        records.append(record)
    before, after = [(RELEASE / f'run{number}/boot.art').read_bytes() for number in [1, 2]]
    offsets = image_offsets(before, after)
    image_begin = struct.unpack_from('<I', before, 16)[0]
    if image_begin != 0x70000000 or struct.unpack_from('<i', before, 0x3e3b0)[0] != 2:
        raise ValueError('Image begin or long[] length differs')
    draft = load(ASSEMBLY / 'image-exception-draft.json')
    for number, data in enumerate([before, after], 1):
        if hashlib.sha256(data).hexdigest() != draft[f'run{number}_boot_art_sha256']:
            raise ValueError('New image pair differs')
    for variant in ['common', '61b']:
        root = ASSEMBLY / '.artifacts' / variant
        row = next(member for member in load(root / 'bundle.json')['boot_group']['members']
            if member['target'].endswith('/boot.art'))
        if sha(root / row['source']) != draft['run1_boot_art_sha256'] or row['sha256'] != draft['run1_boot_art_sha256']:
            raise ValueError('Selected bundle boot.art is not run1')
    draft.update(id='u16-boot-art-backtrace-word0', category='image-reproducibility',
        decision='pending', approved_by=None, status='pending-outer-signature', selected_run=1,
        changed_byte_count=len(offsets), byte_offsets=[hex(offset) for offset in offsets],
        field_width_bytes=8, image_begin=hex(image_begin), long_array_address='0x7003e3a8',
        array_length=2, data_offset='0x3e3b8', elements=dict(
            run1=[hex(value) for value in struct.unpack_from('<QQ', before, 0x3e3b8)],
            run2=[hex(value) for value in struct.unpack_from('<QQ', after, 0x3e3b8)]),
        dump_evidence=records, inventory=evidence(DUMP / 'SHA256SUMS', 'evidence/object-chain/SHA256SUMS'),
        paired_receipts=paired_receipts, outputs=pair_rows, strict_identical=26, outputs_total=27,
        frozen_oatdump_sha256='cd3babf9b1db4066c3e38414aeb74a0c251305a9d167a3a547a615ec4519d8f5',
        dump_recipe=evidence(ASSEMBLY / 'dump-object-chain-hw248.sh', 'inputs/dump-object-chain-hw248.sh.txt'),
        owner_header_in_original_excerpt=False,
        owner_attribution='Outer verified PendingFuture.CANCELLED; original grep excerpt omits enclosing Class header; supplementary context requested',
        scope='Only the exact nine-input/new-image pair and first long[2] element interval; no general image-byte waiver')
    draft.pop('needed', None)
    return draft


def native_review():
    source = PRIOR / 'outer-approval-packet.json'
    signed_path = MASTER / 'benchmark/2026-10-03-u16-review/outer-approval-packet.json'
    old, signed = load(source), load(signed_path)
    if sha(source) != 'da1f47285a639f4594b89464594f326f4a8e9c7c9e89319ff27390ba73fd9667':
        raise ValueError('Originally signed request packet changed')
    approved = {}
    for group in signed['decisions']:
        for identifier in group['ids']:
            if identifier in approved:
                raise ValueError('Duplicate signed scope ID')
            approved[identifier] = group
    require_equal(sorted(approved), sorted(row['id'] for row in old['decisions']), 'Signed seventeen scopes')
    if len(approved) != 17:
        raise ValueError('Expected seventeen signed scopes')
    for key in ['native_manifest_sha256', 'native_inputs_sha256']:
        require_equal(old[key], signed['binds'][key], 'Old binding ' + key)
    selected = {}
    base_root = Path(load(ASSEMBLY / 'common/composition.json')['content_base'].replace('$WORKSPACES', str(WORKSPACES)))
    for relative, pinned in old['selected_artifacts'].items():
        paths = [PRIOR / '.artifacts/native-pair-a3/native' / relative]
        paths += [ASSEMBLY / '.artifacts' / variant / 'native' / relative for variant in ['common', '61b']]
        if any(sha(path) != pinned['new'] for path in paths):
            raise ValueError('Selected ELF differs: ' + relative)
        deployed = base_root / 'native' / relative
        if sha(deployed) != pinned['old']:
            raise ValueError('U15 comparison ELF differs: ' + relative)
        selected[relative] = dict(**pinned, identical_bytes=True, paths=paths, deployed=deployed, deployed_sha256=sha(deployed))
    findings_by_variant = {}
    for variant in ['common', '61b']:
        if sha(ASSEMBLY / variant / 'native-manifest.json') != MANIFEST or sha(ASSEMBLY / variant / 'native-inputs.json') != INPUTS:
            raise ValueError('Final native identity mismatch')
        findings_by_variant[variant] = load(ASSEMBLY / variant / 'native-report.json')['gates']['N1']['findings']
        static = load(ASSEMBLY / variant / 'static-report.json')
        flutter = next(row for row in static['members'] if row['target'].endswith('/westlake_flutter/libandroid.so'))
        require_equal(flutter['open_site_delta'], old['static_allowance_draft']['delta'], 'Exact Flutter production delta')
        require_equal(flutter['delta_sha256'], old['static_allowance_draft']['delta_sha256'], 'Exact delta SHA')
    rows = []
    for original in old['decisions']:
        row = copy.deepcopy(original)
        group = approved[row['id']]
        row.update(decision='pending', approved_by=None, previous_signed_scope=group['scope'],
            previous_signed_basis=group['basis'], scope_unchanged=True,
            original_row_sha256=hashlib.sha256(canonical(original).encode()).hexdigest(),
            artifact_bytes_unchanged=True, semantic_fields_equal=True,
            new_binding=dict(native_manifest_sha256=MANIFEST, native_inputs_sha256=INPUTS))
        if 'finding' in original:
            before = finding(original['finding'])
            for variant, findings in findings_by_variant.items():
                matches = [item for item in findings if finding(item) == before]
                if len(matches) != 1:
                    raise ValueError('Exact finding missing/ambiguous: ' + row['id'] + '/' + variant)
                after = matches[0]
                row['semantic_proof'] = require_equal(before, finding(after), 'Finding semantic fields')
                row['field_proofs'] = {name: field_proof(before, finding(after), name) for name in
                    ['profile', 'kind', 'function', 'namespace', 'library', 'target_expression',
                     'evidence.source', 'evidence.line', 'evidence.text', 'reason']}
                new_id = issue_id('N1', after, MANIFEST, INPUTS)
                require_equal(new_id, after['issue_id'], 'New issue ID')
                require_equal(issue_id('N1', original['finding'], old['native_manifest_sha256'], old['native_inputs_sha256']), original['issue_id'], 'Original issue ID')
                row.update(old_issue_id=original['issue_id'], issue_id=new_id, finding=after)
        else:
            row['semantic_proof'] = dict(equal=True, differences=[], basis='Whole selected ELF bytes identical; exact original raw call-set/string row retained')
        rows.append(row)
    proofs = [evidence(path, 'evidence/native/' + path.name) for path in sorted((PRIOR / 'evidence').glob('approval-*.txt'))]
    references = dict(original_request=evidence(source, 'inputs/native-original-request.json'),
        signed_approval=evidence(signed_path, 'inputs/native-signed-approval.json'),
        selected_artifacts=selected, exact_disassembly=proofs, static_allowance=old['static_allowance_draft'],
        old_binding=signed['binds'], new_binding=dict(native_manifest_sha256=MANIFEST, native_inputs_sha256=INPUTS),
        equal=17, changed=0, issue_id_mappings=[dict(id=row['id'], old=row['old_issue_id'], new=row['issue_id'])
            for row in rows if 'old_issue_id' in row])
    save('native-transfer.json', references)
    return rows, references


def git_source(relative):
    commit = subprocess.check_output(['git', '-C', str(MASTER), 'log', '-1', '--format=%H', '--', relative], text=True).strip()
    blob = subprocess.check_output(['git', '-C', str(MASTER), 'rev-parse', commit + ':' + relative], text=True).strip()
    contents = subprocess.check_output(['git', '-C', str(MASTER), 'show', commit + ':' + relative])
    path = MASTER / relative
    if contents != path.read_bytes():
        raise ValueError('Source git blob mismatch: ' + relative)
    return dict(commit=commit, git_blob=blob, **evidence(path, 'inputs/source/' + path.name))


def dump_jar(path, label, tool):
    blocks, records = {}, []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(item for item in archive.namelist() if re.fullmatch(r'classes\d*\.dex', item)):
            dex = HERE / '.artifacts/dex' / label / name
            dex.parent.mkdir(parents=True, exist_ok=True)
            dex.write_bytes(archive.read(name))
            raw = dex.with_suffix('.dexdump.txt')
            with raw.open('wb') as output:
                result = subprocess.run([str(tool), '-l', 'plain', str(dex)], stdout=output, stderr=subprocess.PIPE)
            if result.returncode:
                raise ValueError('dexdump failed: ' + result.stderr.decode(errors='backslashreplace'))
            parsed = parse_blocks(raw.read_text(encoding='utf-8', errors='backslashreplace'))
            if blocks.keys() & parsed.keys():
                raise ValueError('Duplicate DEX descriptor')
            blocks.update(parsed)
            records.append(dict(dex=name, dex_sha256=sha(dex), raw=raw, raw_sha256=sha(raw), exit_code=0, classes=len(parsed)))
    if not blocks:
        raise ValueError('Empty JAR dump')
    return blocks, records


def class_review():
    candidate = ASSEMBLY / '.artifacts/common/framework/adapter-mainline-stubs.jar'
    static = load(ASSEMBLY / 'common/static-report.json')
    jar_check = next(row for row in static['members'] if row['target'].endswith('adapter-mainline-stubs.jar'))
    composition = load(ASSEMBLY / 'common/composition.json')
    base_root = Path(composition['content_base'].replace('$WORKSPACES', str(WORKSPACES)))
    baseline = base_root / 'framework/adapter-mainline-stubs.jar'
    require_equal(sha(baseline), jar_check['deployed_sha256'], 'Base stubs bytes')
    require_equal(sha(candidate), jar_check['candidate_sha256'], 'Candidate stubs bytes')
    tool = sorted((Path.home() / 'Library/Android/sdk/build-tools').glob('*/dexdump'))[-1]
    before, base_records = dump_jar(baseline, 'baseline', tool)
    after, candidate_records = dump_jar(candidate, 'candidate', tool)
    added = sorted(after.keys() - before.keys())
    if before.keys() - after.keys() or len(added) != 8 or len(before) != 276 or len(after) != 284:
        raise ValueError('Expected exact276/284 and eight additions')
    donor_root = MASTER / 'benchmark/2026-10-02-android-net-stub-members/donor'
    donor_digest = hashlib.sha256(b''.join(path.read_bytes() for path in sorted(donor_root.rglob('*.java')))).hexdigest()
    receipt = load(MASTER / 'benchmark/2026-10-03-u16-t1-wifimanager/receipt-u16t1.json')
    require_equal(donor_digest, receipt['donor_sources_sha256'], 'Complete actual donor aggregate')
    require_equal(candidate_records[0]['dex_sha256'], receipt['out_classes_dex_sha256'], 'Actual emitted DEX')
    sources = {name: git_source('benchmark/2026-10-02-android-net-stub-members/donor/android/net/' + name + '.java')
        for name in ['ConnectivityManager', 'DhcpInfo', 'wifi/SupplicantState', 'wifi/WifiManager']}
    rows = []
    for index, descriptor in enumerate(added, 1):
        owner = descriptor[1:-1].split('$')[0].removeprefix('android/net/')
        details = contract(descriptor, after[descriptor])
        source_path = HERE / sources[owner]['snapshot']
        suffix = descriptor.split('$', 1)[1].removesuffix(';') if '$' in descriptor else owner.split('/')[-1]
        anchor = 'new Creator<' if suffix == '1' else ('interface ' if 'Listener' in suffix else 'class ') + suffix
        if owner == 'wifi/SupplicantState' and suffix != '1':
            anchor = 'enum SupplicantState'
        anchors = [(number, line) for number, line in enumerate(source_path.read_text().splitlines(), 1) if anchor in line]
        if len(anchors) != 1:
            raise ValueError('Source anchor missing/ambiguous: ' + descriptor)
        review_notes = {
            'ConnectivityManager': 'Listener interface declares onNetworkActive; presence does not deliver network-active events.',
            'DhcpInfo': 'Parcelable value object / anonymous Creator; copied primitive address fields, no network owner or DHCP service.',
            'wifi/SupplicantState': 'Parcelable enum / anonymous Creator; enum predicates and parcel round-trip only, not supplicant implementation.',
            'wifi/WifiManager': 'Listener or reference-counted lock value type; donor omits service acquire/release and event delivery; no real Wi-Fi guarantee.'
        }
        raw = HERE / f'evidence/classes/class-{index:02d}.txt'
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(after[descriptor])
        diff = HERE / f'evidence/classes/class-{index:02d}.diff'
        diff.write_text(''.join(difflib.unified_diff([], after[descriptor].splitlines(keepends=True),
            fromfile='U15:absent:' + descriptor, tofile='U16:' + descriptor)))
        details.update(id=f'stubs-allow-add-{index:02d}', category='jar-exact-add', decision='pending', approved_by=None,
            baseline_present=False, candidate_present=True, source=sources[owner],
            source_anchor=dict(line=anchors[0][0], text=anchors[0][1]), review=review_notes[owner],
            recommendation='approve exact class addition only after outer review',
            raw=dict(path=portable(raw), sha256=sha(raw), snapshot=f'evidence/classes/class-{index:02d}.txt'),
            diff=dict(path=portable(diff), sha256=sha(diff)),
            candidate_sha256=sha(candidate), deployed_sha256=sha(baseline),
            allow_add=descriptor, beneficiary_keys=['fd-wifianalyzer'], predicted_first_fatal_movement=0,
            prediction='Auxiliary class presence is not eight app walls. t1 targets eight WifiManager member gaps; no radio/service or confirmed first-fatal movement from these additions alone.',
            scope='Exact descriptor and byte-pinned stubs pair only; no allow_drop/reshape, no radio or callback-delivery guarantee')
        rows.append(details)
    command = ['python3', str(MASTER / 'scripts/lab/deployed_class_diff.py'), str(candidate), '--deployed', str(baseline), '--frozen']
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    raw = HERE / '.artifacts/class-diff-raw.txt'
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(result.stdout)
    evidence_path = HERE / 'evidence/class-diff-frozen.txt'
    evidence_path.write_text(portable(result.stdout.decode(encoding='utf-8', errors='backslashreplace')))
    if result.returncode != 1 or '0 dropped, 0 reshaped, 8 added' not in evidence_path.read_text():
        raise ValueError('Unexpected frozen class diff')
    provenance = dict(dexdump=dict(path=tool, sha256=sha(tool)), baseline=base_records, candidate=candidate_records,
        donor_sources_sha256=donor_digest, receipt=evidence(MASTER / 'benchmark/2026-10-03-u16-t1-wifimanager/receipt-u16t1.json', 'inputs/t1-build-receipt.json'),
        source_note='Canonical receipt/build recipe compiles the 2026-10-02 donor aggregate. The t1 eight-method WifiManager donor has no nested classes and is not their source.',
        frozen_diff=dict(command=command, exit_code=result.returncode, raw=raw, raw_sha256=sha(raw), evidence=evidence_path, evidence_sha256=sha(evidence_path)))
    save('class-review.json', dict(classes=rows, provenance=provenance))
    return rows


def outer_gates():
    faces = []
    inventories = []
    for stamp in ['darwin-20261003T165327', 'linux-20261003T170534']:
        report = ASSEMBLY / 'gates' / (stamp + '.json')
        data = load(report)
        inventories.append(evidence(report, 'evidence/gates/' + report.name))
        if len(data['records']) != 2 or data['remote_executed'] is not True:
            raise ValueError('Need two actual outer image runs')
        for variant, record in zip(['common', '61b'], data['records']):
            path = ASSEMBLY / 'evidence' / variant / stamp / 'image.txt'
            if sha(path) != record['evidence_sha256'] or record['exit_code'] != 0:
                raise ValueError('Outer G1/G2 record mismatch')
            parsed = json.loads(path.read_text().splitlines()[-1])
            if parsed['G1'] is not True or parsed['G2'] is not True:
                raise ValueError('Outer G1/G2 not both PASS')
            faces.append(dict(platform=stamp.split('-')[0], variant=variant, exit_code=0, G1=True, G2=True,
                command=record['command'], evidence=evidence(path, f'evidence/gates/{stamp}-{variant}.txt'),
                checker_sha256=parsed['checker_sha256'], swapped_segments=parsed['swapped_segments'],
                probe='java.lang.String#hashCode cand36/ref36 identical', executed_by='outer(claude)'))
    return dict(faces=faces, execution_reports=inventories, four_faces_pass=True,
        not_production_pass=True, execution_enabled=False, rollout_ready=False)


def main():
    image = image_review()
    native, transfer = native_review()
    classes = class_review()
    gates = outer_gates()
    packet = dict(schema='outer-gate-approval/v1', signer=None, signed_at=None, requested_signer='outer(claude)',
        status='pending', native_manifest_sha256=MANIFEST, native_inputs_sha256=INPUTS,
        bundles={variant: sha(ASSEMBLY / variant / 'bundle.json') for variant in ['common', '61b']},
        decisions=[image] + native + classes, counts=dict(image=1, native=17, classes=8, total=26, pending=26),
        native_transfer=transfer, outer_image_gates=gates, execution_enabled=False, rollout_ready=False,
        gate_registry_applied=False, not_approved_here='Production admission, promotion, FZ-009 owner semantics, radio function, rendering or lighting')
    save('outer-approval-packet.json', packet)
    save('image-review.json', image)
    save('outer-g1-g2-receipt.json', gates)
    save('results.json', dict(status='pending-outer-signature', counts=packet['counts'], native_equal=17,
        native_changed=0, class_exact_add=8, strict_images_identical=26, images_total=27,
        changed_image_bytes=3, exception_field_bytes=8, G1_G2_faces=4, G1_G2_exits=[0, 0, 0, 0],
        manifest_sha256=MANIFEST, inputs_sha256=INPUTS, bundles=packet['bundles'], execution_enabled=False,
        rollout_ready=False, gate_registry_applied=False))
    save('assembly-supplement.json', dict(schema='u16-assembly-outer-evidence/v1', package_artifacts_unchanged=True,
        native_manifest_sha256=MANIFEST, native_inputs_sha256=INPUTS, bundles=packet['bundles'],
        second_approval_packet=dict(path=HERE / 'outer-approval-packet.json', sha256=sha(HERE / 'outer-approval-packet.json')),
        outer_image_gates=gates, image_reproduction_decision='pending', execution_enabled=False, rollout_ready=False))
    destination = ASSEMBLY / 'receipts/outer-g1-g2-second-review.json'
    destination.write_bytes((HERE / 'assembly-supplement.json').read_bytes())
    print('REVIEW26 all pending; NATIVE17 exact/0 changed; STUBS8 exact additions; G1/G2 four outer faces exit0; no gate writes')


if __name__ == '__main__':
    main()
