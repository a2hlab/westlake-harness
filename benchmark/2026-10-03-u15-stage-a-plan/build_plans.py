"""Generate local-only disabled plans; capture explicitly reads retained local evidence."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKSPACES = ROOT.parent
MASTER = WORKSPACES / 'westlake-harness'
PREFIX = '$WORKSPACES/westlake-harness/benchmark/' + HERE.name
SERIALS = {'5ea': '5ea34a4500000000000000001123012c',
           '5cd': '5cd1e3dd00000000000000000923012c',
           '61b': '61b0657200000000000000000324012c'}


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable(value):
    if isinstance(value, str):
        return value.replace(str(WORKSPACES) + '/', '$WORKSPACES/')
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    return value


def capture():
    sources = []
    table_root = MASTER / 'benchmark/2026-10-03-u15-observation-keys'
    paths = [(table_root / 'u15-stage-a-keys.json', 'key-table.json'),
             (MASTER / 'benchmark/2026-10-03-u14-reference/sources.json', 'reference.json')]
    for window in (1, 2, 3):
        paths.append((MASTER / f'benchmark/2026-10-03-u14-stage-a-plan/window{window}-signoff/outer-signoff.json',
                      f'window{window}-signoff.json'))
    for source, target in paths:
        write(HERE / 'inputs' / target, portable(read(source)))
        sources.append({'source': portable(str(source)), 'source_sha256': sha(source),
                        'snapshot': 'inputs/' + target, 'snapshot_sha256': sha(HERE / 'inputs' / target)})
    table = read(HERE / 'inputs/key-table.json')
    for board in table['boards']:
        for group in board['shards']:
            source = table_root / group['keys_file']
            target = HERE / 'inputs/accepted-keys' / group['keys_file']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            sources.append({'source': portable(str(source)), 'source_sha256': sha(source),
                            'snapshot': str(target.relative_to(HERE)), 'snapshot_sha256': sha(target)})
    run = WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan/window1/u14-A1-r3-20261003T120358'
    specifications = [
        ('flutter-anw', '5ea/runner/movers-localsend-1/*/*/localsend/hilog.txt',
         r'eglCreateWindowSurface: detected ANW shim (?:0x)?([0-9A-Fa-f]+), unwrapped to OH NativeWindow=(?:0x)?([0-9A-Fa-f]+)'),
        ('flutter-eglsurface', '5ea/runner/movers-localsend-1/*/*/localsend/hilog.txt',
         r'eglCreateWindowSurface: dpy=.* -> EGLSurface=(?:0x)?([0-9A-Fa-f]+)'),
        ('resident-publication', '5cd/runner/movers-fd-fluffychat-1/*/*/fd-fluffychat/hilog.txt',
         r'\[N3-OWNER\] resident runtime published for westlake\.anl\.app\.[0-9]+\.[0-9]+'),
        ('bind-order', '5cd/runner/movers-newpipe-1/*/*/newpipe/hilog.txt',
         r'\[B8-AMB-ORDER\] holding in-process bind until org\.schabi\.newpipe\.MainActivity is started'),
        ('compat-visible', '5cd/runner/movers-cv2-com-ath0-rpn-1/*/*/cv2-com-ath0-rpn/hilog.txt',
         r'\[U10-COMPAT-VISIBLE\] owner_verified view=default resident_view=westlake\.sealed\.child')]
    markers = []
    for name, pattern, regex in specifications:
        matches = list(run.glob(pattern))
        if len(matches) != 1:
            raise ValueError('ambiguous hilog source ' + name)
        source = matches[0]
        lines = source.read_text(errors='backslashreplace').splitlines()
        number, text = next((number, text) for number, text in enumerate(lines, 1) if re.search(regex, text))
        markers.append({'id': name, 'regex': regex, 'source': portable(str(source)),
                        'run_directory': portable(str(source.parent)), 'source_sha256': sha(source),
                        'line': number, 'text': text, 'observed_key': source.parent.name,
                        'scope': 'retained U14 diagnostic only; not proof of a new U15 fix or UI',
                        'pid': int(text.split()[2]), 'pointer_groups_must_be_nonzero': name.startswith('flutter-')})
    write(HERE / 'inputs/markers.json', markers)
    write(HERE / 'inputs/provenance.json', sources)


def groups_from(table):
    groups = {}
    for board in table['boards']:
        groups[board['board']] = []
        for group in board['shards']:
            keys = (HERE / 'inputs/accepted-keys' / group['keys_file']).read_text().splitlines()
            groups[board['board']].append((group, [key.strip() for key in keys if key.strip() and not key.startswith('#')]))
    return groups


def validate(groups, reference):
    coverage = {}
    for board, rows in groups.items():
        seen = set()
        for group, keys in rows:
            for key in keys:
                if key in seen:
                    raise ValueError('duplicate category key ' + key)
                seen.add(key)
                if reference['keys'][key]['verdict'] == 'lit':
                    if key in coverage or reference['keys'][key]['board'] != board:
                        raise ValueError('duplicate or wrong-board protection')
                    coverage[key] = board
            if group['name'] == 'lottery' and group['runs_per_key'] != 6:
                raise ValueError('lottery requires six consecutive trials')
    lit = {key for key, row in reference['keys'].items() if row['verdict'] == 'lit'}
    if set(coverage) != lit:
        raise ValueError('missing provisional reference protection')
    return coverage


def validate_marker(marker):
    match = re.search(marker['regex'], marker['text'])
    if not match:
        raise ValueError('marker does not match original hilog')
    if marker['pointer_groups_must_be_nonzero'] and any(int(value, 16) == 0 for value in match.groups()):
        raise ValueError('zero pointer is not successful conversion')


def binding_slots():
    names = ['package', 'bundle_sha256', 'native_manifest_sha256', 'native_inputs_sha256',
             'transaction_base', 'transaction_base_sha256', 'reference_sha256', 'runtime_fingerprint',
             'boot_fingerprint', 'policy_binding_sha256', 'native_tickets_sha256',
             'outer_admission_sha256', 'armed_correspondence_sha256', 'smoke_spec_sha256']
    return {name: None for name in names}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    if args.capture:
        capture()
    table = read(HERE / 'inputs/key-table.json')
    reference = read(HERE / 'inputs/reference.json')
    reference['status'] = 'pending-U14-promotion'
    reference['provisional_only'] = True
    gains = {}
    for window in (1, 2, 3):
        signoff = read(HERE / f'inputs/window{window}-signoff.json')
        for key, description in signoff['summary']['gains'].items():
            row = signoff['keys'][key]
            if not row.get('lit_runs') or not row.get('outer_eyeball'):
                raise ValueError('gain lacks exact signed UI evidence')
            gains[key] = {'board': row['board'], 'description': description,
                          'signoff': f'inputs/window{window}-signoff.json', 'signed_at': signoff['signed_at'],
                          'verdict': row['outer_eyeball'], 'k_of_n': row['k_of_n']}
            reference['keys'][key] = {**reference['keys'][key], 'verdict': 'lit', 'provisional_gain': gains[key]}
    reference['total_lit'] = sum(row['verdict'] == 'lit' for row in reference['keys'].values())
    reference['baseline'] = 'PROVISIONAL U14-reference126 + three signed Stage A gains; pending-U14-promotion'
    reference['u14_stage_a_gains'] = list(gains)
    reference['tallies'] = {}
    for board in SERIALS:
        rows = [row for row in reference['keys'].values() if row['board'] == board]
        reference['tallies'][board] = {'keys': len(rows), 'lit': sum(row['verdict'] == 'lit' for row in rows),
                                     'verdicts': dict(Counter(row['verdict'] for row in rows))}
    write(HERE / 'provisional-reference.json', reference)
    write(HERE / 'signed-gains.json', gains)
    groups = groups_from(table)
    supplemental = {}
    for board, rows in groups.items():
        scheduled = {key for group, keys in rows for key in keys}
        missing = [key for key, gain in gains.items() if gain['board'] == board and key not in scheduled]
        supplemental[board] = missing
        rows.append(({'name': 'signed-gain-protection', 'runs_per_key': 1}, missing))
    covered = validate(groups, reference)
    markers = read(HERE / 'inputs/markers.json')
    for marker in markers:
        validate_marker(marker)
    counts = {}
    for board, rows in groups.items():
        shards = []
        for group, keys in rows:
            for key in keys:
                for trial in range(1, group['runs_per_key'] + 1):
                    name = f"{group['name']}-{key}-{trial}"
                    relative = f'shards/{board}/{name}.txt'
                    path = HERE / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(key + '\n')
                    shards.append({'name': name, 'key': key, 'category': group['name'],
                                   'trial': trial, 'trials': group['runs_per_key'],
                                   'keys_file': PREFIX + '/' + relative,
                                   'manifest': '$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json'
                                               if key.startswith('cv2-') else table['manifest'],
                                   'input_root': table['input_root'],
                                   'reference_protected': key in covered,
                                   'prediction': group.get('per_key', {}).get(key)})
        counts[board] = len(shards)
        plan = {'serial': SERIALS[board], 'lane': 'cx-t0', 'entry': '90',
                'board': '$WORKSPACES/westlake-harness/.octos/boards/app-lighting.md',
                'phase': 'A', 'execution_enabled': False, 'rollout_ready': False,
                'status': 'pending-61b-reconnect' if board == '61b' else 'pending-U14-promotion',
                'bindings': binding_slots(), 'package': None, 'bundle_sha256': None,
                'package_manifest_sha256': None, 'native_inputs_sha256': None,
                'window_limit_minutes': 45, 'stop_new_tests_by_minute': 35,
                'out': PREFIX + '/$U15_RUN_ID/' + board + '/runner',
                'shards': shards, 'batch_flags': table['batch_flags_base'],
                'after_lock': ['python3', PREFIX + '/draft_guard.py', 'apply'],
                'before_unlock': ['python3', PREFIX + '/draft_guard.py', 'finish'],
                'smoke_spec': PREFIX + '/smoke-' + board + '-slot.json',
                'offline_precheck': {'hypothesis': 'U15 moves selected content/first-fatal walls and preserves promoted U14 UI.',
                                     'result': 'pending promotion, fresh four-face gates, binding and outer authorization',
                                     'expect': {'confirm': 'Signed promoted-reference UI preserved; predicted exact first-fatal changes observed with fresh identity and HW/ZZ reports.',
                                                'refute': 'Confirmed regression, identity or activation failure requires restore; flaky outcomes retain k/n and unknown stays unknown.'}},
                'regression_gate': {'reference_status': 'pending-U14-promotion', 'reference_sha256': None,
                                    'provisional_lit': reference['total_lit'], 'confirmed_regressions_allowed': 0,
                                    'judgment': 'outer screenshot signoff; alive/READY/marker does not prove UI',
                                    'lottery': 'six consecutive per key, retain k/n and unfinished trial index'},
                'restore': {'state': 'promoted-U14-per-board', 'unconditional': True,
                            'package': None, 'bundle_sha256': None, 'identity_assertions': None,
                            'failure_preserves_lock': True, 'sequence': ['stopped-parent rollback', 'full byte identity',
                                                                       'runtime/boot fingerprints', 'fresh HW/ZZ', 'final identity']},
                'process_selftest': {'schema_version': 2, 'stage_a': 'record only, never infer UI',
                                     'promotion': 'selftest_error/badtag/probe_error reject; unknown requires fresh individual outer explanation'},
                'continuation': {'same_bytes': True, 'unmeasured': 'unknown', 'no_new_key_after_minute': 35}}
        write(HERE / f'plan-{board}.json', plan)
        write(HERE / f'smoke-{board}-slot.json', {'execution_enabled': False, 'draft_only': True,
              'historical_diagnostics': 'inputs/markers.json', 'required_live_markers': None, 'probe': {'files': None},
              'native_ticket_assert_unchanged': True, 'multiplicity_limits': None,
              'pending': ['fresh promoted U14 owner maps', 'exact U15 candidate identities',
                          'new M3 runtime diagnostic not observed yet', 'fd-meet N2 ABI marker sample not captured in selected U14 runs',
                          'NSD8/framework/ATrace have no proved new log marker; exact identity plus observation keys, not invented messages'],
              'compat_unavailable': 'not success; alone not smoke failure; require relocation/owner evidence separately'})
    write(HERE / 'bindings.json', {'execution_enabled': False, 'variants': {'common': binding_slots(), '61b': binding_slots()},
                                  'fill_owner': {'candidate_and_arming': 'cx-bms/cx-t0 after exact U15 outer admission',
                                                 'base_and_reference': 'outer/cx-t0 after signed U14 promotion and retained full identity',
                                                 'policy_and_tickets': 'outer after all boards UNLOCK and204 registry rows applied',
                                                 'g2_and_smoke': 'outer fresh Mac+VM+oatdump_remote after U14 promotion'}})
    write(HERE / 'results.json', {'execution_enabled': False, 'rollout_ready': False, 'offline_only': True,
                                 'board_operations': 0, 'vm_ssh_operations': 0, 'production_pass_claimed': False,
                                 'reference_status': 'pending-U14-promotion', 'original_lit': 126,
                                 'signed_gain_count': len(gains), 'provisional_lit': len(covered),
                                 'runs': counts, 'total_runs': sum(counts.values()), 'supplemental_keys': supplemental,
                                 'raw_marker_count': len(markers), '61b_pending': True})
    print(json.dumps(read(HERE / 'results.json'), ensure_ascii=False))


if __name__ == '__main__':
    main()
