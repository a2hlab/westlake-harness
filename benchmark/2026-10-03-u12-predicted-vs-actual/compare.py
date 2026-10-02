#!/usr/bin/env python3
"""U12 stage A: predicted vs actual first-fatal moves, per key, for the 51 keys of the U12 prediction table.

    compare.py [--out-dir .]

Inputs
  prediction  benchmark/2026-10-02-u12-prediction-table/u12-predictions.csv (any_predicted_mover yes/no, owners)
  U10.1T8     benchmark/2026-10-02-candidate-first-fatal-clusters/first-fatal.json (stage-A window 5, the same 51 keys,
              first_fatal.py) + its sources.json
  U12         every non-smoke run of these keys under westlake-harness-u7-executor/.../2026-10-02-u12-final-assembly/
              window{1..4} (record.json present), first_fatal.py run here on each; the board's runtime-fingerprint.txt
              runtime jar is recorded (U12 = 0482c9b1)
  screens     outer sign-offs: window{1,2,3}-signoff/outer-signoff.json (master); window 4 has no sign-off file yet --
              the only outer window-4 verdict on the board is fd-client (ACK 2026-10-03T00:58:37: new lit). Every other
              window-4 screen is reported `unsigned` with run_facts' shots/alive, never as lit/white.
Comparison, two signatures per run, normalised (pids, tids, addresses, numbers -> #):
  terminal   cluster_first_cause.cluster_key() of first_fatal.py (the termination and its innermost Java cause)
  wall       the earliest WALL line (linker/ULE/abort/missing-class/method) of the target pids before the terminal
             (whole log when nothing terminated), skipping lines whose signature is in the benign registry
             (knowledge/gates/benign-log-signatures.json) and the [COROUTINE-FIX] CoroutineStart probe. A terminal that is only the consequence (mcdonalds' DI NPE,
             a bare SIGABRT, "process disappeared") keeps its signature while the wall under it changes.
  moved      terminal OR wall differs from U10.1T8 in at least one U12 run (all runs listed; which one moved is kept)
  same       both equal in every U12 run
  not-run    no U12 run of the key
Score (keys with a U12 run): predicted&moved, predicted&not-moved, unpredicted&moved, unpredicted&not-moved.
"""
import argparse
import csv
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import cluster_first_cause as cfc  # noqa: E402
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
PRED = REPO / 'benchmark/2026-10-02-u12-prediction-table/u12-predictions.csv'
BASE = REPO / 'benchmark/2026-10-02-candidate-first-fatal-clusters'
U12 = WS / 'westlake-harness-u7-executor/benchmark/2026-10-02-u12-final-assembly'
SIGN = WS / 'westlake-harness/benchmark/2026-10-02-u12-final-assembly'
W4_OUTER = {'fd-client': 'lit (new): own onboarding page; ACK 2026-10-03T00:58:37 (U10.1T8: dead)'}


def norm(sig):
    def n(s):
        s = re.sub(r'0x[0-9a-fA-F]+', '#', s or '')
        s = re.sub(r'\d+', '#', s)
        return s.strip()
    return f"{sig['kind']}|{n(sig['cause'])[:160]}|{n(sig.get('first_frame') or '')[:120]}"


WALL = re.compile(r'UnsatisfiedLinkError|dlopen(?:_ns)? failed|cannot locate symbol|UNSUPPORTED-SYMBOL|F02-A1\d|'
                  r'Abort message|FORTIFY|CHECK failed|NoSuchMethodError|NoClassDefFoundError|'
                  r'ClassNotFoundException|ExceptionInInitializerError|NoSuchFieldError')
LINE = re.compile(r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+(\S+?):\s?(.*)$')
BENIGN = {e['signature'] for e in json.loads((REPO / 'knowledge/gates/benign-log-signatures.json').read_text())['signatures']}


def bnorm(message):
    message = re.sub(r'\b0x[0-9a-fA-F]{8,}\b', '<address>', message)
    message = re.sub(r'@[0-9a-fA-F]{6,}\b', '@<address>', message)
    message = re.sub(r'\b[0-9a-fA-F]{12,16}\b', '<address>', message)
    return re.sub(r'\b(?:pid|tid)[=: ]+\d+\b', '<thread-id>', message, flags=re.I)


def earliest_wall(run_dir, ff):
    pids = {str(p) for p in ff.get('target_pids') or []}
    stop = ((ff.get('terminal') or {}).get('event') or {}).get('line') or 10 ** 9
    if not pids:
        return ''
    for n, line in enumerate(open(Path(run_dir) / 'hilog.txt', errors='replace'), 1):
        if n > stop:
            break
        m = LINE.match(line.rstrip('\n'))
        if not m or m.group(2) not in pids:
            continue
        msg = m.group(6)
        if not WALL.search(msg):
            continue
        if f'{m.group(5)}|{m.group(4)}|{bnorm(msg)}' in BENIGN or 'kotlinx.coroutines.CoroutineStart' in msg:
            continue  # the [COROUTINE-FIX] probe's CNFE is in every process (benign U5-BENIGN-017 family)
        return msg.removeprefix('[stderr] ').strip()[:400]
    return ''


def wnorm(s):
    s = re.sub(r'0x[0-9a-fA-F]+', '#', s or '')
    s = re.sub(r'\d+', '#', s)
    return s.strip()[:400]


def signal_thread(run_dir, ff):
    t = (ff.get('terminal') or {})
    if t.get('kind') != 'signal':
        return ''
    line = (t.get('event') or {}).get('line') or 0
    with open(Path(run_dir) / 'hilog.txt', errors='replace') as fh:
        for n, text in enumerate(fh, 1):
            if line <= n <= line + 3 and 'threadName(' in text:
                return text.split('threadName(', 1)[1].split(')')[0]
            if n > line + 3:
                break
    return ''


def first_fatal(d):
    r = subprocess.run([sys.executable, str(REPO / 'scripts/lab/first_fatal.py'), str(d)], capture_output=True,
                       text=True, timeout=900)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {'status': 'unknown', 'error': (r.stderr or r.stdout)[-300:]}


def signoffs():
    out = {}
    for w in (1, 2, 3):
        f = SIGN / f'window{w}-signoff/outer-signoff.json'
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        for k, v in d.get('keys', {}).items():
            vs = v if isinstance(v, list) else [v]
            out.setdefault(k, []).extend(f"w{w}:{x.get('window', x) if isinstance(x, dict) else x}" for x in vs)
        for k, v in (d.get('unlit_measured') or {}).items():
            out.setdefault(k, []).append(f'w{w}:{v}')
    return out


def run_facts_line(d, key):
    r = subprocess.run([sys.executable, str(REPO / 'scripts/lab/run_facts.py'), str(d.parent)], capture_output=True,
                       text=True)
    for line in r.stdout.splitlines():
        if line.split()[:1] == [key]:
            return ' '.join(line.split()[1:])
    return ''


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out-dir', default=str(HERE))
    a = ap.parse_args()
    out = Path(a.out_dir)
    pred = {r['key']: r for r in csv.DictReader(open(PRED))}
    base = json.loads((BASE / 'first-fatal.json').read_text())
    base_src = json.loads((BASE / 'sources.json').read_text())
    signs = signoffs()
    u12_ff, rows = {}, []
    for k in sorted(pred):
        b = base.get(k)
        bsig = norm(cfc.cluster_key(b)) if b else ''
        bdir = Path(base_src[k].replace('$WORKSPACES', str(WS))) if k in base_src else None
        bwall = earliest_wall(bdir, b) if (b and bdir) else ''
        bthread = signal_thread(bdir, b) if (b and bdir) else ''
        runs = []
        for rec in sorted(glob.glob(str(U12 / 'window*/**/runner/*/*/*/' / k / 'record.json'), recursive=True)):
            if '/smoke/' in rec:
                continue
            d = Path(rec).parent
            if not (d / 'hilog.txt').exists():
                continue
            ff = first_fatal(d)
            w = next(p for p in d.parts if p.startswith('window'))
            u12_ff[f'{k}@{w}@{d.parent.name[:4]}'] = ff
            jar = ''
            fp = d.parent / 'runtime-fingerprint.txt'
            if fp.exists():
                jar = next((l.split()[0][:8] for l in fp.read_text().splitlines()
                            if l.endswith('/oh-adapter-runtime.jar')), '')
            sig = cfc.cluster_key(ff)
            wall = earliest_wall(d, ff)
            sthread = signal_thread(d, ff)
            runs.append({'window': w, 'board': d.parent.name[:3], 'runtime_jar': jar, 'sig': norm(sig),
                         'wall': wall, 'signal_thread': sthread,
                         'terminal_moved': norm(sig) != bsig or (bool(bthread) and sthread != bthread), 'wall_moved': wnorm(wall) != wnorm(bwall),
                         'kind': sig['kind'], 'cause': (sig['cause'] or '')[:200],
                         'frame': (sig.get('first_frame') or '')[:160], 'facts': run_facts_line(d, k),
                         'run': str(d).replace(str(WS), '$WORKSPACES')})
        if not runs:
            actual = 'not-run'
        elif any(r['terminal_moved'] or r['wall_moved'] for r in runs):
            actual = 'moved'
        else:
            actual = 'same'
        screens = list(signs.get(k, []))
        if any(r['window'] == 'window4' for r in runs):
            screens.append('w4:' + W4_OUTER.get(k, 'unsigned (' + '; '.join(r['facts'] for r in runs
                                                                            if r['window'] == 'window4') + ')'))
        bk = cfc.cluster_key(b) if b else {'kind': 'none', 'cause': '', 'first_frame': ''}
        rows.append({'key': k, 'predicted_mover': pred[k]['any_predicted_mover'], 'owners': pred[k]['owners'],
                     'predicted_by': ';'.join(c for c in ('java_fix', 'mediandk', 'icu', 'disappeared', 'sigabrt',
                                                          'n11h_family') if pred[k].get(c)),
                     'u10_1t8_kind': bk['kind'], 'u10_1t8_cause': (bk['cause'] or '')[:200],
                     'u10_1t8_frame': (bk.get('first_frame') or '')[:160],
                     'u10_1t8_wall': bwall, 'u10_1t8_signal_thread': bthread, 'u10_1t8_run': base_src.get(k, ''), 'actual': actual,
                     'moved_by': ','.join(sorted({('terminal' if r['terminal_moved'] else '') + ('+wall' if r['wall_moved'] else '')
                                                  for r in runs} - {''})), 'u12_runs': runs, 'screens': screens})
    # context / noise_context are the bulky +-lines around the terminal; cluster_key() needs only these fields
    keep = ('status', 'target_pids', 'terminal', 'root', 'later_terminals', 'key', 'package', 'source', 'registry_sha256')
    u12_ff = {k: {x: v.get(x) for x in keep} for k, v in u12_ff.items()}
    (out / 'u12-first-fatal.json').write_text(json.dumps(u12_ff, indent=1, ensure_ascii=False))
    c = subprocess.run([sys.executable, str(REPO / 'scripts/lab/cluster_first_cause.py'), str(out / 'u12-first-fatal.json')],
                       capture_output=True, text=True)
    (out / 'u12-clusters.json').write_text(c.stdout)
    (out / 'per-key.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    with open(out / 'per-key.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['key', 'predicted_mover', 'predicted_by', 'actual', 'moved_by', 'u10_1t8_first_fatal',
                    'u10_1t8_wall', 'u12_first_fatal', 'u12_wall', 'u12_windows', 'screens'])
        for r in rows:
            u12 = ' || '.join(sorted({f"{x['kind']}: {x['cause'][:120]} @ {x['frame'][:80]}" for x in r['u12_runs']}))
            u12w = ' || '.join(sorted({x['wall'][:160] for x in r['u12_runs']}))
            w.writerow([r['key'], r['predicted_mover'], r['predicted_by'], r['actual'], r['moved_by'],
                        f"{r['u10_1t8_kind']}: {r['u10_1t8_cause'][:120]} @ {r['u10_1t8_frame'][:80]}",
                        r['u10_1t8_wall'][:160], u12, u12w,
                        ' '.join(f"{x['window']}/{x['board']}" for x in r['u12_runs']), ' | '.join(r['screens'])])
    ran = [r for r in rows if r['actual'] != 'not-run']
    score = {
        'keys': len(rows), 'ran_in_u12': len(ran), 'not_run': len(rows) - len(ran),
        'predicted_and_moved': sum(1 for r in ran if r['predicted_mover'] == 'yes' and r['actual'] == 'moved'),
        'predicted_not_moved': sum(1 for r in ran if r['predicted_mover'] == 'yes' and r['actual'] == 'same'),
        'unpredicted_moved': sum(1 for r in ran if r['predicted_mover'] != 'yes' and r['actual'] == 'moved'),
        'unpredicted_same': sum(1 for r in ran if r['predicted_mover'] != 'yes' and r['actual'] == 'same'),
        'predicted_not_run': sum(1 for r in rows if r['predicted_mover'] == 'yes' and r['actual'] == 'not-run'),
    }
    (out / 'score.json').write_text(json.dumps(score, indent=1))
    print(json.dumps(score))
    for r in rows:
        print(f"{r['key']:40s} pred={r['predicted_mover']:3s} actual={r['actual']:7s} by={r['moved_by']:14s} runs={len(r['u12_runs'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
