#!/usr/bin/env python3
"""Advisory, file-only reboot prediction; never connects to or changes a board."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from selinux_label_audit import expected_label, load_recipe, plan_targets


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def board_path(path):
    if not isinstance(path, str) or not re.fullmatch(r'/[A-Za-z0-9_./+-]+', path):
        raise ValueError('invalid board path: ' + str(path))
    if str(Path(path)) != path or '..' in Path(path).parts or path.endswith('/'):
        raise ValueError('noncanonical board path: ' + path)
    return path


def read_inputs(path):
    manifest = json.loads(path.read_text())
    names = {'plan', 'snapshot', 'inventory', 'autostart', 'closure', 'recipe', 'queries', 'policy'}
    if manifest.get('schema_version') != 1 or set(manifest.get('inputs', {})) != names:
        raise ValueError('inputs manifest requires exactly: ' + ', '.join(sorted(names)))
    objects, hashes = {}, {}
    for name, reference in manifest['inputs'].items():
        source = Path(os.path.expandvars(reference['path']))
        if not source.is_absolute():
            source = path.parent / source
        if not source.is_file():
            raise ValueError('missing input ' + name + ': ' + str(source))
        actual = digest(source)
        if actual != reference['sha256']:
            raise ValueError('input SHA mismatch ' + name + ': expected=' + reference['sha256'] + ' actual=' + actual)
        hashes[name] = actual
        if name == 'recipe':
            objects[name] = load_recipe(source)
        elif name != 'policy':
            objects[name] = json.loads(source.read_text())
    for name, reference in manifest.get('raw_inputs', {}).items():
        source = Path(os.path.expandvars(reference['path']))
        if not source.is_absolute():
            source = path.parent / source
        if not source.is_file() or digest(source) != reference['sha256']:
            raise ValueError('missing/drifted raw snapshot input: ' + name)
    queries = objects['queries']
    if queries.get('policy_sha256') != hashes['policy'] or queries.get('recipe_sha256') != hashes['recipe']:
        raise ValueError('policy-query evidence binding mismatch')
    snapshot = objects['snapshot']
    inventory = objects['inventory']
    if inventory.get('snapshot_sha256') != hashes['snapshot']:
        raise ValueError('physical/source inventory snapshot binding mismatch')
    if not snapshot.get('boot_id') or not snapshot.get('serial'):
        raise ValueError('snapshot boot/serial missing')
    if snapshot.get('complete') is not True or snapshot.get('boot_stable') is not True:
        raise ValueError('snapshot incomplete or boot unstable')
    for name, item in snapshot.get('items', {}).items():
        if (item.get('rc') != 0 and not item.get('diagnostic')) or name not in manifest.get('raw_inputs', {}):
            raise ValueError('snapshot item failed or lacks a pinned raw input: ' + name)
        for key, pin in [(name, 'raw_sha256'), (name + '.stderr', 'stderr_sha256')]:
            if manifest.get('raw_inputs', {}).get(key, {}).get('sha256') != item.get(pin):
                raise ValueError('snapshot raw receipt binding mismatch: ' + key)
    if snapshot.get('plan_sha256') and snapshot['plan_sha256'] != hashlib.sha256(
            json.dumps(objects['plan'], sort_keys=True, separators=(',', ':')).encode()).hexdigest():
        raise ValueError('snapshot/deployment plan binding mismatch')
    if objects['autostart'].get('serial') != snapshot['serial']:
        raise ValueError('autostart/snapshot serial mismatch')
    plan_targets(objects['plan'], objects['recipe'])
    return objects, hashes


class RecordedQueries:
    """Consume exact queries exported by sepolicy_gate.run_query, including denies."""
    def __init__(self, evidence):
        if not evidence.get('query_provider') or not re.fullmatch(r'[a-f0-9]{64}', evidence.get('query_tool_sha256', '')):
            raise ValueError('query provider identity missing')
        self.rows = {}
        for row in evidence['queries']:
            key = (row['domain'], row['label'], row['permission'], row['class'])
            if key in self.rows or not isinstance(row.get('allowed'), bool) or not row.get('evidence'):
                raise ValueError('duplicate/incomplete permission query')
            self.rows[key] = row

    def __call__(self, domain, label, permission, object_class):
        return self.rows.get((domain, label, permission, object_class))


def collect_queries(run_query, policy, recipe_path, inventory, autostart, closure, query_tool):
    recipe = load_recipe(recipe_path)
    labels = {row['context'].split(':')[2] for row in [*recipe['rules'], recipe['default']]}
    for table in ['physical_files', 'source_files']:
        for row in inventory.get(table, {}).values():
            match = re.fullmatch(r'u:object_r:([A-Za-z0-9_]+):s0', row.get('label', ''))
            if match:
                labels.add(match.group(1))
    domains = {row['domain'] for row in closure['roots']}
    domains.update(row['secon'].split(':')[2] for row in autostart['services'])
    domains.add(autostart['seccomp']['domain'])
    rows = []
    for domain in sorted(domains):
        for label in sorted(labels):
            for object_class, permissions in [('dir', ['search', 'getattr']),
                                               ('file', ['entrypoint', 'execute', 'read', 'open', 'map', 'getattr'])]:
                for permission in permissions:
                    raw = run_query(Path(policy), domain, label, permission, object_class)
                    if not isinstance(raw, list) or any(not isinstance(line, str) for line in raw):
                        raise ValueError('invalid sepolicy query result')
                    rows.append(dict(domain=domain, label=label, permission=permission, **{'class': object_class},
                                     allowed=bool(raw), raw_allow_rows=raw,
                                     evidence='\n'.join(raw) or 'sesearch: exact query returned no allow rows'))
    return dict(policy_sha256=digest(policy), recipe_sha256=digest(recipe_path),
                query_provider='sepolicy_gate.run_query', query_tool_sha256=digest(query_tool), queries=rows)


def simulate(plan, snapshot, inventory, autostart, closure, recipe, query):
    targets = plan_targets(plan, recipe)
    if not isinstance(autostart.get('enabled'), bool) or not isinstance(autostart.get('apply_label_recipe'), bool):
        raise ValueError('autostart enabled/apply_label_recipe must be explicit booleans')
    state = {}
    for path, row in inventory.get('physical_files', {}).items():
        board_path(path)
        if row.get('kind') not in ['file', 'directory'] or not row.get('evidence'):
            raise ValueError('physical inode kind/evidence missing: ' + path)
        state[path] = dict(row, origin='physical-survives-reboot')
    sources = inventory.get('source_files', {})
    for path, row in sources.items():
        board_path(path)
        if not path.startswith('/data/') or row.get('kind') not in ['file', 'directory'] or not row.get('evidence'):
            raise ValueError('invalid persistent source inventory: ' + path)
    physical_complete = inventory.get('physical_complete') is True
    source_complete = inventory.get('source_complete') is True
    rows = []

    def add(kind, path, status, reason, evidence):
        rows.append(dict(kind=kind, path=path, status=status, reason=reason, evidence=evidence))

    def lookup(path):
        return state.get(path), physical_complete

    enabled = autostart['enabled']
    phase = autostart.get('recover_phase')
    replay_supported = enabled and phase == 'before-services'
    if enabled and not replay_supported:
        add('recover-order', '/', 'UNKNOWN', 'recover is not proven before init service use', [autostart.get('evidence', 'autostart input')])
    mounts = plan['mounts'] if 'mounts' in plan else plan['recover_layers']
    if replay_supported:
        for mount, target in zip(mounts, targets):
            source = mount['source']
            if not source.startswith('/'):
                archive = autostart.get('source_root')
                if not archive or not archive.startswith('/data/'):
                    raise ValueError('relative package source requires persistent /data source_root')
                source = archive.rstrip('/') + '/' + source
            source = board_path(source)
            selected = {path: row for path, row in sources.items() if path == source or
                        (target['kind'] == 'directory' and path.startswith(source + '/'))}
            if source not in selected or selected[source]['kind'] != target['kind']:
                add('recover-source', target['target'], 'FAIL' if source_complete else 'UNKNOWN',
                    'persistent source missing or wrong kind: ' + source, [mount.get('evidence', 'deployment plan')])
                state = {path: row for path, row in state.items() if path != target['target'] and not path.startswith(target['target'] + '/')}
                continue
            state = {path: row for path, row in state.items() if path != target['target'] and not path.startswith(target['target'] + '/')}
            for source_path, source_row in selected.items():
                canonical = target['target'] + source_path[len(source):]
                row = dict(source_row, origin='autostart-bind-replay', source=source_path)
                if autostart['apply_label_recipe']:
                    row['label'], row['recipe_rule'] = expected_label(canonical, recipe)
                    row['label_assumption'] = 'generated recipe executes and readback succeeds'
                state[canonical] = row

    def permission(path, domain, permissions, object_class, kind):
        row, complete = lookup(path)
        if row is None:
            status = 'FAIL' if complete else 'UNKNOWN'
            add(kind, path, status, 'inode absent' if complete else 'underlying physical inode not captured', ['physical/source inventory'])
            return status
        required_kind = 'directory' if object_class == 'dir' else 'file'
        if row.get('kind') != required_kind:
            add(kind, path, 'FAIL', 'wrong inode kind', [row['evidence']])
            return 'FAIL'
        label = row.get('label', '')
        match = re.fullmatch(r'u:object_r:([A-Za-z0-9_]+):s0', label)
        if not match:
            add(kind, path, 'UNKNOWN', 'missing/unsupported inode context: ' + label, [row['evidence']])
            return 'UNKNOWN'
        failures, missing, evidence = [], [], [row['evidence']]
        for perm in permissions:
            proof = query(domain, match.group(1), perm, object_class)
            if proof is None:
                missing.append(perm)
            else:
                evidence.append(proof['evidence'])
                if not proof['allowed']:
                    failures.append(perm)
        status = 'FAIL' if failures else ('UNKNOWN' if missing else 'PASS')
        add(kind, path, status, 'domain=' + domain + ' label=' + label +
            ' denied=' + ','.join(failures) + ' unqueried=' + ','.join(missing), evidence)
        return status

    def traversal(path, domain):
        statuses = []
        for parent in reversed(Path(path).parents):
            if str(parent) != '/':
                statuses.append(permission(str(parent), domain, ['search', 'getattr'], 'dir', 'path-visibility'))
        return statuses

    services = autostart.get('services')
    if not services:
        raise ValueError('init service configuration missing')
    closure_rows = closure.get('objects', {})
    roots = closure.get('roots')
    if not roots:
        raise ValueError('native closure roots missing')
    for service in services:
        path = board_path(service['path'])
        secon = re.fullmatch(r'u:r:([A-Za-z0-9_]+):s0', service['secon'])
        if not secon or not service.get('evidence'):
            raise ValueError('service secon/provenance missing')
        domain = secon.group(1)
        traversal(path, domain)
        permission(path, domain, ['entrypoint', 'execute'], 'file', 'init-entrypoint')
        if path not in [row['path'] for row in roots]:
            raise ValueError('service omitted from native closure roots: ' + path)
    visited = set()

    def walk(path, domain):
        key = (path, domain)
        if key in visited:
            return
        visited.add(key)
        row = closure_rows.get(path)
        permission(path, domain, ['read', 'open', 'map'], 'file', 'dependency-map')
        traversal(path, domain)
        inode, complete = lookup(path)
        if row is None:
            add('needed-closure', path, 'UNKNOWN', 'DT_NEEDED inventory missing', ['native closure input'])
            return
        if inode and (not row.get('sha256') or row['sha256'] != inode.get('sha256')):
            add('needed-closure', path, 'UNKNOWN', 'DT_NEEDED evidence is not bound to predicted ELF bytes', [row.get('evidence', 'native closure input')])
            return
        if not isinstance(row.get('needed'), list) or not row.get('evidence'):
            raise ValueError('DT_NEEDED/evidence missing: ' + path)
        for edge in row['needed']:
            target = edge.get('resolved_path')
            if not edge.get('soname') or not edge.get('namespace') or not edge.get('evidence'):
                raise ValueError('needed edge lacks soname/namespace/resolution evidence')
            if not target:
                add('needed-closure', path, 'FAIL', 'unresolved DT_NEEDED ' + edge['soname'], [edge['evidence']])
            else:
                walk(board_path(target), domain)

    for root in roots:
        walk(board_path(root['path']), root['domain'])
    seccomp = autostart.get('seccomp', {})
    name = seccomp.get('name')
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_]+', name) or not seccomp.get('domain'):
        raise ValueError('seccomp name/domain missing')
    parameters = snapshot.get('params', {})
    layers = parameters.get('const.cust.config_dir_layer')
    if 'const.cust.config_dir_layer' not in parameters:
        layer_roots = []
        add('seccomp-cfg', '/', 'UNKNOWN', 'config_policy parameter query missing', ['snapshot.params'])
    elif layers is None:
        layer_roots = ['/system', '/chipset', '/sys_prod', '/chip_prod']
    elif isinstance(layers, str) and layers.startswith('/'):
        layer_roots = [board_path(part) for part in layers.split(':')]
    else:
        layer_roots = []
        add('seccomp-cfg', '/', 'UNKNOWN', 'config_policy parameter fallback is not proven: ' + str(layers), ['snapshot.params'])
    visible, uncertain = [], []
    for layer in layer_roots:
        path = layer + '/lib64/seccomp/lib' + name + '_filter.z.so'
        row, complete = lookup(path)
        if row is None and complete:
            continue
        statuses = traversal(path, seccomp['domain']) if row else []
        statuses.append(permission(path, seccomp['domain'], ['getattr', 'read', 'open'], 'file', 'seccomp-visible'))
        if all(status == 'PASS' for status in statuses):
            visible.append(path)
        elif 'FAIL' not in statuses:
            uncertain.append(path)
    if layer_roots:
        status = 'UNKNOWN' if uncertain else ('PASS' if len(visible) == 1 else 'FAIL')
        add('seccomp-cfg', 'lib64/seccomp/lib' + name + '_filter.z.so', status,
            'visible_count=' + str(len(visible)) + ' unknown_count=' + str(len(uncertain)) + ' required_count=1',
            [seccomp.get('evidence', 'autostart input'), *visible, *uncertain])
    statuses = [row['status'] for row in rows]
    overall = 'FAIL' if 'FAIL' in statuses else ('UNKNOWN' if 'UNKNOWN' in statuses else 'PASS')
    return dict(schema_version=1, status=overall, safe_to_reboot=overall == 'PASS', advisory_only=True,
                execution_enabled=False, board_access=False, serial=snapshot['serial'], boot_id=snapshot['boot_id'],
                binding_rule='all existing bind mounts disappear; only proved physical/source inventory survives',
                init_invalid='old in-memory INVALID latch does not survive a real reboot; new exec failures are checked separately',
                label_assumption='successful generated-shell relabel/readback, not a predicted permission to chcon',
                counts={status: statuses.count(status) for status in ['PASS', 'FAIL', 'UNKNOWN']},
                checks=rows, predicted_files=state)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        objects, hashes = read_inputs(args.inputs.resolve())
        query = RecordedQueries(objects['queries'])
        report = simulate(objects['plan'], objects['snapshot'], objects['inventory'], objects['autostart'],
                          objects['closure'], objects['recipe'], query)
        report['input_sha256'] = hashes
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out / 'prediction.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        table = ['kind\tpath\tstatus\treason']
        table.extend('\t'.join(row[key] for key in ['kind', 'path', 'status', 'reason']) for row in report['checks'])
        (args.out / 'prediction.tsv').write_text('\n'.join(table) + '\n')
        print(report['status'] + ' advisory_only=true execution_enabled=false')
        for row in report['checks']:
            if row['status'] != 'PASS':
                print(row['status'] + ' ' + row['kind'] + ' ' + row['path'] + ' ' + row['reason'])
        return 0 if report['status'] == 'PASS' else 1
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        print('NO_PREDICTION: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
