#!/usr/bin/env python3
"""U15 stage-A observation key table (input for cx-t0, not a deployment plan).

    python3 build_keys.py [--out <dir>]

Reads (read-only):
  - benchmark/2026-10-03-u14-reference/sources.json          (reference lit set — PLACEHOLDER:
    swap to the U15 reference once U14 stage-A is signed, then rebuild; README states this)
  - benchmark/2026-10-03-u15-alias-theme-watch/watchlist.csv (driver/watch-lit/controls)
  - benchmark/2026-10-03-u16-wall-clusters/clusters.csv      (U15-covered clusters E/F/K/M/L)
  - knowledge/gates/flaky-keys.json + U13 stage-A signoffs   (lottery evidence gate)

Shards per board (priority order): movers (predicted first-fatal moves; sources listed per key)
> theme-watch (watch-lit must not stick on splash; controls must be unchanged) > white-watch (x1)
> lottery (flaky-only, x6 consecutive, doubles as regression) > lit-regression (reference lit minus
lottery). Window cut ~25 runs / 45 min at ~1.75 min/run.

Known answers asserted at build time:
  - lit-regression ∪ (lit lottery keys) == reference lit set, disjoint, boards match
  - every lottery key evidenced (flaky-keys.json entry or signed 0<k<n)
"""
import csv, glob, hashlib, json, sys
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[2] / 'westlake-harness'
REF = MAIN / 'benchmark/2026-10-03-u14-reference/sources.json'   # PLACEHOLDER until U15 reference
WL = MAIN / 'benchmark/2026-10-03-u15-alias-theme-watch/watchlist.csv'
CL = MAIN / 'benchmark/2026-10-03-u16-wall-clusters/clusters.csv'
FLAKY = MAIN / 'knowledge/gates/flaky-keys.json'
SIGNOFF_GLOB = (MAIN.parent / 'westlake-harness-u7-executor/benchmark/'
                '2026-10-03-u13-stage-a-plan/*-signoff/outer-signoff.json')

MIN_PER_RUN = 1.75
RUNS_PER_WINDOW = 25
# U15-covered u16 clusters: E Bitmap, F M3 GLSurfaceView, K NSD, M trampoline-x, L fd-api(alias-theme driver dup)
U15_CLUSTERS = ('E', 'F', 'K', 'M', 'L')
FLUTTER_KEYS = ('localsend', 'fd-kitchenowl', 'fd-fluffychat', 'fd-libre')   # cluster A, carried by v2 9b824502


def main():
    ref = json.loads(REF.read_text())['keys']
    wl = {r['key']: r for r in csv.DictReader(WL.open())}
    clusters = {c['cluster']: c for c in csv.DictReader(CL.open())}

    # ---- movers ----
    movers = defaultdict(dict)
    for k, r in wl.items():
        if r['role'] == 'driver':
            movers[ref[k]['board']][k] = {
                'source': 'u15-alias-theme-watch (driver)',
                'expect': r['regression_flag'], 'component': r.get('target_activity', '')}
    for cid in U15_CLUSTERS:
        c = clusters[cid]
        for k in c['keys'].split():
            movers[ref[k]['board']][k] = {
                'source': f'u16 cluster {cid} — {c["owner_deliverable"][:70]}',
                'expect': f'predicted_first_fatal_moves={c["predicted_first_fatal_moves"]} '
                          f'confidence={c["confidence"]}',
                'component': ''}
    for k in FLUTTER_KEYS:
        movers[ref[k]['board']][k] = {
            'source': 'u15-flutter-libandroid-v2 ATrace (9b824502, carries fff9be31 EGL)',
            'expect': 'first fatal stays past eglCreateWindowSurface; ATrace no longer missing',
            'component': ''}
    # fd-meet (outer 11:36): ANL dual-alias b96a8991 + org.jitsi.meet + host 9e3ad72e;
    # observation markers [N2-OWNER] ABI global ready / [N3-OWNER] resident runtime published;
    # expected move unknown (anl-review.md: historical 1 conditional move, no lit prediction)
    movers[ref['fd-meet']['board']]['fd-meet'] = {
        'source': 'u15 ANL dual alias b96a8991 (org.jitsi.meet) + resident host 9e3ad72e; '
                  'markers [N2-OWNER] ABI global ready / [N3-OWNER] resident runtime published',
        'expect': 'unknown (anl-review.md: paired route+global ABI expected to clear public and '
                  'fallback relocations; next RN/Hermes/WebRTC wall unknown, no lit prediction)',
        'component': 'org.jitsi.meet'}

    # ---- theme-watch: watch-lit + control-noop (x1 each, regression eyes) ----
    # dedupe rule (outer 09:50): a theme-watch key overlapping lottery stays in lottery (flagged
    # theme_watch in the json); one overlapping lit-regression moves OUT of lit-regression (the
    # theme-watch run doubles as its regression run). Every key ends up in exactly one shard.
    theme_watch_all = defaultdict(list)
    for k, r in wl.items():
        if r['role'] in ('watch-lit', 'control-noop'):
            theme_watch_all[ref[k]['board']].append(k)

    # ---- white-watch: white-window keys without evidence (same gate as v3) ----
    white_watch = {
        '5ea': [],
        '5cd': ['termux', 'cv2-ca-vaults-randomlydie', 'cv2-com-paultirk-yatoo',
                'cv2-dev-obfusk-jiten-webview'],
        '61b': ['cv2-com-degeder-yam', 'cv2-com-bytehamster-flowitgame'],
    }

    # ---- lottery (flaky-only gate) ----  (computed before dedupe so overlaps can be flagged)
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

    lottery_all = {k for ks in lottery.values() for k in ks}
    theme_overlap_lottery = {k for ks in theme_watch_all.values() for k in ks} & lottery_all
    theme_watch = {b: [k for k in ks if k not in theme_overlap_lottery]
                   for b, ks in theme_watch_all.items()}

    # ---- lit-regression: reference lit minus lottery minus theme-watch keys ----
    lit_reg = defaultdict(list)
    for k, e in ref.items():
        if e['verdict'] == 'lit':
            lit_reg[e['board']].append(k)
    taken = lottery_all | {k for ks in theme_watch.values() for k in ks}
    lit_reg = {b: sorted(k for k in ks if k not in taken) for b, ks in lit_reg.items()}

    # ---- write shards + doc ----
    out = HERE
    (out / 'keys').mkdir(parents=True, exist_ok=True)
    boards_doc = []
    for b in ('5ea', '5cd', '61b'):
        mv, tw, ww = sorted(movers.get(b, {})), sorted(theme_watch.get(b, [])), white_watch.get(b, [])
        lo, lr = lottery.get(b, []), lit_reg.get(b, [])
        runs = len(mv) + len(tw) + len(ww) + len(lo) * 6 + len(lr)
        windows = -(-runs // RUNS_PER_WINDOW)
        (out / f'keys/{b}').mkdir(exist_ok=True)
        for name, keys in (('movers', mv), ('theme-watch', tw), ('white-watch', ww),
                           ('lottery', lo), ('lit-regression', lr)):
            (out / f'keys/{b}/{name}.txt').write_text('\n'.join(keys) + ('\n' if keys else ''))
        boards_doc.append({
            'board': b, 'runs_total': runs,
            'breakdown': {'movers': len(mv), 'theme_watch': len(tw), 'white_watch': len(ww),
                          'lottery_keys': len(lo), 'lottery_runs': len(lo) * 6,
                          'lit_regression': len(lr)},
            'est_minutes_at_1.75min_per_run': round(runs * MIN_PER_RUN, 1),
            'windows_needed': windows, 'runs_per_window_~': RUNS_PER_WINDOW,
            'window_split': 'window1 = movers + theme-watch + white-watch + lottery (signal first); '
                            'windows 2..N = lit-regression',
            'shards': [
                {'name': 'movers', 'priority': 1, 'keys_file': f'keys/{b}/movers.txt',
                 'runs_per_key': 1, 'per_key': movers.get(b, {}),
                 'why': 'U15 predicted first-fatal movers (alias-theme driver, u16 clusters E/F/K/M/L, '
                        'flutter ATrace v2)'},
                {'name': 'theme-watch', 'priority': 2, 'keys_file': f'keys/{b}/theme-watch.txt',
                 'runs_per_key': 1,
                 'per_key': {k: {'role': wl[k]['role'], 'watch': wl[k]['regression_flag']}
                             for k in tw},
                 'why': 'alias-theme regression eyes: watch-lit must not stick on splash; '
                        'control-noop must be byte-identical; a lit theme-watch run doubles as its '
                        'regression run (moved out of lit-regression); lottery overlaps stay in lottery'},
                {'name': 'white-watch', 'priority': 3, 'keys_file': f'keys/{b}/white-watch.txt',
                 'runs_per_key': 1,
                 'why': 'white-window family without flaky evidence: one watch run each'},
                {'name': 'lottery', 'priority': 4, 'keys_file': f'keys/{b}/lottery.txt',
                 'runs_per_key': 6, 'consecutive_per_key': True, 'multiwin_check': True,
                 'per_key': {k: {'evidence': lottery_evidence[k],
                                 'theme_watch': {'role': wl[k]['role'], 'watch': wl[k]['regression_flag']}}
                             if k in theme_overlap_lottery else lottery_evidence[k] for k in lo},
                 'why': 'flaky keys only (registry or signed 0<k<n): x6 consecutive; doubles as regression'},
                {'name': 'lit-regression', 'priority': 5, 'keys_file': f'keys/{b}/lit-regression.txt',
                 'runs_per_key': 1,
                 'why': 'reference lit set minus lottery keys: verify no regression'},
            ]})

    doc = {
        'task': 'U15 stage-A observation key-table input for cx-t0', 'date': '2026-10-03',
        'lane': 'oc-t4', 'offline': True, 'board_deploy': False,
        'keys_this_is_input_not_a_full_board_run_plan': True,
        'reference_note': 'PLACEHOLDER: built against benchmark/2026-10-03-u14-reference (126 lit). '
                          'After U14 stage-A is signed, swap REF to the U15 reference and rebuild.',
        'input_root': '~/a2hlab/app-inputs',
        'batch_flags_base': ['--reinstall', '--hilog', '20', '--shots', '5,20', '--focus-check'],
        'window_limit_minutes': 45, 'stop_new_tests_by_minute': 35,
        'priority_order': ['movers', 'theme-watch (alias/theme regression eyes)', 'white-watch',
                           'lottery (flaky-only x6, doubles as regression)', 'lit-regression'],
        'boards': boards_doc,
        'manifest': '$WORKSPACES/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/apps.json',
    }
    (out / 'u15-stage-a-keys.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')

    # ---- known answers ----
    # (1) pairwise-disjoint: every key in exactly one shard per board
    shard_names = ('movers', 'theme-watch', 'white-watch', 'lottery', 'lit-regression')
    for b in ('5ea', '5cd', '61b'):
        seen = {}
        for sn in shard_names:
            for k in (out / f'keys/{b}/{sn}.txt').read_text().split():
                assert k not in seen, f'{k} in both {seen.get(k)} and {sn} on {b}'
                seen[k] = sn
    # (2) regression ∪ lit theme-watch ∪ lit lottery == reference lit; boards match
    union = []
    for b in ('5ea', '5cd', '61b'):
        union += (out / f'keys/{b}/lit-regression.txt').read_text().split()
    tw_all = {k for ks in theme_watch.values() for k in ks}
    lit_lottery = sorted(k for k in lottery_all if ref[k]['verdict'] == 'lit')
    lit_tw = sorted(k for k in tw_all if ref[k]['verdict'] == 'lit')
    ref_lit = sorted(k for k, e in ref.items() if e['verdict'] == 'lit')
    assert sorted(union + lit_lottery + lit_tw) == ref_lit, 'union != reference lit'
    for b in ('5ea', '5cd', '61b'):
        for k in (out / f'keys/{b}/lit-regression.txt').read_text().split():
            assert ref[k]['board'] == b
    for ks in lottery.values():
        for k in ks:
            assert k in lottery_evidence
    for b, bd in zip(('5ea', '5cd', '61b'), boards_doc):
        print(f"{b}: runs={bd['runs_total']} (movers={bd['breakdown']['movers']} "
              f"theme-watch={bd['breakdown']['theme_watch']} white-watch={bd['breakdown']['white_watch']} "
              f"lottery={bd['breakdown']['lottery_keys']}x6 lit-reg={bd['breakdown']['lit_regression']}) "
              f"~{bd['est_minutes_at_1.75min_per_run']}min windows={bd['windows_needed']}")
    print(f'shards pairwise disjoint OK; lit-regression({len(union)}) ∪ lit theme-watch({len(lit_tw)}) '
          f'∪ lit lottery({len(lit_lottery)}) == reference lit {len(ref_lit)} OK; boards match')
    print(f'lottery keys all evidenced: {sum(len(v) for v in lottery.values())}')
    print('u15-stage-a-keys.json sha256:',
          hashlib.sha256((out / 'u15-stage-a-keys.json').read_bytes()).hexdigest())
    return 0


if __name__ == '__main__':
    sys.exit(main())
