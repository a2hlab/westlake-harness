"""Prepare disabled U14 observation plans from the accepted v4 table; no device IO."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKSPACES = ROOT.parent
PREFIX = '$WORKSPACES/westlake-harness-u7-executor/' + str(HERE.relative_to(ROOT))
MASTER = '$WORKSPACES/westlake-harness'
SERIALS = {'5ea': '5ea34a4500000000000000001123012c',
           '5cd': '5cd1e3dd00000000000000000923012c',
           '61b': '61b0657200000000000000000324012c'}
BASES = {'common': '2abe4a4917e09d53f47edcfec0ec21b9e131fc72253b8f4aa3d47ff87e8d5aa0',
         '61b': '0a31ad3515c021ce22d00c3d2e2543e16f9164a1b7d2fc6d1d966f3f2fbba761'}


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_groups(table, sources):
    groups = {}
    for board in table['boards']:
        groups[board['board']] = []
        for shard in board['shards']:
            path = sources / shard['keys_file']
            keys = [s.strip() for s in path.read_text().splitlines() if s.strip() and not s.startswith('#')]
            groups[board['board']].append((shard, keys))
    return groups


def validate(groups, reference, bindings):
    lit = {k: v for k, v in reference['keys'].items() if v['verdict'] == 'lit'}
    protected, lottery, covered = {}, {}, {}
    for board, rows in groups.items():
        seen = set()
        for shard, keys in rows:
            if len(keys) != len(set(keys)):
                raise ValueError('duplicate input key')
            if seen & set(keys):
                raise ValueError('all shard categories must be disjoint')
            seen.update(keys)
            for key in keys:
                if key in lit:
                    if key in covered or lit[key]['board'] != board:
                        raise ValueError('reference board mismatch or duplicate')
                    covered[key] = board
            if shard['name'] in ('lit-regression', 'lottery'):
                target = protected if shard['name'] == 'lit-regression' else lottery
                for key in keys:
                    if key in target or lit.get(key, {}).get('board') != board:
                        raise ValueError('reference board mismatch or duplicate')
                    target[key] = board
    if set(covered) != set(lit):
        raise ValueError('protection union must be exactly the 126 signed keys')
    if len(protected) != 107 or len(lottery) != 6 or reference['total_lit'] != 126:
        raise ValueError('unexpected accepted reference/table cardinality')
    for variant, expected in BASES.items():
        if bindings['variants'][variant]['transaction_base_sha256'] != expected:
            raise ValueError('candidate must target the actual armed U13 base')
    return protected, lottery


def manifest_for(key):
    if key.startswith('cv2-'):
        return ('$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json',
                '$WORKSPACES/westlake-inputs/corpus-v2/app-inputs')
    return (MASTER+'/benchmark/2026-09-28-bms-route-deploy/batch/apps.json', '~/a2hlab/app-inputs')


def build():
    table = read(HERE/'inputs/key-table.json')
    reference = read(HERE/'inputs/reference.json')
    bindings = read(HERE/'inputs/bindings.json')
    source = HERE/'inputs/accepted-keys'
    for row in read(HERE/'inputs/key-source-index.json')['files']:
        if sha(HERE/row['copy']) != row['sha256']:
            raise ValueError('accepted key snapshot drift')
    groups = load_groups(table, source)
    protected, lottery = validate(groups, reference, bindings)
    totals = {}
    for board, rows in groups.items():
        variant = '61b' if board == '61b' else 'common'
        binding = bindings['variants'][variant]
        recovery = read(HERE/f'inputs/recovery-{board}.json')
        if recovery['identity_assertions'] != 321 or recovery['unique_paths'] != 319:
            raise ValueError('U13 recovery requires its complete retained identity')
        shards = []
        for group, keys in rows:
            for key in keys:
                for trial in range(1, group['runs_per_key']+1):
                    name = f'{group["name"]}-{key}-{trial}'
                    rel = f'keys/{board}/{name}.txt'
                    path = HERE/rel; path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(key+'\n')
                    manifest, inputs = manifest_for(key)
                    shards.append({'name': name, 'manifest': manifest, 'input_root': inputs,
                                   'keys_file': PREFIX+'/'+rel, 'key': key, 'category': group['name'],
                                   'trial': trial, 'trials': group['runs_per_key'],
                                   'reference_protected': reference['keys'].get(key, {}).get('verdict') == 'lit',
                                   'prediction': group.get('per_key', {}).get(key)})
        totals[board] = len(shards)
        expected = next(b['runs_total'] for b in table['boards'] if b['board'] == board)
        if len(shards) != expected:
            raise ValueError('run count differs from the accepted table')
        plan = {
            'serial': SERIALS[board], 'lane': 'cx-t0', 'entry': '90',
            'board': MASTER+'/.octos/boards/app-lighting.md',
            'why': 'U14 Stage A disabled preparation; actual armed U13 base, accepted v4 disjoint keys',
            'phase': 'A', 'execution_enabled': False, 'rollout_ready': False,
            'package': binding['package'], 'bundle_sha256': binding['bundle_sha256'],
            'package_manifest_sha256': binding['native_manifest_sha256'],
            'native_inputs_sha256': binding['native_inputs_sha256'],
            'out': PREFIX+'/$U14_RUN_ID/'+board+'/runner',
            'window_limit_minutes': 45, 'stop_new_tests_by_minute': 35,
            'offline_precheck': {
                'hypothesis': 'U14 moves the M5/Flutter/ICU first walls while preserving all126 signed U13 reference screens and process crypto health.',
                'evidence': [PREFIX+'/inputs/key-table.json', PREFIX+'/inputs/bindings.json', PREFIX+'/inputs/reference.json'],
                'result': 'pending required G2 production replay and outer authorization',
                'expect': {
                    'confirm': '126 protection keys remain same_or_lit under signed k/n; predicted first-fatal sites move; fresh candidate identity and crypto reports agree.',
                    'refute': 'Confirmed reference regression or activation/identity failure restores U13; crypto failure is recorded during observation and blocks promotion. One flaky blank is inconclusive.'}},
            'after_lock': ['python3', PREFIX+'/draft_guard.py', 'apply'],
            'before_unlock': ['python3', PREFIX+'/draft_guard.py', 'finish'],
            'smoke_spec': PREFIX+f'/smoke-{board}-slot.json',
            'shards': shards,
            'batch_flags': ['--reinstall', '--hilog', '20', '--shots', '5,20', '--focus-check'],
            'after_shard_record_only': ['python3', MASTER+'/benchmark/2026-10-03-u13-stage-a-plan/observe.py',
                                      'shard', '--plan', PREFIX+f'/plan-{board}.json', '--root', '{shard_out}',
                                      '--out', '{out}/selftest/{shard_name}.json', '--name', '{shard_name}'],
            'process_selftest': {'schema_version': 2, 'source': MASTER+'/benchmark/2026-10-03-u13-stage-a-plan/process_selftest.py',
                                'failure_classes': ['selftest_error', 'badtag', 'probe_error'],
                                'stage_a': 'record and ACK each class per shard, do not stop observation for this verdict',
                                'promotion': 'any failure rejects; unknown requires exact per-record outer explanation'},
            'regression_gate': {'reference': MASTER+'/benchmark/2026-10-03-u14-reference',
                                'reference_sha256': sha(HERE/'inputs/reference.json'), 'lit_required': 126,
                                'lit_this_board': sum(v['board']==board and v['verdict']=='lit' for v in reference['keys'].values()),
                                'confirmed_regressions_allowed': 0,
                                'lottery': {'keys': [k for k, b in lottery.items() if b==board], 'trials': 6,
                                            'consecutive_per_key': True, 'multiwin_check': True,
                                            'evidence': MASTER+'/knowledge/gates/flaky-keys.json'},
                                'judgment': 'outer reads snapshot_display t20; preserve k/n, never infer UI from alive/READY'},
            'restore': {'state': 'U13', 'unconditional': True,
                        'package': binding['transaction_base'], 'bundle_sha256': binding['transaction_base_sha256'],
                        'expected': PREFIX+f'/inputs/recovery-{board}.json', 'identity_assertions': 321,
                        'unique_paths': 319, 'fingerprints': recovery['fingerprints'],
                        'failure_preserves_lock': True, 'sequence': ['stopped-parent rollback', '321 complete SHA assertions',
                                                                    'runtime/boot fingerprints', 'fresh HW/ZZ recovery smoke', 'final identity']},
            'continuation': {'same_bytes': True, 'skip_wrapped_records_only': True,
                             'unmeasured': 'unknown, never counted as passed',
                             'lottery': 'continue unfinished trials on same board; retain trial index and original k/n',
                             'budget': 'cutoff controls actual progress; estimated3 windows is not a promise'},
            'pre_lock_requirements': ['fresh Mac+VM full production gates rc0 including executable oatdump/G2',
                                      'outer admission bound to per-board bundle and manifest',
                                      'vmgr RSS and orb latency recorded before/after; RSS>3GiB preventive restart only while all boards unlocked',
                                      'orb/HDC/bind/tools preflight, no lock on failure',
                                      'complete retained U13 identity by byte SHA, not inode',
                                      'receipt-owned stale children cold_stop; OrganicMaps drain/retry safeguard'],
            'pending': ['outer G2 replay/authorization', 'immutable armed correspondence if later approved',
                        'fresh executable apply/finish binding to U13 and candidate identities',
                        'candidate live marker specification and exact probe.files review']}
        write(HERE/f'plan-{board}.json', plan)
        write(HERE/f'smoke-{board}-slot.json', {'draft_only': True, 'execution_enabled': False,
                                             'pending': 'candidate live fix markers, probe.files and multiplicity review after G2'})
    result = {'execution_enabled': False, 'offline_only': True, 'device_operations': 0,
              'runs': totals, 'total_runs': sum(totals.values()), 'reference_protection': 126,
              'unique_lit_regression': len(protected), 'lottery_keys': len(lottery),
              'lit_movers': 13, 'all_categories_disjoint': True,
              'key_table_sha256': sha(HERE/'inputs/key-table.json'), 'bindings_sha256': sha(HERE/'inputs/bindings.json'),
              'production_status': bindings['readiness'], 'outer_window_authorization': None}
    write(HERE/'results.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    build()
