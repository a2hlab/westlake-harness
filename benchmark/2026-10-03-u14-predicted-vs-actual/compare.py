#!/usr/bin/env python3
"""U14 predicted vs actual: for the 13 non-lit keys clusters.csv assigns to U14, compare the predicted first-fatal
move against the U14 stage-A window-1 signed runs, then re-cluster the NEW first-fatals into a U17 candidate table.

    compare.py [--out-dir .] [--window1 <u14-A1 run root>] [--u13 <u13 window1 run root>]

Signatures are the exact U16 wall-cluster stack: this imports benchmark/2026-10-03-u16-wall-clusters/collect.py and
reuses its helpers (u12cmp.first_fatal + cfc.cluster_key for the terminal, u13ff.bind_of for bind status / bind cause,
u12cmp.earliest_wall, dlopen_failures.scan --near-fatal 3). The terminal (cfc.cluster_key -> u12cmp.norm) is the
clustering key; `earliest_wall` is kept only as context (it is a shared benign adapter line on this gen, e.g.
DisplayManagerProjectionProxy.dispatchDisplayEvent, present in lit runs too, so it is NOT the fatal).

Ground truth for lit/not is the outer window sign-off (screenshot), not the signature. Numbers come from facts.txt.
"""
import argparse
import collections
import csv
import glob
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]                      # westlake-harness(-wiki)
MASTER = REPO.parent / 'westlake-harness'   # clusters.csv/collect.py live on master
if not (MASTER / 'benchmark/2026-10-03-u16-wall-clusters/collect.py').exists():
    MASTER = REPO                           # same tree
WS = REPO.parent

# ---- import the U16 wall-cluster signature stack ----
spec = importlib.util.spec_from_file_location(
    'u16collect', MASTER / 'benchmark/2026-10-03-u16-wall-clusters/collect.py')
u16 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u16)
cfc, u12cmp, u13ff, dl = u16.cfc, u16.u12cmp, u16.u13ff, u16.dlopen_failures

CLUSTERS = MASTER / 'benchmark/2026-10-03-u16-wall-clusters/clusters.csv'
EXEC = WS / 'westlake-harness-u7-executor/benchmark'
U14_W1 = EXEC / '2026-10-03-u14-stage-a-plan/window1/u14-A1-r3-20261003T120358'
U13_W1 = EXEC / '2026-10-03-u13-stage-a-plan/window1'
U14_SIGNOFF = MASTER / 'benchmark/2026-10-03-u14-stage-a-plan/window1-signoff/outer-signoff.json'


def index_runs(root):
    idx = collections.defaultdict(list)
    for rj in glob.glob(str(Path(root) / '**/record.json'), recursive=True):
        d = Path(rj).parent
        if not (d / 'hilog.txt').exists():
            continue
        try:
            k = json.loads(Path(rj).read_text()).get('key')
        except Exception:
            continue
        if k:
            idx[k].append(d)
    return idx


import re
_FRAME = re.compile(r'#\d+ pc [0-9a-f]+ (?:/\S+/)?([\w.+\-]+\.so)\(([^)]*)\)')


def top_frame(ff):
    """Thread-correct crashing frame from first_fatal's fault-thread report (cfc.cluster_key leaves it empty for
    signals). Returns (pc0, 'lib.so(sym)') : pc0=True when the top frame is an unmapped pc=0 (the Impeller NULL-proc
    signature); the lib(sym) is the first real frame below it, with the per-app build-id and +offset stripped so the
    same wall in different apps clusters together (libflutter.so(<build-id>) -> libflutter.so)."""
    root = ff.get('root') if isinstance(ff, dict) else None
    frames = ((root or {}).get('report') or {}).get('frames') or []
    pc0 = False
    for fr in frames:
        msg = fr.get('message', '')
        if '#00 pc 0000000000000000' in msg or 'Not mapped' in msg:
            pc0 = True
            continue
        m = _FRAME.search(msg)
        if m:
            lib, inside = m.group(1), m.group(2).split('+')[0].strip()
            if re.fullmatch(r'[0-9a-f]{12,}', inside) or not inside:
                return pc0, lib                      # build-id / no symbol -> just the lib
            return pc0, f'{lib}({inside})'           # a real symbol -> keep it
    return pc0, ''


def sig_for(d):
    d = Path(d)
    text = (d / 'hilog.txt').read_text(errors='replace') if (d / 'hilog.txt').exists() else ''
    ff = u12cmp.first_fatal(d)
    sig = cfc.cluster_key(ff)
    bind, bc = u13ff.bind_of(d, text)
    wall = bc if bind == 'bind_failed' and bc else u12cmp.earliest_wall(d, ff)
    near = [r['lib'] for r in dl.scan([d], near_fatal_seconds=3) if r.get('near_fatal_keys')]
    pc0, frame = top_frame(ff)
    return dict(kind=sig['kind'], cause=(sig['cause'] or '')[:200], frame=frame, pc0=pc0,
                norm=u12cmp.norm(sig), wall=u12cmp.wnorm(wall), bind=bind, near=near,
                cmp=cmp_key(sig['kind'], sig, pc0, frame, bind, bc),
                facts=u12cmp.run_facts_line(d, d.name))


def cmp_key(kind, sig, pc0, frame, bind, bind_cause):
    """Kind-aware identity for 'moved/unchanged' and for re-clustering. Signals are identified by their crashing
    frame (not the signo line, which is identical across all SIGSEGVs); bind-failures by the bind cause; others by
    the normalized terminal cause."""
    if bind == 'bind_failed' and bind_cause:
        return f'bind_failed|{bind_cause[:80]}'
    if kind == 'signal':
        return f'signal|{"pc0->" if pc0 else ""}{frame or "unresolved"}'
    return u12cmp.norm(sig)


def owner_of_wall():
    """Known cluster owners keyed by a short wall token, to mark which new first-fatals are already assigned."""
    owners = {}
    for r in csv.DictReader(open(CLUSTERS)):
        owners[r['cluster']] = (r['owner'], r['name'])
    return owners


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out-dir', default=str(HERE))
    ap.add_argument('--window1', default=str(U14_W1))
    ap.add_argument('--u13', default=str(U13_W1))
    a = ap.parse_args()
    out = Path(a.out_dir)

    rows = list(csv.DictReader(open(CLUSTERS)))
    u14 = [r for r in rows if r['owner'] == 'U14']
    keys = [(r['cluster'], k, r) for r in u14 for k in r['keys'].split()]

    signoff_doc = json.loads(U14_SIGNOFF.read_text())
    signoff = signoff_doc['keys']
    gains = (signoff_doc.get('summary') or {}).get('gains') or {}   # authoritative "newly lit on U14"
    u14idx = index_runs(a.window1)
    u13idx = index_runs(a.u13)

    results = []
    for cluster, key, r in keys:
        pred_moves = int(r['predicted_first_fatal_moves'] or 0)
        # ground-truth lit = sign-off screenshot: summary.gains / reference=='lit' / outer_eyeball — NOT the
        # pair_sheet pre-screen lit_runs field (it was 0 for vlc/termux/dddmodel2 although they showed their own UI;
        # outer errata 88648a6eb9). lit_runs is read only as a post-errata tie-breaker.
        so = signoff.get(key, {})
        ref = so.get('reference')
        eyeball = so.get('outer_eyeball')
        gain = gains.get(key)
        is_lit = bool(gain) or ref == 'lit' or (so.get('lit_runs') or 0) > 0
        u14runs = u14idx.get(key, [])
        u13runs = u13idx.get(key, [])
        u14sig = sig_for(u14runs[0]) if u14runs else None
        u13sig = sig_for(u13runs[0]) if u13runs else None

        if not u14runs:
            verdict = 'pending-window2' if key not in signoff else 'no-run-window1'
        elif is_lit:
            verdict = 'lit'
        elif cluster == 'G':
            # z-order / alive-white: not a first-fatal move. judge by reference + whether still alive.
            verdict = ('still-white' if (ref or '').startswith('alive') or u14sig['kind'] in
                       ('no-observed-termination', 'alive') else 'regressed')
        else:
            # first-fatal clusters: moved if the U14 terminal identity (frame-aware) differs from U13's.
            if u13sig and u14sig and u14sig['cmp'] == u13sig['cmp']:
                verdict = 'unchanged'
            elif u14sig and u14sig['kind'] in ('no-observed-termination', 'alive'):
                verdict = 'moved-alive'           # past the wall, no new terminal observed
            else:
                verdict = 'moved'
        results.append(dict(
            cluster=cluster, key=key, predicted_moves=bool(pred_moves),
            prediction=r['name'][:120], picture=r['picture_prediction'][:120], confidence=r['confidence'],
            signoff_reference=ref, signoff_lit_runs=so.get('lit_runs'), signoff_gain=gain, signoff_eyeball=eyeball,
            lit=is_lit,
            u13_before={k: u13sig[k] for k in ('kind', 'cmp', 'cause', 'bind')} if u13sig else None,
            u14_actual=u14sig, verdict=verdict,
            new_first_fatal=(None if verdict == 'lit' else (u14sig['cmp'] if u14sig else None)),
            u14_runs=len(u14runs), u13_runs=len(u13runs)))

    # ---- re-cluster the NEW first-fatals of the moved/not-lit first-fatal keys ----
    def classify(nf):
        """Owner / category of a new wall, so only genuine unowned walls fall into the U17 table."""
        if 'libflutter' in nf or 'pc0->' in nf:
            return 'owned-U16', 'U16 flutter Impeller GLES-proc gap (u16-flutter-impeller-build / u16-flutter-egl-names A‴)'
        if nf.startswith('no-observed-termination'):
            return 'alive', 'alive past the wall, no new fatal -> screenshot/render question, not a first-fatal wall'
        if nf.startswith('process-disappeared'):
            return 'u17-unlocalized', 'moved, but the fatal cause was not captured (process vanished) -> U17 candidate needs a fuller dump to localize'
        return 'u17', 'unowned new wall -> U17 candidate (predicted: a fix moves these first-fatals)'
    buckets = collections.defaultdict(list)
    for x in results:
        if x['cluster'] == 'G' or x['verdict'] in ('lit', 'pending-window2', 'no-run-window1'):
            continue
        if x['verdict'] in ('unchanged', 'regressed'):
            continue  # not a new wall (stuck or worse)
        nf = x['new_first_fatal'] or '(none)'
        buckets[nf].append(x['key'])
    _order = {'u17-functional': 0, 'u17': 0, 'u17-unlocalized': 1, 'alive': 2, 'owned-U16': 3}
    u17 = []
    for nf, ks in buckets.items():
        cat, note = classify(nf)
        u17.append({'new_first_fatal': nf, 'keys_blocked': len(ks), 'keys': sorted(ks), 'category': cat, 'note': note})
    # termux is now lit (own terminal UI) but hit a FUNCTIONAL bootstrap wall behind the lit screen: it hardcodes
    # TERMUX_FILES_DIR=/data/data/com.termux/files, bypassing getFilesDir() (which fixDataDirs overrides to the real
    # /data/app/el2/<uid>/base/<pkg>); the sandbox bind of /data/data/<pkg> fails (host src absent on OH, APPSPAWN
    # errno:2) so the hardcoded path is empty -> bootstrap-install error dialog. DEX scan: only the Termux family
    # hardcodes this path (evidence/datadata-dex-scan.txt).
    u17.append({'new_first_fatal': 'termux bootstrap: hardcoded /data/data/<pkg>/files not present (getFilesDir bypassed)',
                'keys_blocked': 1, 'keys': ['termux'], 'category': 'u17-functional',
                'note': ('lit (own terminal UI) but functionally blocked: map the sandbox /data/data/<pkg> (and the '
                         '/data/user/0/<pkg> symlink) to the real dataDir /data/app/el2/<uid>/base/<pkg> instead of '
                         'bind-mounting the absent host /data/data/<pkg>, so hardcoded /data/data/<pkg>/files resolves. '
                         'Beneficiaries (DEX /data/data/<pkg> hardcoders, whole corpus): termux (+ com.termux.api if run); '
                         'no other corpus app hardcodes it (all use getFilesDir, already fixed).')})
    u17.sort(key=lambda b: (_order.get(b['category'], 9), -b['keys_blocked']))

    summary = collections.Counter(x['verdict'] for x in results)
    (out / 'predicted-vs-actual.json').write_text(json.dumps({
        'scope': 'U14 stage-A window1 (u14-A1-r3-20261003T120358); window2 u14-A2-20261003T131427 pending signoff',
        'u14_keys': len(results), 'verdict_counts': dict(summary),
        'rows': results, 'u17_candidate_new_walls': u17,
    }, indent=1, ensure_ascii=False) + '\n')

    # ---- u17-candidates.csv (ranked new walls; category marks owned/alive so the rest are the U17 table) ----
    with open(out / 'u17-candidates.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['rank', 'category', 'keys_blocked', 'new_first_fatal', 'keys', 'note'])
        for i, b in enumerate(u17, 1):
            w.writerow([i, b['category'], b['keys_blocked'], b['new_first_fatal'], ' '.join(b['keys']), b['note']])

    # console table
    print(f"{'CL':2} {'KEY':22} {'PRED-MOVE':9} {'VERDICT':15} NEW-FIRST-FATAL")
    print('-' * 100)
    for x in results:
        print(f"{x['cluster']:2} {x['key']:22} {str(x['predicted_moves']):9} {x['verdict']:15} "
              f"{(x['new_first_fatal'] or '')[:48]}")
    print('\nverdicts:', dict(summary))
    nc = collections.Counter(b['category'] for b in u17)
    print(f'new-wall buckets: {len(u17)}  categories={dict(nc)}')
    for b in u17:
        print(f"  [{b['keys_blocked']}] {b['category']:16} {b['new_first_fatal'][:46]}  <- {b['keys']}")


if __name__ == '__main__':
    main()
