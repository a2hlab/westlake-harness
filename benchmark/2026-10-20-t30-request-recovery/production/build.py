#!/usr/bin/env python3
"""Prepare or execute two frozen T30 TUs against exact T29 objects. No device API."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent

def need(value, message):
    if not value:
        raise ValueError(message)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def frozen(root, manifest_path):
    need(root and manifest_path, 'candidate root and frozen manifest required')
    root = root.resolve()
    manifest = json.loads(manifest_path.read_text())
    need(manifest.get('status') == 'T30_SOURCE_FINAL_REVIEWED', 'candidate is not frozen/reviewed')
    found = {}
    for role in ('source_r14', 'source_r15', 'review'):
        row = manifest.get(role, {})
        need(isinstance(row.get('path'), str) and row['path'], 'missing ' + role + ' path')
        need(re.fullmatch(r'[0-9a-f]{64}', row.get('sha256') or ''), 'missing ' + role + ' SHA')
        path = (root / row['path']).resolve()
        need(path.is_relative_to(root), role + ' path escapes snapshot')
        need(path.is_file() and digest(path) == row['sha256'], role + ' SHA mismatch')
        found[role] = path
    need(found['source_r14'].name == 'window_module.c', 'R14 source name mismatch')
    need(found['source_r15'].name == 'provider_adapter.c', 'R15 source name mismatch')
    return manifest, found

def definitions(text):
    rows = [line.split() for line in text.splitlines()]
    return {tuple(row[i] for i in (3, 4, 5, 7)) for row in rows
            if len(row) >= 8 and row[0].endswith(':') and
            row[4] in ('GLOBAL', 'WEAK') and row[6] != 'UND'}

def verify_inputs(recipe, expand):
    for token, row in recipe['inputs'].items():
        path = Path(expand(token))
        need(path.is_file() and path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], 'baseline input drift: ' + token)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 't29-tree', 'orb-root', 'sdk', 'repo', 'candidate-root', 'candidate-pins', 'out'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    recipe = json.loads((HERE / 'recipe.json').read_text())
    if not args.execute:
        if args.candidate_pins:
            frozen(args.candidate_root, args.candidate_pins)
        print(json.dumps({'status': 'PREVIEW_ONLY', 'candidate_frozen': bool(args.candidate_pins),
            'compile_units': ['window_module.c', 'provider_adapter.c'], 'replace_objects': recipe['replace_objects'],
            'baseline_inputs': len(recipe['inputs']), 'bridge_sha256': recipe['bridge_sha256'],
            'compiler_calls': 0, 'device_calls': 0}))
        return
    manifest, candidate = frozen(args.candidate_root, args.candidate_pins)
    need(all((args.baseline, args.t29_tree, args.orb_root, args.sdk, args.repo, args.out)), 'all execution paths required')
    need(args.out.is_absolute() and not str(args.out).startswith(('/tmp/', '/private/tmp/')), 'persistent absolute output required')
    need(not args.out.exists(), 'output exists; do not overwrite original receipts')
    bindings = {'$BASE': args.baseline.resolve(), '$T29_TREE': args.t29_tree.resolve(),
                '$ORB': args.orb_root.resolve(), '$SDK': args.sdk.resolve(), '$HOME': Path.home()}
    def expand(text):
        for key, value in bindings.items():
            text = text.replace(key, str(value))
        need('$' not in text, 'unresolved input anchor')
        return text
    verify_inputs(recipe, expand)
    # Refuse any consumer/owner drift before an output directory or compiler is created.
    need(digest(args.baseline / 'bridge.so') == recipe['bridge_sha256'], 'bridge drift')
    need(digest(args.baseline / 'shim.so') == recipe['shim_sha256'], 'shim drift')
    args.out.mkdir(parents=True)
    raw = args.out / 'raw'
    raw.mkdir()
    receipt = {'status': 'INCOMPLETE_NOT_DEPLOYABLE', 'device_calls': 0,
               'runtime': 'UNKNOWN', 'commands': [], 'recipe_sha256': digest(HERE / 'recipe.json'),
               'builder_sha256': digest(__file__), 'candidate_manifest_sha256': digest(args.candidate_pins),
               'frozen_manifest': manifest, 'baseline_inputs': recipe['inputs']}
    def save():
        (args.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def run(name, command):
        command = list(map(str, command))
        (raw / (name + '.argv.json')).write_text(json.dumps(command, indent=2) + '\n')
        with (raw / (name + '.stdout')).open('wb') as stdout, (raw / (name + '.stderr')).open('wb') as stderr:
            try:
                rc = subprocess.run(command, cwd=args.t29_tree, stdout=stdout, stderr=stderr, timeout=180).returncode
            except subprocess.TimeoutExpired:
                rc = 124
            except OSError as error:
                stderr.write(str(error).encode())
                rc = 127
        (raw / (name + '.rc')).write_text(str(rc) + '\n')
        receipt['commands'].append({'name': name, 'rc': rc})
        save()
        need(rc == 0, 'command failed: ' + name)
        return (raw / (name + '.stdout')).read_text()
    save()
    try:
        run('00-frozen', [sys.executable, args.repo / 'scripts/lab/check_frozen.py', '--git', args.repo,
                          '--registry', args.repo / 'knowledge/frozen/frozen.json'])
        sources = {}
        for unit, name in [('r14', 'window_module.c'), ('r15', 'provider_adapter.c')]:
            sources[unit] = args.out / name
            shutil.copyfile(candidate['source_' + unit], sources[unit])
            need(digest(sources[unit]) == manifest['source_' + unit]['sha256'], 'copied source drift')
        shutil.copyfile(candidate['review'], args.out / 'source-review.raw')
        link = [expand(item) for item in recipe['link']]
        link[link.index('-o') + 1] = str(args.out / 'shim-baseline.so')
        run('01-baseline-link', link)
        need(digest(args.out / 'shim-baseline.so') == recipe['shim_sha256'], 'T29 baseline relink differs')
        for unit, source in sources.items():
            compile_cmd = [expand(item) for item in recipe['compiles'][unit]]
            compile_cmd[compile_cmd.index('-c') + 1] = str(source)
            compile_cmd[compile_cmd.index('-o') + 1] = str(args.out / (unit + '.o'))
            compile_cmd[compile_cmd.index('-MF') + 1] = str(args.out / (unit + '.d'))
            run('02-' + unit, compile_cmd)
            deps = shlex.split((args.out / (unit + '.d')).read_text().replace('\\\n', ' ').split(': ', 1)[1])
            allowed = {str(Path(expand(item)).resolve()) for item in recipe['inputs']} | {str(source.resolve())}
            need(all(str(Path(item).resolve()) in allowed for item in deps), 'new unfrozen compilation dependency')
            old_object = expand(recipe['replace_objects'][unit])
            need(link.count(old_object) == 1, 'baseline object is not unique: ' + unit)
            link = [str(args.out / (unit + '.o')) if item == old_object else item for item in link]
        link[link.index('-o') + 1] = str(args.out / 'shim.so')
        run('03-candidate-link', link)
        rd = expand(recipe['readelf'])
        texts = [run('04-elf-' + label, [rd, '--elf-output-style=GNU', '-h', '-d', '--dyn-syms', '--wide', args.out / file])
                 for label, file in [('baseline', 'shim-baseline.so'), ('candidate', 'shim.so')]]
        before, after = map(definitions, texts)
        need(len(before) == 78 and before == after, 'empty/drifted ABI definitions')
        needed = lambda text: re.findall(r'\(NEEDED\).*Shared library: \[(.*?)\]', text)
        need(needed(texts[0]) and needed(texts[0]) == needed(texts[1]), 'empty/drifted NEEDED')
        need('TEXTREL' not in texts[1], 'candidate TEXTREL')
        exports = {}
        for name in ('ANativeWindow_lock', 'ANativeWindow_unlockAndPost', 'ANativeWindow_setBuffersGeometry'):
            rows = [line.split() for line in texts[1].splitlines() if line.split() and line.split()[-1] == name + '@@LIBC']
            need(len(rows) == 1, 'missing/ambiguous candidate export ' + name)
            exports[name] = hex(int(rows[0][1], 16))
        verify_inputs(recipe, expand)
        need(frozen(args.candidate_root, args.candidate_pins)[0] == manifest, 'frozen manifest changed during build')
        need(digest(args.out / 'source-review.raw') == manifest['review']['sha256'], 'review snapshot drift')
        for unit, source in sources.items():
            need(digest(source) == manifest['source_' + unit]['sha256'], 'source snapshot changed during compile')
        shutil.copyfile(args.baseline / 'bridge.so', args.out / 'bridge.so')
        need(digest(args.out / 'bridge.so') == recipe['bridge_sha256'], 'bridge copy differs')
        receipt.update(status='OFFLINE_CANDIDATE_PENDING_PEER_AND_RUNTIME', compiled_units=2,
                       bridge_recompiled=False, abi_definitions=78, needed=needed(texts[1]), shim_exports=exports)
        receipt['outputs'] = {str(p.relative_to(args.out)): {'sha256': digest(p), 'bytes': p.stat().st_size}
                              for p in args.out.rglob('*') if p.is_file() and p.name != 'receipt.json'}
        save()
        print(json.dumps({'status': receipt['status'], 'bridge': receipt['outputs']['bridge.so'], 'shim': receipt['outputs']['shim.so']}))
    except Exception as error:
        receipt['error'] = str(error)
        save()
        raise

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print('T30 build refused: ' + str(error), file=sys.stderr)
        sys.exit(2)
