"""Exclude package-only binaries before binding APK calls to deployed U7 JNI."""

import argparse
import collections
import json
from pathlib import Path
import tempfile

import scan


def bind(document, previous, workspaces):
    expected_path = scan.ROOT/'benchmark/2026-10-01-u7-prospective/v1/expected-run.json'
    expected = scan.read(expected_path)
    by_sha = collections.defaultdict(list)
    for group in ['runtime_files', 'boot_files']:
        for path, sha in expected[group].items():
            by_sha[sha].append(path)
    selected = {name: {**item, 'deployed_paths': sorted(by_sha[item['sha256']])}
                for name, item in previous['inputs'].items() if item['sha256'] in by_sha}
    excluded = {name: item for name, item in previous['inputs'].items() if item['sha256'] not in by_sha}
    with tempfile.TemporaryDirectory(prefix='corpus-deployed-jni-') as directory:
        package = Path(directory)
        files, exports, providers = {}, set(), collections.defaultdict(list)
        for relative, item in selected.items():
            physical = Path(item['path'].replace('$WORKSPACES', str(workspaces)).replace('$HOME', str(Path.home())))
            payload = physical.read_bytes()
            if scan.digest(payload) != item['sha256']:
                raise ValueError('deployed profile input changed: '+relative)
            destination = package/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(physical)
            files[relative] = item['sha256']
            if relative.endswith('.so'):
                parsed = scan.elf_info(payload)
                for symbol in parsed['exports']:
                    exports.add(symbol)
                    providers[symbol].append(relative)
        (package/'package.json').write_text(json.dumps(dict(generation='U7-deployed-hash-domain', files=files)))
        jni = scan.scan_jni.scan(package, overlay=None)
        methods = {item['id']: dict(status=item['status'], reason=item['reason'],
                                   evidence=scan.portable(item['evidence'])) for item in jni['methods']}
        for item in methods.values():
            item['evidence'] = json.loads(json.dumps(item['evidence']).replace(str(package), 'U7_DEPLOYED_PROFILE'))
    dependencies = {**document['scanner_dependencies'], **scan.dependencies(), str(Path(__file__).relative_to(scan.ROOT)): scan.digest(Path(__file__).read_bytes())}
    runtime = dict(name='U7:T7d+J7b+N4-order:deployed-hashes-only',
                   candidate_sha256=previous['candidate_sha256'], native_manifest_sha256=previous['native_manifest_sha256'],
                   expected_run_sha256=scan.digest(expected_path.read_bytes()), inputs=selected,
                   excluded_package_only_inputs=excluded, methods=methods, jni_counts=jni['counts'],
                   source_inputs=scan.portable(jni['source_inputs']),
                   source_attribution_unknown=scan.portable(jni['source_attribution_unknown']),
                   exports=sorted(exports), providers=dict(providers), scanner_dependencies=dependencies,
                   semantics='Only bytes matching a deployed U7 path; compiled coverage still does not prove classloader/namespace/registration execution')
    document['collection_profile_sha256'] = document['runtime_profile_sha256']
    document['runtime_profile_sha256'] = scan.digest(json.dumps(runtime, sort_keys=True).encode()+b'\n')
    document['scanner_dependencies'] = dependencies
    document['deployment_binding'] = dict(mode='post-collection-deployed-identity-filter-and-fresh-JNI-attribution',
                                           excluded_inputs=len(excluded), expected_run_sha256=runtime['expected_run_sha256'])
    for app in document['apps']:
        if app['status'] != 'scanned':
            continue
        for call in app['jni_calls']:
            call['coverage'] = methods.get(call['id'], {}).get('status', 'unknown-not-declared-in-profile')
        app['scanner_dependencies'] = dependencies
    return document, runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workspaces', type=Path, default=scan.ROOT.parent)
    args = parser.parse_args()
    facts, runtime = bind(scan.read(args.facts), scan.read(args.profile), args.workspaces)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'facts.json').write_text(json.dumps(facts, sort_keys=True)+'\n')
    (args.output/'runtime-profile.json').write_text(json.dumps(runtime, sort_keys=True)+'\n')
    print('deployed inputs', len(runtime['inputs']), 'excluded', len(runtime['excluded_package_only_inputs']), 'JNI', runtime['jni_counts'])


if __name__ == '__main__':
    main()
