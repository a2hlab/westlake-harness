"""Verify returned bake bytes and compose disabled local content; no remote IO."""
import argparse
import hashlib
import json
import re
import shlex
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = REPO.parent
MASTER = WS / 'westlake-harness'
DRAFT = REPO / 'benchmark/2026-10-03-u16-assembly-draft'
BAKE = REPO / 'benchmark/2026-10-03-u16-image-bake'
RELEASE = WS / 'westlake-inputs/generations/u16-bt-bake-8593-f6f5-v3-20261003T162410-42707'
ATTEMPT = '20261003T162410-42707'


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def portable(value):
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        value = value.replace(str(WS) + '/', '$WORKSPACES/')
        return re.sub(r'/home/[^/\s\"\']+', '$LAB_HOME', value)
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    return value


def save(path, value, public=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(portable(value) if public else value, default=str, indent=2, ensure_ascii=False) + '\n')


def expand(value):
    return WS / value.removeprefix('$WORKSPACES/')


def image_names():
    segments = ['boot', 'boot-core-libart', 'boot-core-icu4j', 'boot-okhttp', 'boot-bouncycastle',
                'boot-apache-xml', 'boot-adapter-mainline-stubs', 'boot-framework', 'boot-oh-adapter-framework']
    return {segment + '.' + suffix for segment in segments for suffix in ('art', 'oat', 'vdex')}


def validate_receipt(receipt, inputs, outputs):
    if len(inputs) != 9 or len(outputs) != 27 or set(outputs) != image_names():
        raise ValueError('incomplete nine/27 inventory')
    if receipt['input_jars'] != inputs or receipt['outputs'] != outputs:
        raise ValueError('receipt inventory drift')
    for name in ('dex2oat_exit_code', 'tee_exit_code', 'session_tee_exit_code', 'script_exit_code'):
        if receipt.get(name) != 0:
            raise ValueError('failed build or tee: ' + name)
    if receipt.get('exception_used') or receipt.get('reproduction_approved'):
        raise ValueError('no U16 exception approval yet')
    if receipt['status'] != 'verified' or not receipt['actual_argv'] or not receipt['build_command']:
        raise ValueError('missing actual command')
    for name in ('toolchain_identity_sha256', 'build_log_sha256', 'session_log_sha256'):
        if not re.fullmatch('[a-f0-9]{64}', receipt.get(name, '')):
            raise ValueError('missing hashed build evidence')


def validate_pair(rows):
    if len(rows) != 27 or {row['name'] for row in rows} != image_names():
        raise ValueError('incomplete pair')
    differences = [row for row in rows if not row['identical']]
    if len(differences) != 1 or differences[0]['name'] != 'boot.art' or not differences[0]['same_size']:
        raise ValueError('unexpected pair delta')
    if not differences[0]['offsets'] or any(not 0x3e3b8 <= int(offset, 16) < 0x3e3c0 for offset in differences[0]['offsets']):
        raise ValueError('outside known identity field')


def audit():
    inventory = []
    for line in (RELEASE / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        source = (RELEASE / name).resolve()
        if not source.is_relative_to(RELEASE.resolve()) or sha(source) != digest or name in {row['name'] for row in inventory}:
            raise ValueError('sealed inventory mismatch: ' + name)
        inventory.append({'name': name, 'sha256': digest})
    template = load(BAKE / 'paired-receipt.template.json')['runs'][0]
    inputs = {name: sha(RELEASE / 'jars9' / name) for name in template['input_jars']}
    if inputs != template['input_jars']:
        raise ValueError('frozen nine inputs drift')
    for row in load(BAKE / 'handoff.json')['members']:
        if sha(RELEASE / row['member']) != row['sha256']:
            raise ValueError('returned handoff differs: ' + row['member'])
    if (RELEASE / 'logs/hostlibs-run1.sha256').read_bytes() != (RELEASE / 'logs/hostlibs-run2.sha256').read_bytes():
        raise ValueError('hostlibs differ between runs')
    if (RELEASE / 'logs/hostlibs-run1.sha256').read_bytes() != (RELEASE / 'plan/inputs/hostlibs.expected.sha256').read_bytes():
        raise ValueError('frozen hostlibs mismatch')
    runs = []
    for number in (1, 2):
        root = RELEASE / f'run{number}'
        if {path.name for path in root.iterdir()} != image_names() or any(path.is_symlink() or not path.is_file() or path.stat().st_size == 0 for path in root.iterdir()):
            raise ValueError('missing image or unexpected link')
        logs = RELEASE / 'logs'
        compiler = logs / f'dex2oat-run{number}.log'
        session = logs / f'bake-run{number}.session.log'
        argv_file = logs / f'dex2oat-run{number}.argv.json'
        argv = load(argv_file)
        commands = [line.split('dex2oat.cc:3192] ', 1)[1] for line in compiler.read_text().splitlines() if 'dex2oat.cc:3192] ' in line]
        if len(commands) != 1 or shlex.split(commands[0]) != argv:
            raise ValueError('actual log/argv mismatch')
        home = argv[0].removesuffix('/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64')
        if hashlib.sha256(home.encode()).hexdigest() != '4e5277d9907dc562d2135c48e53fa1ed5764ab628dae1e8e397499e708a1c102':
            raise ValueError('frozen LAB_HOME drift')
        expected = [value.replace('$LAB_HOME', home).replace('$U16_ATTEMPT', ATTEMPT)
                    for value in load(BAKE / 'planned-argv.json')[f'run{number}']]
        if argv != expected:
            raise ValueError('actual compiler argv differs from planned attempt')
        for needle in (template['dex2oat_sha256'], template['driver_sha256'], 'host=ecs-9f6c', '[u16-bake] end='):
            if needle not in session.read_text():
                raise ValueError('missing live frozen identity ' + needle)
        driver = load(logs / f't5-run{number}.status.json')
        if driver != {'t5_exit_code': 6}:
            raise ValueError('unexpected old-reference comparison status')
        identity = {'machine': 'ecs-9f6c/hw248', 'os': 'Linux x86_64',
                    'dex2oat_sha256': template['dex2oat_sha256'], 'driver_sha256': template['driver_sha256'],
                    'wrapper_sha256': sha(RELEASE / 'plan/dex2oat-tee.sh'),
                    'recipe_sha256': sha(RELEASE / 'plan/planned-bake.sh'),
                    'hostlibs_sha256': sha(logs / f'hostlibs-run{number}.sha256'),
                    'ldd_sha256': sha(logs / f'ldd-run{number}.txt'), 'session_sha256': sha(session)}
        identity_file = HERE / 'receipts' / f'toolchain-run{number}.json'
        save(identity_file, identity)
        receipt = {'run': number, 'status': 'verified', 'selected': number == 1,
                   'input_jars': inputs, 'outputs': {name: sha(root / name) for name in sorted(image_names())},
                   'actual_argv': argv, 'actual_argv_file_sha256': sha(argv_file), 'build_command': commands[0],
                   'dex2oat_sha256': template['dex2oat_sha256'], 'driver_sha256': template['driver_sha256'],
                   'toolchain_identity_sha256': sha(identity_file), 'build_log': compiler, 'build_log_sha256': sha(compiler),
                   'session_log': session, 'session_log_sha256': sha(session), 'persistent_root': RELEASE,
                   **load(logs / f'dex2oat-run{number}.status.json'), **load(logs / f'session-run{number}.status.json'), **driver,
                   'exception_used': False, 'reproduction_approved': False,
                   'scope': 'actual compiler receipt verified; strict26/27 pair and new boot.art exception still pending'}
        validate_receipt(receipt, inputs, receipt['outputs'])
        save(HERE / f'.artifacts/receipts/paired-run{number}.json', receipt, public=False)
        save(HERE / f'receipts/paired-run{number}.json', receipt)
        runs.append(receipt)
    if runs[0]['actual_argv'] != runs[1]['actual_argv']:
        raise ValueError('two runs did not use same work/compiler invocation')
    comparisons = []
    for name in sorted(image_names()):
        first, second = (RELEASE / 'run1' / name).read_bytes(), (RELEASE / 'run2' / name).read_bytes()
        comparisons.append({'name': name, 'run1_sha256': runs[0]['outputs'][name], 'run2_sha256': runs[1]['outputs'][name],
                            'same_size': len(first) == len(second), 'identical': first == second,
                            'offsets': [hex(index) for index, pair in enumerate(zip(first, second)) if pair[0] != pair[1]]})
    validate_pair(comparisons)
    save(HERE / 'receipts/inventory.json', {'count': len(inventory), 'SHA256SUMS_sha256': sha(RELEASE / 'SHA256SUMS'), 'files': inventory})
    save(HERE / 'reproduction-review.json', {'selected_run': 1, 'strict_identical': 26, 'total': 27,
          'comparisons': comparisons, 'exception_approved': False, 'object_chain_verified': False, 'execution_enabled': False})
    save(HERE / 'image-exception-draft.json', {'status': 'pending-object-chain-and-outer-signature',
          'input_jars': inputs, 'run1_boot_art_sha256': runs[0]['outputs']['boot.art'], 'run2_boot_art_sha256': runs[1]['outputs']['boot.art'],
          'interval': ['0x3e3b8', '0x3e3c0'], 'byte_offsets': next(row['offsets'] for row in comparisons if not row['identical']),
          'elements': {f'run{number}': [hex(value) for value in struct.unpack_from('<QQ', (RELEASE / f'run{number}/boot.art').read_bytes(), 0x3e3b8)] for number in (1, 2)},
          'precedent': 'benchmark/2026-10-03-u14-review/outer-approval-image.json',
          'precedent_sha256': sha(MASTER / 'benchmark/2026-10-03-u14-review/outer-approval-image.json'),
          'not_transferred': True, 'needed': 'fresh frozen oatdump in both new images: PendingFuture.CANCELLED -> backtrace -> long[2] at this field; full log SHA/rc and exact new pair approval'})
    build_source = MASTER / 'knowledge/toolchains/art-r155/BUILD.md'
    text = build_source.read_text()
    match = re.search(r'```t4b-build-json\s*(.*?)```', text, re.S)
    build_record = json.loads(match.group(1))
    build_record['artifacts']['boot_oat_sha256'] = runs[0]['outputs']['boot.oat']
    destination = HERE / 'receipts/U16-BUILD-snapshot.md'
    destination.write_text('# U16 frozen compiler environment binding\n\n'
        + 'This is a derived output binding, not a newly rebuilt compiler. The original frozen compiler BUILD environment comes from '
        + portable(str(build_source)) + ' sha256=' + sha(build_source) + '.\n'
        + 'Both live logs verify dex2oat ae865ddd and driver14b1; hostlibs match the frozen handoff. '
        + 'Only boot_oat_sha256 is rebound to the actual new run1 output; libart and environment are unchanged.\n\n'
        + '```t4b-build-json\n' + json.dumps(build_record, indent=2) + '\n```\n')
    print('INVENTORY86 verified; compiler/tee/session/script all0 both runs; frozen driver6 compares old U15 reference')
    print('PAIR26/27 exact, boot.art3 bytes in [0x3e3b8,0x3e3c0); object-chain/exception pending; run1 selected')


def install(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    subprocess.run(['/bin/cp', '-c', str(source), str(destination)], check=True)


def compose(variant):
    sys.path.insert(0, str(MASTER / 'scripts/lab'))
    import generation_bundle as bundle_tool
    import generation_static_checks as static
    import u7_executor as executor
    base_record = load(REPO / f'benchmark/2026-10-03-u15-on-u14-base/{variant}/composition.json')
    base = expand(base_record['package'])
    if sha(base / 'bundle.json') != base_record['bundle_sha256']:
        raise ValueError('U15 content base drift')
    output = HERE / '.artifacts' / variant
    if output.exists():
        raise ValueError('immutable candidate already exists')
    subprocess.run(['/bin/cp', '-cR', str(base), str(output)], check=True)
    shutil.rmtree(output / 'native')
    native_binding = load(DRAFT / 'native-pair-binding.json')
    native_pair = expand(native_binding['staging'])
    if sha(native_pair / 'package.json') != native_binding['native_manifest_sha256']:
        raise ValueError('approved native staging identity drift')
    for member, digest in load(native_pair / 'package.json')['files'].items():
        if sha(native_pair / member) != digest:
            raise ValueError('native staging byte drift: ' + member)
    subprocess.run(['/bin/cp', '-cR', str(native_pair), str(output / 'native')], check=True)
    manifest = load(output / 'native/package.json')
    bundle = load(output / 'bundle.json')
    old = static.effective(base)
    replacements = {'/system/android/framework/adapter-mainline-stubs.jar': RELEASE / 'jars9/adapter-mainline-stubs.jar',
                    '/system/android/framework/oh-adapter-runtime.jar': DRAFT / '.artifacts/inputs/runtime/oh-adapter-runtime.jar'}
    if sha(replacements['/system/android/framework/oh-adapter-runtime.jar']) != 'f6f5face66a90a16020877cddc5bb6e5bed28063dfabf02fa77064c00c50bb81':
        raise ValueError('runtime JAR is not approved t3 identity')
    replacements.update({'/system/android/framework/arm64/' + name: RELEASE / 'run1' / name for name in image_names()})
    for target, source in replacements.items():
        if not source.is_file():
            raise ValueError('missing selected artifact ' + str(source))
        member = 'payload/' + target.removeprefix('/system/')
        install(source, output / 'native' / member)
        manifest['files'][member] = sha(source)
        manifest['live_hashes'][target] = sha(source)
        overlay = 'boot/arm64/' + Path(target).name if '/arm64/' in target else 'framework/' + Path(target).name
        install(source, output / overlay)
    manifest.update(execution_enabled=False, rollout_ready=False, variant='U16 single disabled content candidate',
                    rollout_blocker='new boot.art exact exception, native/JAR bindings and future U15 promotion pending')
    save(output / 'native/package.json', manifest, public=False)
    checks = output / 'native/native-checks'
    scan = load(checks / 'scan-manifest.json')
    for profile in scan['profiles']:
        profile['identity']['manifest_sha256'] = sha(output / 'native/package.json')
    save(checks / 'scan-manifest.json', scan, public=False)
    gates = load(checks / 'native-gates.json')
    gates['package_manifest_sha256'] = sha(output / 'native/package.json')
    gates['initialization']['manifest']['sha256'] = sha(checks / 'scan-manifest.json')
    if gates['initialization'].get('dex_artifact'):
        row = gates['initialization']['dex_artifact']
        row['sha256'] = manifest['files'][row['path']]
    save(checks / 'native-gates.json', gates, public=False)
    bundle['native']['manifest']['sha256'] = sha(output / 'native/package.json')
    for row in bundle['boot_group']['members'] + [bundle['runtime_jar']]:
        row['sha256'] = sha(output / row['source'])
    for row in bundle['image_gate_reference']['members']:
        prior = old[row['target']]
        install(bundle_tool.member(base, prior), output / row['source'])
        row['sha256'] = prior['sha256']
    bundle['image_gate_reference'].update(kind='unpromoted-U15-content-comparison', baseline_bundle_sha256=sha(base / 'bundle.json'))
    effective_base = executor.prepare(base, base / 'native')['expected']
    for kind, row in bundle['reference'].items():
        prior = bundle_tool.read_fingerprint(base / row['source'])
        destination = output / row['source']
        destination.unlink()
        destination.write_text('\n'.join(sorted(effective_base[target] + '  ' + target for target in prior)) + '\n')
        row['sha256'] = sha(destination)
    receipt = HERE / '.artifacts/receipts/paired-run1.json'
    install(receipt, output / 'receipts/u16-paired-build.json')
    bundle['paired_build_receipt'] = {'source': 'receipts/u16-paired-build.json', 'sha256': sha(receipt)}
    bundle.pop('image_reproduction_approval', None)
    bundle.pop('native_review_approval', None)
    policy = output / 'static-policy-u16-draft.json'
    save(policy, {'schema_version': 1, 'native': {}, 'jars': {}, 'execution_enabled': False,
                 'reason': 'fresh raw review; old U15 allowances not inherited'}, public=False)
    bundle['static_checks'] = {'baseline_bundle_sha256': sha(base / 'bundle.json'),
                               'policy': {'source': policy.name, 'sha256': sha(policy)}}
    bundle.update(execution_enabled=False, rollout_ready=False,
                  transaction_binding={'base': None, 'base_sha256': None, 'promotion_confirmed': False, 'content_comparison_only': True},
                  rollout_blocker='U15 unpromoted; exact pair exception/native/JAR approval and future per-board transaction BASE pending')
    save(output / 'bundle.json', bundle, public=False)
    data, actual_manifest, _ = bundle_tool.validate(output)
    receipt_status = executor.receipt_check(output, data, actual_manifest)['status']
    new = static.effective(output)
    changed = {target: {'old': old[target]['sha256'], 'new': row['sha256']} for target, row in new.items() if old[target]['sha256'] != row['sha256']}
    allowed = set(replacements) | {'/system/android/lib64/liboh_android_runtime.so', '/system/android/lib64/westlake_flutter/libandroid.so'}
    if set(old) != set(new) or set(changed) - allowed:
        raise ValueError('unexpected effective changes')
    for target in replacements:
        if manifest['live_hashes'][target] != new[target]['sha256']:
            raise ValueError('underlay and overlay mismatch')
    save(HERE / variant / 'composition.json', {'package': output, 'content_base': base,
          'content_base_sha256': sha(base / 'bundle.json'), 'bundle_sha256': sha(output / 'bundle.json'),
          'native_manifest_sha256': sha(output / 'native/package.json'), 'native_inputs_sha256': sha(checks / 'native-gates.json'),
          'changed': changed, 'execution_enabled': False, 'rollout_ready': False, 'transaction_base': None,
          'reproduction_approved': False, 'paired_compiler_receipt': receipt_status})
    for name, path in [('bundle.json', output / 'bundle.json'), ('native-manifest.json', output / 'native/package.json'),
                       ('native-inputs.json', checks / 'native-gates.json')]:
        save(HERE / variant / name, load(path))
    print(f'U16 {variant} bundle={sha(output / "bundle.json")} changed={len(changed)} receipt={receipt_status}; disabled/unbound')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--compose', action='store_true')
    args = parser.parse_args()
    audit()
    if args.compose:
        for variant in ('common', '61b'):
            compose(variant)
