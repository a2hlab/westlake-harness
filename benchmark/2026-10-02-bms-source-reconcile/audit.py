#!/usr/bin/env python3
import difflib
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get('WORKSPACES', REPO.parent))
MASTER = WS / 'westlake-harness'
DEPLOY = WS / 'westlake-harness-bms-deploy'
BASE = WS / 'westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3'
N10 = MASTER / 'benchmark/2026-10-01-n10b-child/smoke-markers'
N2 = DEPLOY / 'benchmark/2026-09-30-n2-native'
N3 = DEPLOY / 'benchmark/2026-09-30-n3-native'
INSTALLER = DEPLOY / 'bms/src/.work/installer-background-launcher/source-archive'
STOCK = 'bms/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/'
RUNTIME = 'bms/src/adapter/framework/android-runtime/src/'
ANL = 'bms/src/adapter/framework/app-native-loader/'
PM = 'bms/src/adapter/framework/package-manager/jni/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def portable(value):
    text = str(value)
    for root, token in [(REPO, '$REPO'), (WS, '$WORKSPACES')]:
        prefix = str(root)
        if text == prefix or text.startswith(prefix + '/'):
            return token + text[len(prefix):]
    return text


def public(text):
    return text.replace(str(WS) + '/', '$WORKSPACES/').replace(str(Path.home()) + '/', '$HOME/')


def save(name, value):
    (HERE / name).write_text(public(json.dumps(value, indent=2, ensure_ascii=False)) + '\n')


def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args])


def source_info(path):
    result = {'path': portable(path), 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
    for tree in [MASTER, DEPLOY, REPO, WS / 'westlake-harness-b4']:
        if path.is_relative_to(tree):
            result['commit'] = git(tree, 'log', '-1', '--format=%H', '--', str(path.relative_to(tree))).decode().strip() or None
            break
    return result


def command(name, argv):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    raw = HERE / '.artifacts/raw' / name
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(result.stdout)
    (HERE / 'evidence' / name).write_text(public(result.stdout.decode(errors='replace')))
    return {'command': [portable(value) for value in argv], 'exit_code': result.returncode,
        'evidence': 'evidence/' + name, 'raw_sha256': sha(result.stdout),
        'raw_persistent_path': '$WORKSPACES/westlake-harness-bms/' + str(raw.relative_to(REPO))}


def nm(path):
    text = subprocess.check_output(['llvm-nm', '--defined-only', str(path)], text=True)
    return {parts[2] for line in text.splitlines() if len(parts := line.split()) == 3
        and parts[1] in ['T', 't', 'W', 'w']}


def choose(path):
    name = Path(path).name
    if path.startswith(RUNTIME):
        source = N10 / 'src/AndroidRuntime.cpp' if name == 'AndroidRuntime.cpp' else N2 / 'src' / name
        return 'LAND', source, 'N10b AndroidRuntime override; other TUs are exact authenticated N2 cached objects, not current live source.'
    if path == ANL + 'src/app_native_loader.c':
        return 'LAND', N3 / 'flutter/app_native_loader.c', 'N3 result eebd62f2 matches deployed bytes; neither lane-head loader is the compiled source.'
    if path == STOCK + 'src/westlake_stock_host_main.c':
        return 'LAND', REPO / 'benchmark/2026-10-01-u10-native-shims/host-r3/candidate-stock-host.c', 'Accepted r3 source SHA507bf160 and existing artifact65cc3535; do not install the historical branch host.'
    if path.startswith(PM):
        return 'LAND', INSTALLER / 'adapter/framework/package-manager/jni' / name, 'Background-launch archive matches branch source; expected-per-board pins installer7048 on all three boards.'
    if name == 'native_loader.cpp':
        return 'KEEP-MASTER', WS / 'westlake-inputs/generations/u10.1-policy-repro/native-loader-u10.1/src/native_loader.cpp', 'Exact policy0718 uses cdd53c08 already on master; b4 implicit LD_LIBRARY_PATH fallback is not its source.'
    if name == 'hwui_oh_abi_patch.cpp':
        return 'UNKNOWN-NO-LAND', None, 'Deployed hwui be592 provenance is blocked; neither retry variant has a source/object receipt for these bytes.'
    if '/tests/host/' in path:
        return 'NON-PRODUCTION-NO-LAND', None, 'Host test or mock header is not compiled into the deployed loader. Neither test version can be selected from ELF provenance; N3 source requires a separately reviewed test adaptation.'
    if name == 'child_main_after_stock.cpp':
        return 'UNKNOWN-NO-LAND', None, 'Deployed childdc73 N10b receipt compiles sealed_child_provider_loader.c, not this legacy C++ ActivityThread entry. U9 input hash alone does not bind this source to any current executing provider owner; source selection remains unproved.'
    if path.startswith(STOCK):
        return 'HISTORICAL-NO-LAND', None, 'Branch stock generation metadata/scripts describe the historical baseline, not the r3 override/object recipe; do not overwrite current source-closure metadata as if complete.'
    if 'compile_oh_android_runtime' in name:
        return 'SUPERSEDED-NO-LAND', None, 'Actual N10b uses its build-runtime.py and frozen N4 recipe with cached objects and explicit overrides, not this current canonical script.'
    if name == 'compile_sigchain_muslcompat.sh':
        return 'UNKNOWN-NO-LAND', None, 'Android and route sigchain have different deployed SHA42062f49/6d5d5538. No exact build-source receipt binds this branch script to both; no newest-script inference.'
    if path.endswith('r45-dynamic-roots/SHA256SUMS'):
        return 'STALE-NO-LAND', None, 'Historical roots7e1fd94e/22df3988 differ from effective ac59dec0/84695d62; do not overwrite a frozen hash registry with historical identities.'
    raise ValueError(path)


def main():
    (HERE / 'evidence').mkdir(exist_ok=True)
    module_path = MASTER / 'scripts/lab/unlanded.py'
    spec = importlib.util.spec_from_file_location('unlanded', module_path)
    unlanded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unlanded)
    expected_path = BASE / 'bundle/expected-per-board.json'
    expected = json.loads(expected_path.read_text())
    save('evidence/expected-per-board.json', expected)
    rows = []
    for lane, count in [('westlake-harness-bms-deploy', 22), ('westlake-harness-b4', 4)]:
        tree = WS / lane
        inventory = [path for path, status in unlanded.branch_residue(tree, MASTER)
            if path.startswith('bms/src/') and status == 'master-still-at-merge-base']
        assert len(inventory) == count, (lane, len(inventory))
        for path in inventory:
            branch_bytes = git(tree, 'show', 'HEAD:' + path)
            decision, selected, reason = choose(path)
            rows.append({'lane': lane, 'lane_head': git(tree, 'rev-parse', 'HEAD').decode().strip(),
                'path': path, 'branch_sha256': sha(branch_bytes),
                'branch_commit': git(tree, 'log', '-1', '--format=%H', '--', path).decode().strip(),
                'worktree_sha256': sha((tree / path).read_bytes()),
                'master_sha256': sha((MASTER / path).read_bytes()),
                'decision': decision, 'selected': source_info(selected) if selected else None,
                'reason': reason, 'evidence': []})
    for index, row in enumerate(rows, 1):
        tree = WS / row['lane']
        branch = git(tree, 'show', 'HEAD:' + row['path']).decode()
        previous = (MASTER / row['path']).read_text()
        name = 'evidence/residue-' + str(index).zfill(2) + '.patch'
        (HERE / name).write_text(public(''.join(difflib.unified_diff(
            previous.splitlines(keepends=True), branch.splitlines(keepends=True),
            fromfile='master/' + row['path'], tofile=row['lane'] + '/' + row['path']))))
        row['branch_difference_evidence'] = name
    runtime_receipt_path = N10 / 'runtime-build-receipt.json'
    runtime_receipt = json.loads(runtime_receipt_path.read_text())
    out = WS / runtime_receipt['out_directory']
    runtime_deployed = BASE / 'bundle/native/payload/android/lib64/liboh_android_runtime.so'
    assert runtime_receipt['variants']['candidate']['sha256'] == sha(runtime_deployed.read_bytes())
    objects = []
    linked = nm(runtime_deployed)
    for name in ['AndroidRuntime', 'android_graphics_compat_shim', 'android_view_SurfaceControl', 'android_media_AudioSystemCapabilities']:
        hashes = {}
        for variant in ['candidate', 'repeat']:
            path = out / variant / 'runtime-objects' / (name + '.o')
            hashes[variant] = sha(path.read_bytes())
            assert hashes[variant] == runtime_receipt['variants'][variant]['objects'][name + '.o']
        source = N10 / 'src/AndroidRuntime.cpp' if name == 'AndroidRuntime' else N2 / 'src' / (name + '.cpp')
        symbols = sorted(nm(out / 'candidate/runtime-objects' / (name + '.o')))
        original = DEPLOY / 'bms/src/.work/n2-native/runtime-objects' / (name + '.o')
        objects.append({'name': name, 'hashes': hashes, 'source': source_info(source),
            'n2_object_sha256': sha(original.read_bytes()), 'candidate_defined_functions': symbols,
            'linked_functions': [symbol for symbol in symbols if symbol in linked],
            'source_binding': 'N10b explicit override' if name == 'AndroidRuntime' else 'N2 source-sha256 + restore_cache forced compile + same .o through N4 and N10b'})
    save('evidence/runtime-object-selection.json', {'receipt': source_info(runtime_receipt_path), 'objects': objects})
    source_hashes = json.loads((N2 / 'source-sha256.json').read_text())
    for row in objects[1:]:
        assert row['source']['sha256'] == source_hashes['src/' + row['name'] + '.cpp']
        assert row['n2_object_sha256'] == row['hashes']['candidate']
    n3_hashes = json.loads((N3 / 'source-sha256.json').read_text())
    assert sha((N3 / 'flutter/app_native_loader.c').read_bytes()) == n3_hashes['flutter/app_native_loader.c']
    host_receipt_path = REPO / 'benchmark/2026-10-01-u10-native-shims/evidence/host-r3/build-receipt.json'
    host_receipt = json.loads(host_receipt_path.read_text())
    host_source = REPO / 'benchmark/2026-10-01-u10-native-shims/host-r3/candidate-stock-host.c'
    assert sha(host_source.read_bytes()) == host_receipt['source_sha256']
    assert sha((REPO / 'benchmark/2026-10-01-u10-native-shims/host-r3/resident-compat.h').read_bytes()) == host_receipt['resident_header_sha256']
    assert sha((N3 / 'flutter/flutter_domain.inc').read_bytes()) == n3_hashes['flutter/flutter_domain.inc']
    assert sha((N2 / 'src/surface_session_identity.h').read_bytes()) == source_hashes['src/surface_session_identity.h']
    binaries = {
        'runtime': (out / 'candidate/runtime-out/liboh_android_runtime.so', runtime_deployed),
        'host': (REPO / 'benchmark/2026-10-01-u10-native-shims/.artifacts/host-r3/appspawn-x-candidate', BASE / 'bundle/native/payload/runtime/appspawn-x'),
        'anl': (DEPLOY / 'bms/src/.work/n3-native/flutter/libapp_native_loader.so', BASE / 'bundle/native/payload/android/lib64/libapp_native_loader.so'),
        'policy': (WS / 'westlake-inputs/generations/u10.1-policy-repro/u10.1-build/libnativeloader.so', BASE / 'bundle/native/payload/android/lib64/libnativeloader.so'),
        'installer': (INSTALLER / 'adapter/out/adapter/libapk_installer.so', INSTALLER / 'package/libapk_installer.so')}
    binary_rows = {}
    for role, (archive, deployed) in binaries.items():
        assert sha(archive.read_bytes()) == sha(deployed.read_bytes()), role
        binary_rows[role] = {'archive': source_info(archive), 'deployed': source_info(deployed),
            'comparison': command(role + '-strings.txt', ['python3', str(MASTER / 'scripts/lab/deployed_strings_diff.py'), str(archive), '--deployed', str(deployed)])}
        assert binary_rows[role]['comparison']['exit_code'] == 0
    assert host_receipt['artifacts']['candidate'] == binary_rows['host']['deployed']['sha256']
    identity = command('artifact-identity.txt', ['python3', str(MASTER / 'scripts/lab/artifact_identity.py')]
        + [str(pair[1]) for pair in binaries.values()] + ['--expected', str(expected_path)])
    assert identity['exit_code'] == 0
    pins = []
    def walk(value, trail):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, trail + [key])
        elif isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value):
            if trail[-1].endswith(('libapk_installer.so', 'libhwui.so', 'libsigchain.so')):
                pins.append({'trail': trail, 'sha256': value})
    walk(expected, [])
    installer_pins = [pin for pin in pins if pin['trail'][-1].endswith('libapk_installer.so')]
    assert len(installer_pins) == 6
    assert {pin['sha256'] for pin in installer_pins} == {binary_rows['installer']['deployed']['sha256']}
    save('evidence/special-artifact-pins.json', pins)
    for name in ['liboh_android_runtime.so', 'libapp_native_loader.so', 'libnativeloader.so', 'libhwui.so', 'libsigchain.so', 'libapk_installer.so', 'appspawn-x']:
        command('whois-' + name + '.txt', ['python3', str(MASTER / 'scripts/lab/deployed_whois.py'), name, '--generation', str(BASE)])
    command('runtime-symbols.txt', ['llvm-nm', '--defined-only', '--demangle', str(runtime_deployed)])
    command('installer-symbols.txt', ['llvm-nm', '--dynamic', '--defined-only', '--demangle', str(binaries['installer'][1])])
    command('anl-dwarf-lines.txt', ['llvm-dwarfdump', '--debug-line', str(DEPLOY / 'bms/src/.work/n3-native/flutter/anl.o')])
    references = [N10 / 'build-runtime.py', runtime_receipt_path, N10 / 'child-build-receipt.json', N2 / 'restore_cache.py', N2 / 'runtime-recipe.sh', N2 / 'source-sha256.json', N3 / 'results.json', N3 / 'source-sha256.json', N3 / 'build-flutter.sh', host_receipt_path, INSTALLER / 'evidence/elf-summary.json', INSTALLER / 'evidence/build-installer.sh', INSTALLER / 'evidence/build-installer.log', WS / 'westlake-inputs/generations/u10.1-policy-repro/README.md']
    save('evidence/references.json', [source_info(path) for path in references])
    excerpt = []
    for path in references:
        for number, text in enumerate(path.read_text(errors='replace').splitlines(), 1):
            if any(token in text for token in ['AndroidRuntime.cpp', 'android_graphics_compat_shim', 'android_view_SurfaceControl', 'android_media_AudioSystemCapabilities', 'app_native_loader.c', 'eebd62f2', 'ac59dec0', 'source_sha256', '65cc3535', '7048c7c5', 'native_loader.cpp', 'sourcedir', 'compile_package_manager', 'clang', '-c ', 'nt "$s"', 'surface_session_identity.h', 'flutter_domain.inc', 'resident_header_sha256', 'apk_network_permissions.h']):
                excerpt.append({'file': portable(path), 'line': number, 'text': public(text)})
    save('evidence/recipe-excerpts.json', excerpt)
    selected = {row['path']: Path(row['selected']['path'].replace('$WORKSPACES', str(WS)).replace('$REPO', str(REPO)))
        for row in rows if row['decision'] == 'LAND'}
    selected.update({RUNTIME + 'surface_session_identity.h': N2 / 'src/surface_session_identity.h',
        ANL + 'src/flutter_domain.inc': N3 / 'flutter/flutter_domain.inc',
        STOCK + 'src/resident-compat.h': REPO / 'benchmark/2026-10-01-u10-native-shims/host-r3/resident-compat.h',
        PM + 'apk_network_permissions.h': INSTALLER / 'adapter/framework/package-manager/jni/apk_network_permissions.h'})
    export = []
    patches = []
    for target, source in sorted(selected.items()):
        data = source.read_bytes()
        assert not re.search(rb'/Users/|/home/[^/]+/', data), target
        snapshot = HERE / 'sources' / target
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(data)
        previous = MASTER / target
        old = previous.read_text().splitlines(keepends=True) if previous.is_file() else []
        patches += list(difflib.unified_diff(old, data.decode().splitlines(keepends=True),
            fromfile='a/' + target if previous.is_file() else '/dev/null', tofile='b/' + target))
        role = 'runtime' if target.startswith(RUNTIME) else 'anl' if target.startswith(ANL) else 'host' if target.startswith(STOCK) else 'installer'
        basis = {'runtime': ['evidence/runtime-object-selection.json', 'evidence/recipe-excerpts.json'],
            'anl': ['evidence/recipe-excerpts.json', 'evidence/anl-dwarf-lines.txt', 'evidence/anl-strings.txt'],
            'host': ['evidence/references.json', 'evidence/recipe-excerpts.json', 'evidence/host-strings.txt'],
            'installer': ['evidence/special-artifact-pins.json', 'evidence/references.json', 'evidence/installer-strings.txt']}[role]
        device_paths = {'runtime': ['/system/android/lib64/liboh_android_runtime.so'],
            'anl': ['/system/android/lib64/libapp_native_loader.so', '/system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/libapp_native_loader.so'],
            'host': ['/system/bin/appspawn-x'],
            'installer': ['/system/lib64/libapk_installer.so', '/system/lib64/platformsdk/libapk_installer.so']}[role]
        export.append({'target': target, 'snapshot': str(snapshot.relative_to(HERE)),
            'source': source_info(source), 'sha256': sha(data),
            'deployed_role': role, 'deployed_sha256': binary_rows[role]['deployed']['sha256'],
            'deployed_device_paths': device_paths, 'deployed_local_copy': binary_rows[role]['deployed']['path'],
            'basis': basis,
            'master_preimage_sha256': sha(previous.read_bytes()) if previous.is_file() else None})
    (HERE / 'selected-sources.patch').write_text(''.join(patches))
    (HERE / 'source-landing-paths.txt').write_text(''.join(
        '# deployed=' + row['deployed_sha256'] + ' ' + ':'.join(row['deployed_device_paths']) + '\n'
        + '# source=' + row['sha256'] + ' snapshot=' + row['snapshot'] + '\n'
        + '# basis=' + ','.join(row['basis']) + '\n' + row['target'] + '\n'
        for row in export))
    save('source-to-deployed.json', export)
    patch_check = command('source-patch-check.txt', ['git', '-C', str(MASTER), 'apply', '--check', str(HERE / 'selected-sources.patch')])
    assert patch_check['exit_code'] == 0
    for row in rows:
        row['evidence'] = [row['branch_difference_evidence'], 'evidence/references.json', 'evidence/recipe-excerpts.json']
        if row['path'].startswith(RUNTIME):
            row['evidence'].append('evidence/runtime-object-selection.json')
        if row['path'].startswith(PM):
            row['evidence'].append('evidence/special-artifact-pins.json')
    save('results.json', {'schema': 1, 'execution_enabled': False, 'compiler_runs': 0, 'device_operations': 0,
        'master_commit': git(MASTER, 'rev-parse', 'HEAD').decode().strip(),
        'inventory_tool': source_info(module_path), 'expected_per_board': source_info(expected_path),
        'artifact_identity': identity,
        'rows': rows, 'binary_checks': binary_rows, 'selected_sources': export,
        'unknown_rows': [row['path'] for row in rows if row['decision'] == 'UNKNOWN-NO-LAND'],
        'runtime_object_evidence': 'evidence/runtime-object-selection.json',
        'source_patch_sha256': sha((HERE / 'selected-sources.patch').read_bytes()),
        'source_patch_check': patch_check,
        'source_landing_requires_outer_review': True})
    table = ['| Lane | Path | Decision | Selected SHA | Reason |', '|---|---|---|---|---|']
    table += ['| ' + ' | '.join([row['lane'].removeprefix('westlake-harness-'), row['path'], row['decision'],
        row['selected']['sha256'][:12] if row['selected'] else 'none', row['reason']]) + ' |' for row in rows]
    (HERE / 'DECISIONS.md').write_text('\n'.join(table) + '\n')


if __name__ == '__main__':
    main()
