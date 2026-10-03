#!/usr/bin/env python3
"""U16 stage-A observation key table (input for cx-t0, not a deployment plan).

    python3 build_keys.py [--out <dir>]

Reads (read-only):
  - benchmark/2026-10-03-u14-reference/sources.json   (PLACEHOLDER reference: U14 126-lit;
    swap to the U16 reference after U15 sign-off + U16 assembly, then rebuild)
  - benchmark/2026-10-03-u15-alias-theme-watch/watchlist.csv (theme-watch eyes, if still wanted)
  - knowledge/gates/flaky-keys.json + U13 stage-A signoffs (lottery evidence gate)

Shards per board (priority): movers (U16 fix observation points) > risk-watch (t3's 4
native-engine lit keys, x1, doubles as regression) > theme-watch > white-watch > lottery
(flaky-only x6, doubles as regression) > lit-regression (reference lit minus every key
already covered above). Same generic invariants as U15:
  - every key in EXACTLY ONE shard per board (pairwise disjoint, asserted)
  - lit-regression ∪ lit risk-watch ∪ lit theme-watch ∪ lit lottery == reference lit
  - every lottery key evidenced (flaky-keys.json or signed 0<k<n)
  - M1 replay keys (fd-uhabits/wikipedia/noice) are movers here (t4's regression evidence)
"""
import csv, glob, hashlib, json, sys
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[2] / 'westlake-harness'
REF = MAIN / 'benchmark/2026-10-03-u14-reference/sources.json'   # PLACEHOLDER
WL = MAIN / 'benchmark/2026-10-03-u15-alias-theme-watch/watchlist.csv'
FLAKY = MAIN / 'knowledge/gates/flaky-keys.json'
SIGNOFF_GLOB = (MAIN.parent / 'westlake-harness-u7-executor/benchmark/'
                '2026-10-03-u13-stage-a-plan/*-signoff/outer-signoff.json')

MIN_PER_RUN = 1.75
RUNS_PER_WINDOW = 25

M = {  # U16 movers: fix observation points (source + expectation)
    'fd-wifianalyzer': ('u16 t1 — WifiManager 8 methods no-wifi semantics (stubs 85938130)',
                        'first fatal moves past WifiManager NoSuchMethodError (cluster N)'),
    'fd-breezyweather': ('u16 t3 — launch-transaction ON_START sync '
                         '(runtime JAR f6f5face, benchmark/2026-10-03-u16-t3-build/)',
                         'first fatal moves past weatherView lateinit (async-lifecycle-ordering); '
                         'lit medium'),
    'localsend': ('u16 flutter interposer (NEW in U16, cc-t3 building; SHA pending — see '
                  'benchmark/2026-10-03-u16-flutter-impeller-proc/; pc=0 glDepthRange next)',
                  'first fatal moves past eglCreateWindowSurface AND past pc=0 glDepthRange'),
    'fd-kitchenowl': ('u16 flutter interposer (NEW in U16, cc-t3 building; SHA pending — see '
                      'benchmark/2026-10-03-u16-flutter-impeller-proc/; pc=0 glDepthRange next)',
                      'first fatal moves past eglCreateWindowSurface AND past pc=0 glDepthRange'),
    'fd-fluffychat': ('u16 flutter interposer (NEW in U16, cc-t3 building; SHA pending — see '
                      'benchmark/2026-10-03-u16-flutter-impeller-proc/; pc=0 glDepthRange next)',
                      'first fatal moves past eglCreateWindowSurface AND past pc=0 glDepthRange'),
    'fd-libre': ('u16 flutter interposer (NEW in U16, cc-t3 building; SHA pending — see '
                 'benchmark/2026-10-03-u16-flutter-impeller-proc/; pc=0 glDepthRange next)',
                 'first fatal moves past eglCreateWindowSurface AND past pc=0 glDepthRange'),
    # t4 M1-split replay evidence keys (the 3 apps the freeze dossier re-verifies)
    'fd-uhabits': ('u16 t4 — M1 split replay evidence (runtime native 1d42dbfb, '
                   'benchmark/2026-10-03-u16-t4-m1-runtime/; FZ-009 pre-registration)',
                   '[M1-COPY] semantics unchanged; auto=same expected (lit re-verify)'),
    'wikipedia': ('u16 t4 — M1 split replay evidence (runtime native 1d42dbfb, '
                  'benchmark/2026-10-03-u16-t4-m1-runtime/; FZ-009 pre-registration)',
                  '[M1-COPY] semantics unchanged; auto=same expected (lit re-verify)'),
    'noice': ('u16 t4 — M1 split replay evidence (runtime native 1d42dbfb, '
              'benchmark/2026-10-03-u16-t4-m1-runtime/; FZ-009 pre-registration)',
              '[M1-COPY] semantics unchanged; auto=same expected (lit re-verify)'),
}
RISK_WATCH = ['fd-minetest', 'fd-mpv', 'fd-organicmaps', 'fd-stk']  # t3 native-engine lit keys


def main():
    ref = json.loads(REF.read_text())['keys']
    wl = {}
    if WL.is_file():
        wl = {r['key']: r for r in csv.DictReader(WL.open())}

    movers = defaultdict(dict)
    for k, (src, expect) in M.items():
        movers[ref[k]['board']][k] = {'source': src, 'expect': expect, 'component': ''}

    risk_watch = defaultdict(list)
    for k in RISK_WATCH:
        risk_watch[ref[k]['board']].append(k)

    theme_watch_all = defaultdict(list)
    for k, r in wl.items():
        if r['role'] in ('watch-lit', 'control-noop'):
            theme_watch_all[ref[k]['board']].append(k)

    white_watch = {
        '5ea': [], '5cd': ['termux', 'cv2-ca-vaults-randomlydie', 'cv2-com-paultirk-yatoo',
                           'cv2-dev-obfusk-jiten-webview'],
        '61b': ['cv2-com-degeder-yam', 'cv2-com-bytehamster-flowitgame'],
    }

    flaky_registry = {e['key'] for e in json.loads(FLAKY.read_text())['keys']}
    lottery = {b: [] for b in ('5ea', '5cd', '61b')}
    lottery_evidence = {}
    for f in sorted(glob.glob(str(SIGNOFF_GLOB))):
        sd = json.loads(Path(f).read_text())
        for k, e in sd.get('keys', {}).items():
            kn = str(e.get('k_of_n', '')).strip()
            if '/' in kn:
                a, b = (int(x) for x in kn.split('/'))
                if 0 < a < b and k not in lottery_evidence and k in ref:
                    lottery[ref[k]['board']].append(k)
                    lottery_evidence[k] = f'signed k/n {kn} ({Path(f).parent.name})'
    for k in sorted(flaky_registry):
        if k in ref and k not in lottery_evidence:
            lottery[ref[k]['board']].append(k)
            lottery_evidence[k] = 'knowledge/gates/flaky-keys.json'

    movers_all = {k for d in movers.values() for k in d}
    risk_all = set(RISK_WATCH)
    # priority: a key that is a mover (or risk-watch) leaves the lottery — one shard per key
    # (the U16 movers include the 3 M1 replay keys, which are also flaky-registry keys)
    for b in list(lottery):
        lottery[b] = [k for k in lottery[b] if k not in movers_all and k not in risk_all]
    lottery_all = {k for ks in lottery.values() for k in ks}
    theme_overlap_lottery = {k for ks in theme_watch_all.values() for k in ks} & lottery_all
    theme_watch = {b: [k for k in ks if k not in theme_overlap_lottery and k not in movers_all
                       and k not in risk_all]
                   for b, ks in theme_watch_all.items()}
    white_watch = {b: [k for k in ks if k not in movers_all and k not in risk_all
                       and k not in lottery_all and k not in {x for v in theme_watch.values() for x in v}]
                   for b, ks in white_watch.items()}

    taken = lottery_all | movers_all | risk_all | {k for ks in theme_watch.values() for k in ks} \
            | {k for ks in white_watch.values() for k in ks}
    lit_reg = defaultdict(list)
    for k, e in ref.items():
        if e['verdict'] == 'lit':
            lit_reg[e['board']].append(k)
    lit_reg = {b: sorted(k for k in ks if k not in taken) for b, ks in lit_reg.items()}

    out = HERE
    (out / 'keys').mkdir(parents=True, exist_ok=True)
    boards_doc = []
    for b in ('5ea', '5cd', '61b'):
        mv, rw = sorted(movers.get(b, {})), sorted(risk_watch.get(b, []))
        tw, ww = sorted(theme_watch.get(b, [])), white_watch.get(b, [])
        lo, lr = lottery.get(b, []), lit_reg.get(b, [])
        runs = len(mv) + len(rw) + len(tw) + len(ww) + len(lo) * 6 + len(lr)
        windows = -(-runs // RUNS_PER_WINDOW)
        (out / f'keys/{b}').mkdir(exist_ok=True)
        for name, keys in (('movers', mv), ('risk-watch', rw), ('theme-watch', tw),
                           ('white-watch', ww), ('lottery', lo), ('lit-regression', lr)):
            (out / f'keys/{b}/{name}.txt').write_text('\n'.join(keys) + ('\n' if keys else ''))
        boards_doc.append({
            'board': b, 'runs_total': runs,
            'breakdown': {'movers': len(mv), 'risk_watch': len(rw), 'theme_watch': len(tw),
                          'white_watch': len(ww), 'lottery_keys': len(lo),
                          'lottery_runs': len(lo) * 6, 'lit_regression': len(lr)},
            'est_minutes_at_1.75min_per_run': round(runs * MIN_PER_RUN, 1),
            'windows_needed': windows, 'runs_per_window_~': RUNS_PER_WINDOW,
            'window_split': 'window1 = movers + risk-watch + theme-watch + white-watch + lottery '
                            '(signal first); windows 2..N = lit-regression',
            'shards': [
                {'name': 'movers', 'priority': 1, 'keys_file': f'keys/{b}/movers.txt',
                 'runs_per_key': 1, 'per_key': movers.get(b, {}),
                 'why': 'U16 fix observation points (t1 wifi, t3 lifecycle, flutter interposer, '
                        't4 M1-split replay evidence)'},
                {'name': 'risk-watch', 'priority': 2, 'keys_file': f'keys/{b}/risk-watch.txt',
                 'runs_per_key': 1,
                 'why': "t3's 4 native-engine lit keys (SurfaceView/GL): onStart-at-launch "
                        're-verify; x1 doubles as their regression run (moved out of '
                        'lit-regression)'},
                {'name': 'theme-watch', 'priority': 3, 'keys_file': f'keys/{b}/theme-watch.txt',
                 'runs_per_key': 1,
                 'per_key': {k: {'role': wl[k]['role'], 'watch': wl[k]['regression_flag']}
                             for k in tw},
                 'why': 'alias-theme regression eyes (U15 watchlist still standing)'},
                {'name': 'white-watch', 'priority': 4, 'keys_file': f'keys/{b}/white-watch.txt',
                 'runs_per_key': 1,
                 'why': 'white-window family without flaky evidence: one watch run each'},
                {'name': 'lottery', 'priority': 5, 'keys_file': f'keys/{b}/lottery.txt',
                 'runs_per_key': 6, 'consecutive_per_key': True, 'multiwin_check': True,
                 'per_key': {k: lottery_evidence[k] for k in lo},
                 'why': 'flaky keys only (registry or signed 0<k<n): x6 consecutive; doubles as '
                        'regression'},
                {'name': 'lit-regression', 'priority': 6, 'keys_file': f'keys/{b}/lit-regression.txt',
                 'runs_per_key': 1,
                 'why': 'reference lit set minus every key covered above: verify no regression'},
            ]})

    doc = {
        'task': 'U16 stage-A observation key-table input for cx-t0', 'date': '2026-10-03',
        'lane': 'oc-t4', 'offline': True, 'board_deploy': False,
        'keys_this_is_input_not_a_full_board_run_plan': True,
        'reference_note': 'PLACEHOLDER: built against benchmark/2026-10-03-u14-reference '
                          '(126 lit). After U15 sign-off + U16 assembly, swap REF to the U16 '
                          'reference and rebuild.',
        'input_root': '~/a2hlab/app-inputs',
        'batch_flags_base': ['--reinstall', '--hilog', '20', '--shots', '5,20', '--focus-check'],
        'window_limit_minutes': 45, 'stop_new_tests_by_minute': 35,
        'priority_order': ['movers (U16 fix observation points)', 'risk-watch (t3 native-engine '
                           'lit keys, x1, doubles as regression)', 'theme-watch', 'white-watch',
                           'lottery (flaky-only x6, doubles as regression)', 'lit-regression'],
        'boards': boards_doc,
        'manifest': '$WORKSPACES/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/apps.json',
    }
    (out / 'u16-stage-a-keys.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')

    # ---- known answers (generic invariants) ----
    shard_names = ('movers', 'risk-watch', 'theme-watch', 'white-watch', 'lottery', 'lit-regression')
    for b in ('5ea', '5cd', '61b'):
        seen = {}
        for sn in shard_names:
            for k in (out / f'keys/{b}/{sn}.txt').read_text().split():
                assert k not in seen, f'{k} in both {seen.get(k)} and {sn} on {b}'
                seen[k] = sn
    union = []
    for b in ('5ea', '5cd', '61b'):
        union += (out / f'keys/{b}/lit-regression.txt').read_text().split()
    lit_rw = sorted(k for k in risk_all if ref[k]['verdict'] == 'lit')
    lit_tw = sorted(k for k in {k for ks in theme_watch.values() for k in ks} if ref[k]['verdict'] == 'lit')
    lit_lot = sorted(k for k in lottery_all if ref[k]['verdict'] == 'lit')
    lit_mv = sorted(k for k in movers_all if ref[k]['verdict'] == 'lit')
    ref_lit = sorted(k for k, e in ref.items() if e['verdict'] == 'lit')
    assert sorted(union + lit_rw + lit_tw + lit_lot + lit_mv) == ref_lit, 'union != reference lit'
    for b in ('5ea', '5cd', '61b'):
        for k in (out / f'keys/{b}/lit-regression.txt').read_text().split():
            assert ref[k]['board'] == b
    for ks in lottery.values():
        for k in ks:
            assert k in lottery_evidence
    # known answer: every SHA prefix quoted in a mover source must be findable in the
    # deliverable dir named in the same source (artifact or receipt) — a wrong SHA would hang
    # the observer on the wrong changed artifact (check_fix_observers matches by prefix).
    import re
    SHA_RE = re.compile(r'\b[0-9a-f]{8}\b')
    for b in ('5ea', '5cd', '61b'):
        for k, v in movers.get(b, {}).items():
            src = v['source']
            for m in SHA_RE.finditer(src):
                pre = m.group(0)
                dm = re.search(r'benchmark/2026-10-03-([\w.-]+)/', src)
                d = HERE.parents[2] / 'westlake-harness/benchmark' / dm.group(0).split('/')[-2] \
                    if dm else None
                if 'pending' in src or not dm:
                    continue    # explicitly-pending deliverables carry no SHA yet
                found = False
                for cand in d.rglob('*'):
                    if cand.is_file() and cand.suffix in ('', '.json', '.txt', '.sh', '.py'):
                        try:
                            if pre in cand.read_text(errors='ignore'):
                                found = True
                                break
                        except OSError:
                            continue
                assert found, f'{k}: SHA prefix {pre} not found in {d}'
    for b, bd in zip(('5ea', '5cd', '61b'), boards_doc):
        print(f"{b}: runs={bd['runs_total']} (movers={bd['breakdown']['movers']} "
              f"risk-watch={bd['breakdown']['risk_watch']} theme-watch={bd['breakdown']['theme_watch']} "
              f"white-watch={bd['breakdown']['white_watch']} lottery={bd['breakdown']['lottery_keys']}x6 "
              f"lit-reg={bd['breakdown']['lit_regression']}) ~{bd['est_minutes_at_1.75min_per_run']}min "
              f"windows={bd['windows_needed']}")
    print(f'shards pairwise disjoint OK; lit-regression({len(union)}) ∪ lit risk-watch({len(lit_rw)}) '
          f'∪ lit theme-watch({len(lit_tw)}) ∪ lit lottery({len(lit_lot)}) ∪ lit movers({len(lit_mv)}) '
          f'== reference lit {len(ref_lit)} OK; boards match')
    print(f'lottery keys all evidenced: {sum(len(v) for v in lottery.values())}')
    print('u16-stage-a-keys.json sha256:',
          hashlib.sha256((out / 'u16-stage-a-keys.json').read_bytes()).hexdigest())
    return 0


if __name__ == '__main__':
    sys.exit(main())
