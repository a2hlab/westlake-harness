#!/usr/bin/env python3
"""U14 stage-A observation key table (input for cx-t0, not a deployment plan).

    python3 build_keys.py [--out <dir>]

Reads (read-only):
  - benchmark/2026-10-03-u14-reference/sources.json      (126 lit keys + board assignment + verdicts)
  - benchmark/2026-10-03-u14-m5-watchlist/watchlist.csv   (m5 dialog-zorder movers)
  - benchmark/2026-10-03-u14-flutter-libandroid/results.json (Flutter EGL interposer movers)

Writes u14-stage-a-keys.json + keys/<board>/<shard>.txt + README snippet data.
Priority per board: movers (predicted first-fatal moves, source+expectation each) >
lottery (still-flaky keys x6 consecutive) > lit-regression (the 126 reference keys, each
stays on its reference board). Windows cut at ~25 runs (~45 min at ~1.75 min/run).
Known answer: per-board lit-regression union == the reference's 126 lit keys, no dupes,
each key on its reference board.
"""
import csv, json, hashlib, sys
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[2] / 'westlake-harness'
REF = MAIN / 'benchmark/2026-10-03-u14-reference/sources.json'
WL = MAIN / 'benchmark/2026-10-03-u14-m5-watchlist/watchlist.csv'
FL = MAIN / 'benchmark/2026-10-03-u14-flutter-libandroid/results.json'

FLUTTER_PREDICTION = ("first fatal moves past eglCreateWindowSurface (high), lit low-medium "
                      "(u14-flutter-libandroid EGL interposer)")

MIN_PER_RUN = 1.75
WINDOW_LIMIT_MIN = 45
STOP_NEW_BY_MIN = 35
RUNS_PER_WINDOW = 25          # floor(45 / 1.75) = 25


def main():
    ref = json.loads(REF.read_text())['keys']
    watch = {r['key']: r for r in csv.DictReader(WL.open())}

    movers = defaultdict(dict)          # board -> key -> {sources, expect}
    for k, r in watch.items():
        b = ref[k]['board']
        movers[b][k] = {'source': 'u14-m5-watchlist',
                        'expect': 'dialog z-order first-fatal move (see watchlist.csv row)',
                        'component': r.get('component', '')}
    for k in ('localsend', 'fd-kitchenowl', 'fd-fluffychat', 'fd-libre'):
        b = ref[k]['board']
        movers[b][k] = {'source': 'u14-flutter-libandroid (EGL interposer)',
                        'expect': FLUTTER_PREDICTION, 'component': ''}
    movers[ref['toutiao']['board']]['toutiao'] = {'source': 'u14 ICU alias shim',
                                                  'expect': 'first fatal moves past ICU load wall',
                                                  'component': ''}
    movers[ref['cv2-org-andresoviedo-dddmodel2']['board']]['cv2-org-andresoviedo-dddmodel2'] = {
        'source': 'M5 named target (DIGEST 690/714/721; outer 09:25)',
        'expect': 'dialog-zorder / window-creation path named by M5; watch first-fatal + t20',
        'component': ''}

    # lottery = flaky keys ONLY: recorded in knowledge/gates/flaky-keys.json, or a signed
    # k_of_n with 0 < k < n in a stage-A window signoff. (Neither holds today -> empty.)
    flaky_registry = {e['key'] for e in json.loads(
        (MAIN / 'knowledge/gates/flaky-keys.json').read_text())['keys']}
    lottery = {b: [] for b in ('5ea', '5cd', '61b')}
    lottery_evidence = {}
    import glob
    for f in sorted(glob.glob(str(MAIN / '../westlake-harness-u7-executor/benchmark/'
                                   '2026-10-03-u13-stage-a-plan/*-signoff/outer-signoff.json'))):
        sd = json.loads(Path(f).read_text())
        for k, e in sd.get('keys', {}).items():
            kn = str(e.get('k_of_n', '')).strip()
            if '/' in kn:
                a, b = (int(x) for x in kn.split('/'))
                if 0 < a < b and k not in lottery_evidence:
                    b_ref = ref[k]['board']
                    if k not in lottery[b_ref]:
                        lottery[b_ref].append(k)
                    lottery_evidence[k] = f'signed k/n {kn} ({Path(f).parent.name})'
    for k in sorted(flaky_registry):
        if k in ref and k not in lottery_evidence:
            b_ref = ref[k]['board']
            if k not in lottery[b_ref]:
                lottery[b_ref].append(k)
            lottery_evidence[k] = 'knowledge/gates/flaky-keys.json'

    # white-watch: the 8 white-window keys previously mis-filed as lottery -> x1 each
    white_watch = {
        '5ea': [],
        '5cd': ['fd-app', 'termux', 'cv2-ca-vaults-randomlydie', 'cv2-com-paultirk-yatoo',
                'cv2-dev-obfusk-jiten-webview'],
        '61b': ['cv2-com-degeder-yam', 'cv2-com-bytehamster-flowitgame'],
    }
    lit_reg = defaultdict(list)
    for k, e in ref.items():
        if e['verdict'] == 'lit':
            lit_reg[e['board']].append(k)
    for b in lit_reg:
        lit_reg[b].sort()

    # lottery keys leave lit-regression: their x6 doubles as the regression run (U13 README
    # footnote pattern -- wikipedia's x6 also served as its regression run)
    lottery_all = {k for ks in lottery.values() for k in ks}
    lit_reg_dedup = {b: [k for k in ks if k not in lottery_all] for b, ks in lit_reg.items()}
    lit_reg = lit_reg_dedup

    out = HERE
    (out / 'keys').mkdir(parents=True, exist_ok=True)
    boards_doc = []
    for b in ('5ea', '5cd', '61b'):
        mv = sorted(movers.get(b, {}))
        ww = white_watch.get(b, [])
        lo = lottery.get(b, [])
        lr = lit_reg.get(b, [])
        runs = len(mv) + len(ww) + len(lo) * 6 + len(lr)
        windows = -(-runs // RUNS_PER_WINDOW)
        (out / f'keys/{b}').mkdir(exist_ok=True)
        def write(name, keys):
            (out / f'keys/{b}/{name}.txt').write_text('\n'.join(keys) + ('\n' if keys else ''))
        write('movers', mv)
        write('white-watch', ww)
        write('lottery', lo)
        write('lit-regression', lr)
        boards_doc.append({
            'board': b, 'runs_total': runs,
            'breakdown': {'movers': len(mv), 'white_watch': len(ww),
                          'lottery_keys': len(lo), 'lottery_runs': len(lo) * 6,
                          'lit_regression': len(lr)},
            'est_minutes_at_1.75min_per_run': round(runs * MIN_PER_RUN, 1),
            'windows_needed': windows, 'runs_per_window_~': RUNS_PER_WINDOW,
            'window_split': 'window1 = movers + lottery (the U14 signal, first); windows 2..N = lit-regression',
            'shards': [
                {'name': 'movers', 'priority': 1, 'keys_file': f'keys/{b}/movers.txt',
                 'runs_per_key': 1,
                 'per_key': {k: movers[b][k] for k in mv},
                 'why': 'U14 predicted first-fatal movers (m5 watchlist / flutter EGL / ICU alias); run first'},
                {'name': 'white-watch', 'priority': 2, 'keys_file': f'keys/{b}/white-watch.txt',
                 'runs_per_key': 1,
                 'why': 'white-window family keys without signed k/n or flaky-registry entry: one watch run each'},
                {'name': 'lottery', 'priority': 3, 'keys_file': f'keys/{b}/lottery.txt',
                 'runs_per_key': 6, 'consecutive_per_key': True, 'multiwin_check': True,
                 'per_key': {k: lottery_evidence[k] for k in lo},
                 'why': 'flaky keys (flaky-keys.json or signed 0<k<n): x6 consecutive on one board, multiwin misroute check'},
                {'name': 'lit-regression', 'priority': 4, 'keys_file': f'keys/{b}/lit-regression.txt',
                 'runs_per_key': 1,
                 'why': 'U14 reference 126-lit set (this board\'s slice): verify no regression'},
            ],
        })

    doc = {
        'task': 'U14 stage-A observation key-table input for cx-t0',
        'date': '2026-10-03', 'lane': 'oc-t4', 'offline': True, 'board_deploy': False,
        'keys_this_is_input_not_a_full_board_run_plan': True,
        'input_root': '~/a2hlab/app-inputs',
        'batch_flags_base': ['--reinstall', '--hilog', '20', '--shots', '5,20', '--focus-check'],
        'window_limit_minutes': WINDOW_LIMIT_MIN, 'stop_new_tests_by_minute': STOP_NEW_BY_MIN,
        'priority_order': [
            'movers (predicted first-fatal moves: m5 watchlist, flutter EGL, ICU alias)',
            'lottery (white-window family keys x6 consecutive on one board, +multiwin check)',
            'lit-regression (U14 reference 126-lit set, verify no regression)',
        ],
        'boards': boards_doc,
        'manifest': '$WORKSPACES/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/apps.json',
        'known_answers': {
            'lit_regression_union_equals_reference': 'check: union of keys/*/lit-regression.txt == '
                                                     'the 126 lit keys of u14-reference/sources.json',
        },
    }
    (out / 'u14-stage-a-keys.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')

    # ---- known answer checks ----
    union = []
    for b in ('5ea', '5cd', '61b'):
        p = out / f'keys/{b}/lit-regression.txt'
        union += p.read_text().split()
    lit_lottery = sorted(k for k in lottery_all if ref[k]['verdict'] == 'lit')
    combined = sorted(union + lit_lottery)
    ref_lit = sorted(k for k, e in ref.items() if e['verdict'] == 'lit')
    assert len(union) == len(set(union)), 'duplicate keys in lit-regression shards'
    assert not (set(union) & set(lit_lottery)), 'lit-regression overlaps lottery keys'
    assert combined == ref_lit, f'lit-regression ∪ lit lottery != 126 lit keys ({len(combined)} vs {len(ref_lit)})'
    for b in ('5ea', '5cd', '61b'):
        for k in (out / f'keys/{b}/lit-regression.txt').read_text().split():
            assert ref[k]['board'] == b, f'{k} on {b} but reference board is {ref[k]["board"]}'
    for b, bd in zip(('5ea', '5cd', '61b'), boards_doc):
        print(f"{b}: runs={bd['runs_total']} (movers={bd['breakdown']['movers']} "
              f"lottery={bd['breakdown']['lottery_keys']}x6 lit-reg={bd['breakdown']['lit_regression']}) "
              f"~{bd['est_minutes_at_1.75min_per_run']}min windows={bd['windows_needed']}")
    print(f'lit-regression({len(union)}) ∪ lit lottery({len(lit_lottery)}) == reference lit {len(ref_lit)} OK; disjoint; boards match')
    # known answer: every lottery key must be evidenced (registry or signed 0<k<n)
    for b in ('5ea', '5cd', '61b'):
        for k in lottery.get(b, []):
            assert k in lottery_evidence, f'lottery key {k} has no flaky evidence'
    print(f'lottery keys all evidenced: {sum(len(v) for v in lottery.values())} keys, '
          f'{sorted(lottery_evidence.items()) if lottery_evidence else "empty"}')
    print('u14-stage-a-keys.json sha256:',
          hashlib.sha256((out / 'u14-stage-a-keys.json').read_bytes()).hexdigest())
    return 0


if __name__ == '__main__':
    sys.exit(main())
