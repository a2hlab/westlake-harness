#!/usr/bin/env python3
"""U13 first-fatal collection: every key not lit at U13 window 1, one row per run, two signatures per run.

    collect.py [--out-dir .]

Population   the 44 non-lit keys of the U13 signing reference (benchmark/2026-10-03-u13-reference/u13-ref-*.txt),
             minus the keys the U13 window-1 outer sign-off scored lit in every run (fd-noice, fd-uhabits), plus the
             lit-reference keys it scored dead (fd-fitness).
Source       U13 window 1 (westlake-harness-u7-executor/.../2026-10-03-u13-stage-a-plan/window1/u13-A1-*/<board>/runner/),
             when the key ran there; otherwise the key's latest U12 stage-A run
             (.../2026-10-02-u12-final-assembly/window{1..4}/.../runner/). 61b has no U13 run (window 2 adds it).
             Every row carries `generation` (u13 | u12) and the board's runtime jar from runtime-fingerprint.txt.
Signatures   the same as benchmark/2026-10-03-u12-predicted-vs-actual/compare.py (imported, not copied):
  terminal   cluster_first_cause.cluster_key() of first_fatal.py, normalised
  wall       the earliest WALL line of the target pids before the terminal; for bind_failed runs the wall is the
             innermost 'Caused by:' under '[B43-BIND] ensureBindApplication FAILED' (rule from bt-le-scancallback)
  bind       bind_status.py per run: bound | bind_failed | fatal_before_bind | unbound_at_capture
  near-fatal dlopen_failures.py --near-fatal 3 (libs that failed to load <=3 s before the first fatal line)
"""
import argparse
import glob
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import bind_status  # noqa: E402
import cluster_first_cause as cfc  # noqa: E402
import dlopen_failures  # noqa: E402
import lab_paths  # noqa: E402

spec = importlib.util.spec_from_file_location('u12cmp', REPO / 'benchmark/2026-10-03-u12-predicted-vs-actual/compare.py')
u12cmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u12cmp)

WS = lab_paths.workspaces()
EXE = WS / 'westlake-harness-u7-executor/benchmark'
U13 = EXE / '2026-10-03-u13-stage-a-plan/window1'
U12 = EXE / '2026-10-02-u12-final-assembly'
REF = REPO / 'benchmark/2026-10-03-u13-reference'
SIGNOFF = REPO / 'benchmark/2026-10-03-u13-stage-a-plan/window1-signoff/outer-signoff.json'
BOARDS = {'5ea': '5ea34a45', '5cd': '5cd1e3dd', '61b': '61b06572'}
REF_LINE = re.compile(r'^row \d+ col \d+\s+(\S+)\s+verdict=(\S+)')


def population():
    ref = {}
    for b in BOARDS:
        for line in open(REF / f'u13-ref-{b}.txt'):
            m = REF_LINE.match(line)
            if m:
                ref[m.group(1)] = (b, m.group(2))
    so = json.loads(SIGNOFF.read_text())['keys']
    keys = {k: {'board': b, 'u13_reference': v} for k, (b, v) in ref.items() if v != 'lit'}
    for k, v in so.items():
        if k in keys and v['runs'] and v['lit_runs'] == v['runs']:
            keys[k]['u13_window1'] = f"lit {v['k_of_n']}"
        elif v['reference'] == 'lit' and v['lit_runs'] < v['runs']:
            keys[k] = {'board': v['board'], 'u13_reference': 'lit', 'u13_window1': f"{v['verdicts']} {v['k_of_n']}"}
        elif k in keys:
            keys[k]['u13_window1'] = f"{'/'.join(v['verdicts'])} {v['k_of_n']}"
    return {k: v for k, v in keys.items() if not v.get('u13_window1', '').startswith('lit')}


def runs_of(key):
    u13 = sorted(p for p in glob.glob(str(U13 / 'u13-A1-*/*/runner/*/*/*' / Path(key) / 'record.json'))
                 if '/smoke/' not in p)
    if u13:
        return 'u13', [Path(p).parent for p in u13]
    u12 = sorted((Path(p).parent for p in glob.glob(str(U12 / 'window*/**/runner/*/*/*' / Path(key) / 'record.json'),
                                                  recursive=True) if '/smoke/' not in p),
                 key=lambda d: d.parent.parent.name)
    return ('u12', [u12[-1]]) if u12 else ('none', [])


def bind_of(d, text):
    if bind_status.BOUND in text:
        return 'bound', ''
    if bind_status.BIND_FAILED in text:
        tail = text[text.find(bind_status.BIND_FAILED):].splitlines()[1:80]
        causes = [l for l in tail if bind_status.CAUSED in l]
        return 'bind_failed', (causes[-1].split(bind_status.CAUSED, 1)[1].strip()[:300] if causes else '')
    if any(f in text for f in bind_status.FATALS):
        return 'fatal_before_bind', ''
    return 'unbound_at_capture', ''


def jar_of(d):
    fp = d.parent / 'runtime-fingerprint.txt'
    if not fp.exists():
        return ''
    return next((l.split()[0][:8] for l in fp.read_text().splitlines() if l.endswith('/oh-adapter-runtime.jar')), '')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out-dir', default=str(HERE))
    out = Path(ap.parse_args().out_dir)
    rows = []
    for key, meta in sorted(population().items()):
        gen, dirs = runs_of(key)
        for d in dirs:
            text = (d / 'hilog.txt').read_text(errors='replace') if (d / 'hilog.txt').exists() else ''
            ff = u12cmp.first_fatal(d)
            sig = cfc.cluster_key(ff)
            bind, bind_cause = bind_of(d, text)
            wall = bind_cause if bind == 'bind_failed' and bind_cause else u12cmp.earliest_wall(d, ff)
            near = [r['lib'] for r in dlopen_failures.scan([d], near_fatal_seconds=3) if r.get('near_fatal_keys')]
            rows.append({'key': key, **meta, 'generation': gen, 'runtime_jar': jar_of(d),
                         'terminal': u12cmp.norm(sig), 'terminal_kind': sig['kind'],
                         'terminal_cause': (sig['cause'] or '')[:240], 'terminal_frame': (sig.get('first_frame') or '')[:200],
                         'signal_thread': u12cmp.signal_thread(d, ff), 'wall': wall, 'wall_norm': u12cmp.wnorm(wall),
                         'wall_source': 'bind_failed_cause' if bind == 'bind_failed' and bind_cause else 'earliest_wall',
                         'bind': bind, 'near_fatal_dlopen': near, 'facts': u12cmp.run_facts_line(d, key),
                         'run': str(d).replace(str(WS), '$WORKSPACES')})
            print(key, gen, bind, sig['kind'], (sig['cause'] or '')[:70], '|', wall[:90], file=sys.stderr)
    (out / 'per-run.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
