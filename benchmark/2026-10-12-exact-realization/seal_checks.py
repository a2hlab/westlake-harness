"""Preserve demo_selfcheck's non-file seal requirements; never execute commands.

Only a pinned demo-seal/v1 supplies these requirements. An empty result for a
candidate fingerprint is not a complete seal verification. Boot/serial and the
complete realized file set remain the caller's independent checks.
"""
import copy
from pathlib import Path
import re
import shlex

import realization as core
import observations

PATH = re.compile(r'/[A-Za-z0-9_./:+@-]+\Z')
PATTERN = re.compile(r'/[A-Za-z0-9_./:+@*?-]+\Z')
IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_.]*\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
CONTROL = re.compile(r'(/data/westlake-demo/toutiao/recovery-attempts/[A-Za-z0-9_.-]+)(?:/|$)')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def board_path(value, pattern=False):
    need(isinstance(value, str) and (PATTERN if pattern else PATH).fullmatch(value)
         and '..' not in value.split('/'), 'unsafe board path: ' + str(value))
    return value


def validate_seal(seal):
    """Copy the original seal's required structure; do not invent defaults."""
    need(isinstance(seal, dict) and seal.get('schema') == 'demo-seal/v1', 'seal schema')
    need(seal.get('serial') in observations.SERIALS, 'seal serial not whitelisted')
    groups = seal.get('files')
    need(isinstance(groups, dict) and set(groups) == {'runtime', 'boot', 'overlays', 'installation'},
         'files must contain runtime,boot,overlays,installation')
    files = {}
    for group, entries in groups.items():
        need(isinstance(entries, dict) and (group == 'overlays' or bool(entries)), 'empty/invalid files.' + group)
        for path, sha in entries.items():
            board_path(path)
            need(isinstance(sha, str) and SHA.fullmatch(sha), 'invalid file SHA')
            need(path not in files or files[path] == sha, 'conflicting duplicate file')
            files[path] = sha
    system = seal.get('system_params')
    need(isinstance(system, dict) and system, 'system_params required')
    for key, value in system.items():
        need(isinstance(key, str) and IDENT.fullmatch(key) and isinstance(value, str) and value,
             'invalid system parameter')
    packages = seal.get('packages')
    need(isinstance(packages, list) and packages, 'nonempty packages required')
    seen = set()
    for package in packages:
        need(isinstance(package, dict), 'invalid package')
        name = package.get('package')
        need(isinstance(name, str) and IDENT.fullmatch(name) and name not in seen, 'invalid/duplicate package')
        seen.add(name)
        board_path(package.get('apk_path'))
        need(SHA.fullmatch(str(package.get('apk_sha256', ''))) and
             str(package.get('version_code', '')).isdigit(), 'invalid package identity')
    inventories = seal.get('inventories', [])
    need(isinstance(inventories, list), 'invalid inventories')
    for inventory in inventories:
        need(isinstance(inventory, dict), 'invalid inventory')
        patterns, paths = inventory.get('patterns'), inventory.get('paths')
        need(isinstance(patterns, list) and patterns, 'empty inventory patterns')
        for pattern in patterns:
            board_path(pattern, True)
        need(isinstance(paths, list) and paths, 'inventory requires exact unique paths')
        for path in paths:
            need(board_path(path) in files, 'inventory path has no sealed SHA')
        need(len(paths) == len(set(paths)), 'duplicate inventory path')
    return files


def requirements(proof):
    """Read and pin the source seal; only inventory control-root paths may move."""
    identity = proof.get('source_identity')
    need(isinstance(identity, dict), 'source_identity missing')
    kind = identity.get('kind')
    need(kind in {'seal', 'candidate-fingerprint'}, 'source identity kind')
    if kind != 'seal':
        return {}  # Candidate/not_sealed: no claim to full demo-seal coverage.
    base = Path(proof['request']['path']).parent
    source = core.pin(identity, base)
    seal_pin = {key: identity[key] for key in ('path', 'sha256')}
    need(proof.get('source_seal') == seal_pin, 'original seal separately pinned')
    seal = core.read(source)
    files = validate_seal(seal)
    params = proof['parameters']
    target_root = board_path(params['control_root'])
    need(observations.CONTROL.fullmatch(target_root), 'invalid control root')
    old_roots = {match[1] for path in files if (match := CONTROL.match(path))}
    need(len(old_roots) <= 1, 'ambiguous source control root')
    old_root = next(iter(old_roots), None)
    projection = {}
    for row in proof['files']:
        origin, target = row.get('source_target'), row.get('target')
        if origin in projection:
            need(projection[origin] == target, 'ambiguous file projection')
        projection[origin] = target

    def mapped(value):
        if old_root and (value == old_root or value.startswith(old_root + '/')):
            return target_root + value[len(old_root):]
        return value

    inventories = copy.deepcopy(seal.get('inventories', []))
    for inventory in inventories:
        for path in inventory['paths']:
            need(projection.get(path) == mapped(path), 'inventory differs from exact file projection')
        inventory['paths'] = [mapped(path) for path in inventory['paths']]
        inventory['patterns'] = [mapped(pattern) for pattern in inventory['patterns']]
    return {'source_seal': seal_pin, 'system_params': copy.deepcopy(seal['system_params']),
            'packages': copy.deepcopy(seal['packages']), 'inventories': inventories}


def sha_rows(raw):
    rows = {}
    for line in raw.splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)', line)
        need(match is not None and match[2] not in rows, 'malformed/duplicate SHA readback')
        board_path(match[2])
        rows[match[2]] = match[1]
    return rows


def collect(req, collector):
    """Use only the caller's read-only collector; propagate transport failures."""
    if not req:
        return {}
    obs = {'files': {}, 'system_params': {}, 'packages': {}, 'inventories': [], 'errors': []}

    def read(kind, command):
        raw, _ = collector.read(kind, command)
        need(isinstance(raw, bytes), 'collector must return raw bytes')
        return raw.decode('utf-8')

    paths = list(dict.fromkeys(p['apk_path'] for p in req['packages']))
    for start in range(0, len(paths), 24):
        batch = paths[start:start + 24]
        rows = sha_rows(read('seal-apks-%04d' % start, 'sha256sum ' + ' '.join(shlex.quote(p) for p in batch)))
        need(set(rows) == set(batch), 'APK SHA readback target set differs')
        obs['files'].update(rows)
    for key in req['system_params']:
        obs['system_params'][key] = read('seal-param-' + key, 'param get ' + key).strip()
    for package in req['packages']:
        name = package['package']
        text = read('seal-package-' + name, 'bm dump -n ' + name)
        try:
            import json
            data, _ = json.JSONDecoder().raw_decode(text[text.index('{'):])
            code = data.get('versionCode')
            need(data.get('name') == name and type(code) is int and code >= 0,
                 'missing/mismatched top-level installed bundle versionCode')
        except (ValueError, AttributeError) as exc:
            raise ValueError('bm identity ' + name + ': ' + str(exc)) from exc
        obs['packages'][name] = {'version_code': str(code)}
    for number, inventory in enumerate(req['inventories']):
        rows = sha_rows(read('seal-inventory-%d' % number, 'sha256sum ' + ' '.join(inventory['patterns'])))
        obs['inventories'].append(sorted(rows))
    return obs


def compare(req, obs):
    """Raise on any original non-file seal drift, including APK bytes."""
    if not req:
        return
    need(isinstance(obs, dict) and obs.get('errors') == [], 'seal read errors missing/nonempty')
    for key, value in req['system_params'].items():
        need(obs.get('system_params', {}).get(key) == value, 'system parameter drift: ' + key)
    for package in req['packages']:
        name = package['package']
        actual = obs.get('packages', {}).get(name, {}).get('version_code', '<absent>')
        need(str(actual) == str(package['version_code']), 'package version drift: ' + name)
        need(obs.get('files', {}).get(package['apk_path']) == package['apk_sha256'], 'package APK SHA drift: ' + name)
    inventories = obs.get('inventories')
    need(isinstance(inventories, list) and len(inventories) == len(req['inventories']), 'inventory count drift')
    for number, inventory in enumerate(req['inventories']):
        need(inventories[number] == sorted(inventory['paths']), 'inventory path drift: ' + str(number))
