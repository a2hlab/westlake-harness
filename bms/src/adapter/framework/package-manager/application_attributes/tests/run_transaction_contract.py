#!/usr/bin/env python3
"""Build the production transaction GN source graph and run its original tests.

This is a Linux compiler/link harness for the four literal GN targets, not an
OH GN build. Unsupported GN expressions fail rather than being silently ignored.
The only test variant adds the existing reference-fixture seeding methods.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import tempfile


def require(value, message):
    if not value:
        raise SystemExit(message)


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--mode', required=True, choices=['Valid', 'Rejected'])
p.add_argument('--pm-root', type=pathlib.Path, required=True)
p.add_argument('--build-dir', type=pathlib.Path, required=True)
p.add_argument('--cc', required=True)
p.add_argument('--cxx', required=True)
p.add_argument('--ar', required=True)
a = p.parse_args()
pm = a.pm_root.resolve()
gn = re.sub(r'#[^\n]*', '', (pm / 'BUILD.gn').read_text())


def block(kind, name):
    matches = re.findall(r'\b' + kind + r'\("' + name + r'"\)\s*\{([^{}]*)\}', gn)
    require(len(matches) == 1, 'SPC46_GN_LITERAL_TARGET_REQUIRED: ' + name)
    body = matches[0]
    fields = {}
    # Deliberately support only the literal assignments used by this graph.
    assignment = r'\s*(\w+)\s*=\s*(\[[^\[\]]*\]|"[^"\n]*")'
    while body.strip():
        match = re.match(assignment, body)
        require(match is not None, 'SPC46_UNSUPPORTED_GN_EXPRESSION: ' + name)
        key, raw = match.groups()
        require(key not in fields, 'SPC46_DUPLICATE_GN_FIELD: ' + key)
        fields[key] = json.loads(raw.rstrip().removesuffix(',') if raw.startswith('"')
                                 else re.sub(r',\s*\]', ']', raw))
        body = body[match.end():]
    return fields


transaction = 'fn01_package_transaction'
query = 'fn01_package_query'
authority = 'fn01_package_authority'
bms = 'fn01_bms_projection'
expected_deps = {transaction: [], query: [transaction],
                 authority: [query, transaction], bms: [transaction]}
targets = {name: block('ohos_static_library', name) for name in expected_deps}
config = block('config', 'apk_installer_config')
require(set(config) == {'include_dirs'}, 'SPC46_UNSUPPORTED_GN_CONFIG')
external_includes = {'//third_party/minizip', '//third_party/openssl/include',
                     '//base/hiviewdfx/hilog/interfaces/native/innerkits/include'}
for name, target in targets.items():
    require(set(target) <= {'sources', 'configs', 'include_dirs', 'deps',
                            'part_name', 'subsystem_name'}, 'SPC46_GN_FIELDS: ' + name)
    require(target.get('sources'), 'SPC46_EMPTY_PRODUCTION_TARGET: ' + name)
    require(target.get('configs') == [':apk_installer_config'], 'SPC46_GN_CONFIGS: ' + name)
    require(target.get('deps', []) == [':' + dep for dep in expected_deps[name]],
            'SPC46_GN_DEPENDENCY_GRAPH: ' + name)
    for source in target['sources']:
        require((pm / source).is_file(), 'SPC46_TRANSACTION_BUILD_CLOSURE_MISSING: ' + source)
    for directory in config['include_dirs'] + target.get('include_dirs', []):
        require(not directory.startswith('//') or directory in external_includes,
                'SPC46_UNSUPPORTED_EXTERNAL_INCLUDE: ' + directory)

# Pin unchanged original tests, not a rewritten implementation of their rules.
originals = {
    'package_transaction': 'ccfaee73449cc8a03a177338ee05b63543d60b2b2f151f39e1cacbddb19bc818',
    'package_update': '569eddb3f22ab602d733ee91708a3524ec3e390082f3d1bc099f789fda9e619a',
    'package_uninstall': 'c66d75ef54177ce258ef9a089672cecd70ee508cc1cd6a79159b68275e29dae3',
    'package_restart_recovery': '7d4735244a44631402dc147872137825f0417c18c52a4ebc7dc00fff522970ac',
    'package_query': 'd1263be8d8bb3c25fc2474325adc508f20c345b17babdecbd7c2603ca303bea0',
    'package_authority': '46d5ef8abdfb81917aae8c5328476127a7f08e3c508b510ddc577df7b80b65e3',
    'bms_projection': '27ce2243fbaf5935a8677dbbd186a28b64b797acb46576433f8ef4fc74a2cbab',
}


def original(name):
    directory = name if name in ('package_query', 'package_authority', 'bms_projection') else 'package_transaction'
    return pm / directory / 'tests' / (name + '_host_test.cpp')


for name, digest in originals.items():
    require(hashlib.sha256(original(name).read_bytes()).hexdigest() == digest,
            'SPC46_ORIGINAL_TEST_CHANGED: ' + name)

out = a.build_dir.resolve() / ('transaction-' + a.mode.lower())
out.mkdir(parents=True, exist_ok=True)
work = pathlib.Path(tempfile.mkdtemp(prefix='run-', dir=out))
commands = []
sanitize = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer']


def run(argv, label):
    argv = [str(x) for x in argv]
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = work / (label + '.log')
    log.write_bytes(result.stdout)
    commands.append({'argv': argv, 'exit_code': result.returncode, 'log': str(log),
                     'log_sha256': hashlib.sha256(result.stdout).hexdigest()})
    (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    print(result.stdout.decode(errors='replace'), end='', flush=True)
    require(result.returncode == 0, f'SPC46_PRODUCTION_COMMAND_FAILED: {label} exit={result.returncode}')


def includes(target):
    return ['-I' + str(pm / directory) for directory in
            config['include_dirs'] + target.get('include_dirs', [])
            if not directory.startswith('//')]


def build_target(name, fixtures=False):
    target = targets[name]
    suffix = '-fixtures' if fixtures else ''
    objects = []
    for index, source in enumerate(target['sources']):
        obj = work / f'{name}{suffix}-{index}.o'
        is_c = source.endswith('.c')
        run([a.cc if is_c else a.cxx, '-std=c11' if is_c else '-std=c++17',
             '-Wall', '-Wextra', '-UNDEBUG', *sanitize, '-pthread',
             *(['-DFN01_ENABLE_REFERENCE_FIXTURES'] if fixtures else []),
             *includes(target), '-c', pm / source, '-o', obj], obj.stem)
        objects.append(obj)
    archive = work / ('lib' + name + suffix + '.a')
    run([a.ar, 'rcs', archive, *objects], archive.stem)
    return archive


archives = {name: build_target(name) for name in targets}
(work / 'graph.json').write_text(json.dumps(targets, indent=2) + '\n')
all_includes = sorted({flag for target in targets.values() for flag in includes(target)})
probe = work / 'production-link.cpp'
probe.write_text('#include "package_transaction_v1.h"\n#include "package_query_v1.h"\n'
                 '#include "package_authority_service_v1.h"\n#include "bms_projection_v1.h"\n'
                 'int main() { return 0; }\n')


def link(source, executable, libs, fixtures=False):
    run([a.cxx, '-std=c++17', '-Wall', '-Wextra', '-UNDEBUG', *sanitize, '-pthread',
         *(['-DFN01_ENABLE_REFERENCE_FIXTURES'] if fixtures else []), *all_includes,
         source, '-Wl,--no-undefined', '-Wl,--whole-archive', *libs,
         '-Wl,--no-whole-archive', '-o', executable], executable.name + '-link')


# Force every object into the executable, including objects not used by a leaf
# test. No test-only fixture method is compiled into this production closure.
link(probe, work / 'production-link', archives.values())
run([work / 'production-link'], 'production-link-run')
fixture_archive = build_target(transaction, fixtures=True)
test_archives = [fixture_archive if name == transaction else archive
                 for name, archive in archives.items()]
selected = (['package_transaction', 'package_update', 'package_uninstall'] if a.mode == 'Valid'
            else ['package_restart_recovery', 'package_query', 'package_authority', 'bms_projection'])
for name in selected:
    executable = work / name
    link(original(name), executable, test_archives, fixtures=True)
    output = work / (name + '-output')
    if name != 'bms_projection':
        output.mkdir()
    run([executable, output], name + '-run')
print('SPC46_COMPLETE_TRANSACTION_GRAPH_AND_ORIGINAL_TESTS_PASS', a.mode, flush=True)
