"""Identity-bound APK batches using the existing B10 evidence primitives."""

import argparse
import collections
import concurrent.futures
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
B10 = ROOT / 'benchmark/2026-09-29-static-wall-prediction'
sys.path.insert(0, str(B10))
import scan_apps
import scan_jni
from rules85 import elf_info, inspect_method
from rules_u5_feedback import dex_family

sys.path.insert(0, str(ROOT / 'benchmark/2026-10-01-trampoline-scan'))
import rules as trampoline


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def portable(value):
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [portable(item) for item in value]
    if isinstance(value, str):
        workspaces = str(Path(os.environ.get('WORKSPACES', ROOT.parent)))
        return value.replace(workspaces, '$WORKSPACES').replace(str(Path.home()), '$HOME')
    return value


def dependencies():
    paths = [Path(__file__), B10/'scan_apps.py', B10/'scan_jni.py', B10/'registration_sources.py',
             B10/'rules85.py', B10/'rules_u5_feedback.py',
             ROOT/'benchmark/2026-10-01-trampoline-scan/rules.py']
    return {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}


def profile(workspaces):
    candidate_path = ROOT/'benchmark/2026-10-01-u7-prospective/v1/candidate.json'
    candidate = read(candidate_path)
    generation = workspaces/candidate['native_generation']['generation']
    metadata = read(generation/'package.json')
    if digest((generation/'package.json').read_bytes()) != candidate['native_generation']['package_sha256']:
        raise ValueError('native generation manifest drift')
    pins = {**candidate['runtime_files'], **candidate['boot_files']}
    files = {}
    inputs = {}
    for relative, expected in metadata['files'].items():
        if not relative.endswith(('.so', '.jar')):
            continue
        path = generation/relative
        target = '/system/'+relative.removeprefix('payload/')
        if relative.endswith('/oh-adapter-runtime.jar'):
            path = workspaces/'_u6-stage/oh-adapter-runtime.jar'
            expected = candidate['j7b_sha256']
        elif relative.endswith('/adapter-mainline-stubs.jar'):
            path = workspaces/'_hw248-t7d/adapter-mainline-stubs.jar'
            expected = candidate['stubs_sha256']
        elif target in pins and expected != pins[target]:
            route = generation/'payload/route'/Path(relative).name
            if not route.is_file() or digest(route.read_bytes()) != pins[target]:
                raise ValueError('canonical runtime source unresolved: '+relative)
            path = route
            expected = pins[target]
        actual = digest(path.read_bytes())
        if actual != expected or (target in pins and actual != pins[target]):
            raise ValueError('runtime file drift: '+relative)
        files[relative] = actual
        inputs[relative] = portable(dict(path=str(path), sha256=actual, bytes=path.stat().st_size))
    with tempfile.TemporaryDirectory(prefix='corpus-u7-jni-') as directory:
        package = Path(directory)
        for relative, item in inputs.items():
            physical = Path(item['path'].replace('$WORKSPACES', str(workspaces)).replace('$HOME', str(Path.home())))
            destination = package/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(physical)
        (package/'package.json').write_text(json.dumps(dict(generation='u7-t7d-j7b-n4order', files=files)))
        jni = scan_jni.scan(package, overlay=None)
        methods = {item['id']: dict(status=item['status'], reason=item['reason'],
                                   evidence=portable(item['evidence'])) for item in jni['methods']}
        for item in methods.values():
            item['evidence'] = json.loads(json.dumps(item['evidence']).replace(str(package), 'U7_SCAN_PROFILE'))
    exports = set()
    providers = collections.defaultdict(list)
    for relative, item in inputs.items():
        if not relative.endswith('.so'):
            continue
        path = Path(item['path'].replace('$WORKSPACES', str(workspaces)).replace('$HOME', str(Path.home())))
        parsed = elf_info(path.read_bytes())
        for symbol in parsed['exports']:
            name = symbol['name'] if isinstance(symbol, dict) else symbol
            exports.add(name)
            providers[name].append(relative)
    return dict(name='U7:T7d+J7b+N4-order', candidate_sha256=digest(candidate_path.read_bytes()),
                native_manifest_sha256=digest((generation/'package.json').read_bytes()),
                inputs=inputs, methods=methods, jni_counts=jni['counts'],
                source_inputs=portable(jni['source_inputs']),
                source_attribution_unknown=portable(jni['source_attribution_unknown']),
                exports=sorted(exports), providers=dict(providers), scanner_dependencies=dependencies(),
                semantics='Presence and attributed compiled JNI coverage, not registration execution or namespace resolution')


def check_identity(row, payload, fingerprints):
    if digest(payload) != row['sha256'] or len(payload) != row['bytes']:
        raise ValueError('APK SHA/size mismatch: '+row['package'])
    if set(fingerprints) != set(row['signer_sha256']):
        raise ValueError('APK signer mismatch: '+row['package'])


def command(argv):
    result = subprocess.run([str(value) for value in argv], capture_output=True, text=True, errors='replace')
    if result.returncode:
        raise ValueError('tool failed: '+Path(str(argv[0])).name+' exit '+str(result.returncode))
    return result.stdout


def signature(apk, apksigner):
    text = command([apksigner, 'verify', '--verbose', '--print-certs', apk])
    fingerprints = re.findall(r'^(?:Signer #\d+|V[\d.]+ Signer):? certificate SHA-256 digest: ([0-9a-fA-F]+)$', text, re.MULTILINE)
    if not fingerprints:
        raise ValueError('No verified signer fingerprints')
    return dict(fingerprints=[value.lower() for value in fingerprints], output_sha256=digest(text.encode()),
                verification_lines=[line for line in text.splitlines() if line.startswith('Verified using')])


def features(classes, libraries):
    names = set(classes)
    patterns = {'compose':'Landroidx/compose/', 'webview':'Landroid/webkit/WebView;',
                'gl':'Landroid/opengl/', 'androidx-view':'Landroidx/appcompat/',
                'kotlin':'Lkotlin/', 'flutter':'Lio/flutter/', 'unity':'Lcom/unity3d/'}
    result = {name: sorted(owner for owner in names if owner.startswith(prefix))[:5] for name, prefix in patterns.items()}
    result['native_members'] = len(libraries)
    result['basis'] = 'DEX class definitions; API invocations are separately retained. Obfuscation and dynamic modules remain unknown.'
    return result


def native_declarations(text, member):
    owner = name = signature = None
    result = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.search(r"Class descriptor\s+: 'L(.+);'", line)
        if match:
            owner = match[1]
        match = re.search(r"name\s+: '([^']+)'", line)
        if match:
            name = match[1]
        match = re.search(r"type\s+: '(\([^']+)'", line)
        if match:
            signature = match[1]
        if re.search(r'access\s+:.*\bNATIVE\b', line):
            result.append(dict(id=owner+'.'+name+signature, owner=owner, name=name,
                               signature=signature, dex=member, line=number))
    return result


def application_class(text):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith('E: application '):
            continue
        for following in lines[index+1:]:
            if following.lstrip().startswith('E: '):
                break
            match = re.search(r'A: (?:[^\s=]*:)?name(?:\([^)]*\))?="([^"]+)"', following)
            if match:
                return match[1]
        break
    return None


def scan_apk(row, args, runtime):
    apk = args.apks/Path(row['apk_url']).name
    if not apk.is_file():
        return dict(package=row['package'], key=row['package'], status='pending', reason='APK absent')
    payload = apk.read_bytes()
    if digest(payload) != row['sha256'] or len(payload) != row['bytes']:
        return dict(package=row['package'], key=row['package'], status='rejected', reason='APK SHA/size mismatch')
    try:
        signer = signature(apk, args.apksigner)
        check_identity(row, payload, signer['fingerprints'])
        manifest_text = command([args.aapt2, 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml'])
        manifest = trampoline.manifest(manifest_text)
        if manifest['package'] != row['package']:
            raise ValueError('manifest package mismatch')
        badging = command([args.aapt2, 'dump', 'badging', apk])
        manifest['badging'] = [line for line in badging.splitlines() if line.startswith(('package:', 'sdkVersion:', 'targetSdkVersion:', 'launchable-activity:', 'uses-split:', 'native-code:'))]
        manifest['application_class'] = application_class(manifest_text)
        manifest['provider_classes'] = []
        lines = manifest_text.splitlines()
        for index, line in enumerate(lines):
            if line.lstrip().startswith('E: provider'):
                indentation = len(line)-len(line.lstrip())
                for following in lines[index+1:]:
                    if len(following)-len(following.lstrip()) <= indentation:
                        break
                    match = re.search(r'A: (?:[^\s=]*:)?name(?:\([^)]*\))?="([^"]+)"', following)
                    if match:
                        manifest['provider_classes'].append(match[1])
                        break
        classes, methods, dexes, libraries = {}, {}, [], []
        services, native_calls, risks, profile_calls, declarations = [], [], [], [], []
        with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix='corpus-apk-') as directory:
            for member in sorted(archive.namelist()):
                if member.startswith('lib/') and member.endswith('.so'):
                    data = archive.read(member)
                    parsed = elf_info(data) if member.startswith('lib/arm64-v8a/') else dict(header='non-AArch64-member', imports=[], exports=[], needed=[])
                    libraries.append(dict(member=member, sha256=digest(data), bytes=len(data), **parsed))
                if not re.fullmatch(r'classes\d*\.dex', member):
                    continue
                data = archive.read(member)
                dexes.append(dict(member=member, sha256=digest(data), bytes=len(data)))
                path = Path(directory)/member
                path.write_bytes(data)
                text = command([args.dexdump, '-d', path])
                declarations.extend(native_declarations(text, member))
                dex_classes, dex_methods = trampoline.parse_dex(text.splitlines(), member, digest(data))
                classes.update(dex_classes)
                for identifier, method in dex_methods.items():
                    if identifier in methods:
                        raise ValueError('Duplicate DEX method definition: '+identifier)
                    methods[identifier] = method
                current, instructions = '', []
                def flush():
                    calls, natives, unused = scan_apps.method_scan(current, instructions, member, 0, runtime['methods'])
                    services.extend(calls)
                    native_calls.extend(natives)
                    risks.extend(inspect_method(current, member, instructions))
                    for offset, number, instruction in instructions:
                        family = dex_family(instruction)
                        if family:
                            risks.append(dict(family=family, method=current, dex=member, line=number, offset=offset, instruction=instruction))
                for number, line in enumerate(text.splitlines(), 1):
                    header = scan_apps.HEADER.search(line)
                    if header:
                        flush()
                        current, instructions = header[1], []
                    instruction = scan_apps.INSN.search(line)
                    if instruction:
                        instructions.append((instruction[1], number, instruction[2]))
                flush()
                for method in dex_methods.values():
                    for call in method['calls']:
                        owner = call['owner']
                        if owner.startswith(('Landroidx/compose/', 'Landroid/webkit/', 'Landroid/opengl/', 'Lio/flutter/', 'Lcom/unity3d/')):
                            profile_calls.append(dict(dex=member, method=method['id'], **call))
        if not dexes or not manifest['launchers']:
            raise ValueError('Missing DEX or LAUNCHER activity')
        startup_owners = {trampoline.qualified(row['package'], entry['target']).replace('.', '/') for entry in manifest['launchers']}
        startup_owners.update(trampoline.qualified(row['package'], name).replace('.', '/') for name in [manifest['application_class'], *manifest['provider_classes']] if name)
        for owner in list(startup_owners):
            startup_owners.update(ancestor.strip('L;') for ancestor in trampoline.hierarchy('L'+owner+';', classes))
        roots = [identifier for identifier, method in methods.items() if method['owner'].strip('L;') in startup_owners and method['name'] in {'<init>', '<clinit>', 'attachBaseContext', 'onCreate', 'onResume', 'onStart'}]
        reached, frontier = set(roots), set(roots)
        for depth in range(3):
            frontier = {call['target'] for identifier in frontier for call in methods[identifier]['calls'] if call['target'] in methods}-reached
            reached.update(frontier)
        startup_calls = [dict(dex=methods[identifier]['dex'], method=identifier, **call) for identifier in sorted(reached) for call in methods[identifier]['calls']]
        coverage = []
        for call in native_calls:
            coverage.append(dict(**call, coverage=runtime['methods'][call['id']]['status']))
        app_native = []
        for declaration in declarations:
            short = 'Java_'+scan_jni.jni_escape(declaration['owner'])+'_'+scan_jni.jni_escape(declaration['name'])
            long = short+'__'+scan_jni.jni_escape(declaration['signature'].split(')')[0][1:])
            matches = [dict(member=library['member'], symbol=symbol) for library in libraries
                       if library['member'].startswith('lib/arm64-v8a/') for symbol in library['exports']
                       if symbol in {short, long}]
            app_native.append(dict(**declaration, coverage='exported' if matches else 'unknown-dynamic-registration', evidence=matches))
        return dict(key=row['package'], package=row['package'], status='scanned', sha256=row['sha256'],
                    bytes=len(payload), apk_member=apk.name, signer=signer, manifest=manifest,
                    manifest_xml_sha256=digest(manifest_text.encode()), dex=dexes,
                    libraries=libraries, features=features(classes, libraries), framework_calls=profile_calls,
                    services=services, jni_calls=coverage, app_native_candidates=app_native,
                    risks=risks, startup=dict(roots=sorted(roots), reached=sorted(reached), depth=3,
                                             calls=startup_calls, dispatch='Exact in-APK targets only; inherited virtual/reflective/native dispatch remains unknown'),
                    scanner_dependencies=dependencies())
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        return dict(key=row['package'], package=row['package'], status='rejected', sha256=row['sha256'], reason=portable(str(error)))


def initialize_worker(args, runtime):
    global WORKER_ARGS, WORKER_RUNTIME
    WORKER_ARGS, WORKER_RUNTIME = args, runtime


def collect_worker(row):
    result = scan_apk(row, WORKER_ARGS, WORKER_RUNTIME)
    print(row['package'], result['status'], flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces', type=Path, default=Path(os.environ.get('WORKSPACES', ROOT.parent)))
    parser.add_argument('--apks', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--dexdump', type=Path, default=Path.home()/'Library/Android/sdk/build-tools/37.0.0/dexdump')
    parser.add_argument('--aapt2', type=Path, default=Path.home()/'Library/Android/sdk/build-tools/37.0.0/aapt2')
    parser.add_argument('--apksigner', type=Path, default=Path.home()/'Library/Android/sdk/build-tools/37.0.0/apksigner')
    args = parser.parse_args()
    args.apks = args.apks or args.workspaces/'westlake-inputs/corpus-v2/apks'
    args.output.mkdir(parents=True, exist_ok=True)
    runtime = read(args.profile) if args.profile else profile(args.workspaces)
    if args.profile:
        current = dependencies()
        for path, expected in runtime['scanner_dependencies'].items():
            if path != str(Path(__file__).relative_to(ROOT)) and digest((ROOT/path).read_bytes()) != expected:
                raise ValueError('cached runtime classifier dependency changed: '+path)
        for item in runtime['inputs'].values():
            physical = Path(item['path'].replace('$WORKSPACES', str(args.workspaces)).replace('$HOME', str(Path.home())))
            if digest(physical.read_bytes()) != item['sha256']:
                raise ValueError('cached runtime input drift')
        runtime['scanner_dependencies'] = {**runtime['scanner_dependencies'], **current}
    (args.output/'runtime-profile.json').write_text(json.dumps(portable(runtime), sort_keys=True)+'\n')
    selection_path = HERE.parent/'results.json'
    selection = read(selection_path)
    tools = {name: digest(getattr(args, name).read_bytes()) for name in ['dexdump', 'aapt2', 'apksigner']}
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs, initializer=initialize_worker,
                                                initargs=(args, runtime)) as executor:
        apps = list(executor.map(collect_worker, selection['rows']))
    document = dict(schema_version=1, selection_sha256=digest(selection_path.read_bytes()),
                    runtime_profile_sha256=digest(json.dumps(portable(runtime), sort_keys=True).encode()+b'\n'),
                    tools=tools, scanner_dependencies=dependencies(), apps=apps,
                    counts=dict(collections.Counter(app['status'] for app in apps)),
                    input_root=portable(str(args.apks)), observed_device_results=False)
    (args.output/'facts.json').write_text(json.dumps(portable(document), sort_keys=True)+'\n')
    print(document['counts'], flush=True)


if __name__ == '__main__':
    main()
