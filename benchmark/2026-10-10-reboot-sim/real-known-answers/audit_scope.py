"""File-only observed preload/map label audit; never authorizes a reboot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts/lab'))
from board_state_diff import load
from selinux_label_audit import expected_label, load_recipe

SANDBOX = '/system/etc/sandbox/appdata-sandbox.json'
ROUTE = '/system/lib64/westlake/route-a/'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned(reference, base):
    path = Path(os.path.expandvars(reference['path']))
    if not path.is_absolute():
        path = base / path
    if path.is_symlink() or not path.is_file() or digest(path) != reference['sha256']:
        raise ValueError('missing/drifted evidence: ' + reference['path'])
    return path


def manual_libraries(text):
    names = {}
    for number, line in enumerate(text.splitlines(), 1):
        match = re.fullmatch(r'(u:object_r:[a-zA-Z0-9_]+:s0)\s+(lib[A-Za-z0-9_.+-]+\.so|appdata-sandbox\.json)', line)
        if not match:
            raise ValueError('unrecognized manual label row at line ' + str(number))
        context, name = match.groups()
        if name in names:
            raise ValueError('duplicate manual basename: ' + name)
        names[name] = dict(actual=context, line=number, text=line)
    if 'appdata-sandbox.json' not in names or len(names) != 24:
        raise ValueError('expected original 23 library basenames plus sandbox row')
    return names


def snapshot_rows(path, recipe, proofs, required_names):
    snapshot, raw, problems = load(path)
    if problems or snapshot.get('selinux_enforce') != 'Enforcing':
        raise ValueError('snapshot integrity/collection/Enforcing refusal: ' + str(problems))
    labels = snapshot['labels']
    targets = [SANDBOX] + sorted(target for target in labels if target.startswith(ROUTE) and target.endswith('.so'))
    rows = []
    for target in targets:
        actual = labels.get(target)
        expected, rule = expected_label(target, recipe)
        actual_type = actual.split(':')[2] if actual and len(actual.split(':')) == 4 else ''
        permissions = ['read', 'open', 'getattr'] if target == SANDBOX else ['read', 'open', 'map']
        evidence = []
        for name, item in sorted(raw.items()):
            if item['rc'] != 0 or item['stderr'].strip():
                continue
            for number, line in enumerate(item['stdout'].splitlines(), 1):
                fields = line.split()
                if len(fields) >= 2 and fields[-1] == target and actual in fields[:-1]:
                    evidence.append(dict(raw=snapshot['items'][name]['raw'], line=number, text=line,
                                         sha256=snapshot['items'][name]['raw_sha256']))
        matching = [proof for proof in proofs if proof.get('domain') == 'appspawn' and
                    proof.get('label') == actual_type and
                    proof.get('class') == 'file' and proof.get('perm') in permissions and proof.get('rule')]
        allowed = list({proof['perm']: proof for proof in reversed(matching)}.values())
        proven = {proof['perm'] for proof in allowed}
        status = 'FAIL' if actual and actual != expected else 'PASS' if (
            actual == expected and evidence and set(permissions) <= proven) else 'UNKNOWN'
        rows.append(dict(path=target, actual=actual, expected=expected, rule=rule, domain='appspawn',
                         permissions=permissions, status=status, evidence=evidence, policy_proofs=allowed,
                         reason='recipe mismatch; permission denial is not inferred' if status == 'FAIL' else
                         'observed inode label and signed positive file permissions' if status == 'PASS' else
                         'missing observed label/raw row/positive permission proof'))
    observed_names = {Path(row['path']).name for row in rows if row['path'].startswith(ROUTE)}
    missing = sorted(set(required_names) - observed_names)
    scope_status = 'FAIL' if any(row['status'] == 'FAIL' for row in rows) else (
        'PASS' if not missing and rows and all(row['status'] == 'PASS' for row in rows) else 'UNKNOWN')
    return dict(serial=snapshot['serial'], boot_id=snapshot['boot_id'], status=scope_status,
                checks=rows, missing_route_basenames=missing, observed_route_libraries=len(observed_names),
                declared_capture_coverage_complete=snapshot.get('complete') is True,
                declared_plan_target_count=snapshot.get('plan_target_count'),
                raw_items_verified=len(raw), captured_at=snapshot['captured_at'])


def context(manifest, base):
    recipe_path = pinned(manifest['recipe'], base)
    recipe = load_recipe(recipe_path)
    policy_path = pinned(manifest['policy'], base)
    report_path = pinned(manifest['policy_evidence'], base)
    policy = json.loads(report_path.read_text())
    canonical_recipe = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()
    if (policy.get('failures') != [] or policy.get('policy_sha256') != digest(policy_path) or
            policy.get('recipe_sha256') != canonical_recipe):
        raise ValueError('signed positive policy evidence binding mismatch')
    manual_path = pinned(manifest['61b_mislabeled'], base)
    manual = manual_libraries(manual_path.read_text())
    return recipe, policy, manual


def build(manifest, base):
    recipe, policy, manual = context(manifest, base)
    names = sorted(name for name in manual if name.endswith('.so'))
    cases = {}
    for name in ['5cd', '5ea']:
        source = pinned(manifest[name], base)
        cases[name] = snapshot_rows(source, recipe, policy['proofs'], names)
        cases[name]['source'] = manifest[name]
    pre_path = pinned(manifest['61b_pre'], base)
    pre_lines = pre_path.read_text().splitlines()
    sandbox = next((dict(line=number, text=line) for number, line in enumerate(pre_lines, 1)
                    if line.split() == [manual['appdata-sandbox.json']['actual'], SANDBOX]), None)
    if sandbox is None:
        raise ValueError('61b manual sandbox label does not match pre-fix source')
    roots = sorted({line.split()[4] for line in pre_lines if len(line.split()) >= 6 and
                    line.split()[4].startswith(ROUTE) and not line.split()[4].endswith('.so')})
    if not roots:
        raise ValueError('pre-fix route namespace mount paths missing')
    checks = []
    for name, row in sorted(manual.items()):
        candidates = [SANDBOX] if name == 'appdata-sandbox.json' else sorted({check['path']
            for case in cases.values() for check in case['checks'] if Path(check['path']).name == name and
            any(check['path'].startswith(root + '/') for root in roots)})
        expected = expected_label(SANDBOX if name == 'appdata-sandbox.json' else ROUTE + name, recipe)[0]
        checks.append(dict(basename=name, canonical_candidates=candidates,
                           identity_basis='exact pre-fix path' if name == 'appdata-sandbox.json' else
                           'pre-fix basename plus pre-fix mount root matched to healthy observed paths; not original per-file path capture',
                           actual=row['actual'], expected=expected,
                           status='FAIL' if row['actual'] != expected else 'UNKNOWN',
                           phase='server-start' if name == 'appdata-sandbox.json' else 'native-map',
                           evidence=dict(source=manifest['61b_mislabeled'], **row),
                           policy_denial_proven=False))
    cases['61b-pre-fix'] = dict(status='FAIL' if any(row['status'] == 'FAIL' for row in checks) else 'UNKNOWN',
                              checks=checks, sandbox_evidence=sandbox, source=manifest['61b_pre'],
                              affected_basename_count=sum(row['status'] == 'FAIL' for row in checks))
    return dict(schema_version=1, mode='observed-preload-and-route-map-label-scope', cases=cases,
                board_access=False, execution_enabled=False, advisory_only=True, safe_to_reboot=False,
                scope_exclusions=['directory traversal', 'physical underlay', 'persistent sources',
                                  'full DT_NEEDED namespace closure', 'complete init/autostart ordering',
                                  'negative policy queries', 'screenshots and live reboot acceptance'],
                input_references=manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--observed-snapshot', type=Path)
    parser.add_argument('--snapshot-sha256')
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.inputs.read_text())
        if args.observed_snapshot:
            source = dict(path=str(args.observed_snapshot.absolute()), sha256=args.snapshot_sha256)
            path = pinned(source, args.inputs.resolve().parent)
            recipe, policy, manual = context(manifest, args.inputs.resolve().parent)
            case = snapshot_rows(path, recipe, policy['proofs'], [name for name in manual if name.endswith('.so')])
            for root, variable in [(Path(os.environ.get('WORKSPACES', REPO.parent)), '$WORKSPACES'),
                                   (Path.home(), '$HOME')]:
                if path.is_relative_to(root):
                    source['path'] = variable + '/' + str(path.relative_to(root))
                    break
            case['source'] = source
            report = dict(schema_version=1, mode='observed-preload-and-route-map-label-scope',
                          cases={case['serial']: case}, safe_to_reboot=False, execution_enabled=False,
                          board_access=False, advisory_only=True, input_references=manifest,
                          scope_exclusions=['full reboot state, traversal, closure, negative policy and acceptance'])
        else:
            if args.snapshot_sha256:
                raise ValueError('snapshot SHA requires --observed-snapshot')
            report = build(manifest, args.inputs.resolve().parent)
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out / 'prediction.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
        table = ['case\tpath_or_basename\tstatus\tactual\texpected']
        for name, case in report['cases'].items():
            table.extend('\t'.join([name, row.get('path', row.get('basename')), row['status'],
                                    str(row['actual']), row['expected']]) for row in case['checks'])
            print(name + ' scope=' + case['status'])
        (args.out / 'prediction.tsv').write_text('\n'.join(table) + '\n')
        print('safe_to_reboot=false; scope PASS is not complete reboot safety')
        if args.observed_snapshot:
            return 0 if case['status'] == 'PASS' else 1
        return 0 if (report['cases']['5cd']['status'] == report['cases']['5ea']['status'] == 'PASS' and
                     report['cases']['61b-pre-fix']['affected_basename_count'] == 24) else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('NO_SCOPE_PREDICTION: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
