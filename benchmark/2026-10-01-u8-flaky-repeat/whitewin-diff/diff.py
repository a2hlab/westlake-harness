#!/usr/bin/env python3
"""Per-key timeline across repeat runs; find first lit-vs-white divergence."""
import json, re, sys
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/lab'))
import lab_paths  # noqa: E402
BASE = lab_paths.workspaces() / 'westlake-harness-t4/benchmark/2026-10-01-u8-flaky-repeat'  # the runs live in oc-t4's worktree

def run_dirs(key):
    found = {}
    for r in ['r1', 'r2', 'r2b', 'r3', 'r4', 'r5']:
        for base in ['61b', '61b-cont']:
            d = BASE / base / r
            if not d.is_dir():
                continue
            hits = sorted(d.glob(f'*/61b0657200000000000000000324012c/{key}'))
            if hits:
                found[r] = hits[0]
    return found

EVENTS = [
    ('scene_create', re.compile(r'RSSurfaceNode::Create|WindowScene_\w+(\d+)|Create.*RSSurfaceNode|system_window_scene.*(Create|OnAttach)')),
    ('activity_resumed_ff', re.compile(r'activityResumed.*first.frame|FG deferred to first frame', re.I)),
    ('transition_done', re.compile(r'AbilityTransitionDone', re.I)),
    ('egl_surface', re.compile(r'eglCreateWindowSurface|createNativeWindowSurface|OHNativeWindow|setBufferGeometry', re.I)),
    ('buffer_event', re.compile(r'AcquireBuffer|buffer event|present frame|onDraw.*frame|Choreographer.*doFrame', re.I)),
    ('ability_start', re.compile(r'startAbility|onCreate.*MainActivity|performCreate', re.I)),
]

def timeline(path, key):
    events = {name: [] for name, _ in EVENTS}
    try:
        for n, line in enumerate(open(path / 'hilog.txt', encoding='utf-8', errors='replace'), 1):
            for name, pat in EVENTS:
                if pat.search(line):
                    ts = line.split()[1] if ' ' in line else ''
                    events[name].append({'line': n, 'ts': ts, 'text': line.strip()[:140]})
    except FileNotFoundError:
        return None
    return events

def main():
    keys = ['wikipedia', 'fd-noice']
    lit = {'wikipedia': ['r1', 'r2b', 'r3'], 'fd-noice': ['r1', 'r3', 'r4']}
    white = {'wikipedia': ['r2', 'r4', 'r5'], 'fd-noice': ['r2', 'r2b', 'r5']}
    out = {}
    for key in keys:
        dirs = run_dirs(key)
        per_round = {}
        for r, d in dirs.items():
            t = timeline(d, key)
            if t:
                per_round[r] = t
        out[key] = {
            'lit_rounds': lit[key], 'white_rounds': white[key],
            'dirs': {r: str(d) for r, d in dirs.items()},
            'events': {r: per_round.get(r) for r in sorted(set(lit[key] + white[key]))},
        }
    Path('/tmp/timeline.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for key in keys:
        print(f"=== {key} (lit {lit[key]} / white {white[key]})")
        for name, _ in EVENTS:
            counts = {r: len((out[key]['events'].get(r) or {}).get(name, [])) for r in sorted(out[key]['events'])}
            if any(v > 0 for v in counts.values()):
                print(f"  {name}: {counts}")

if __name__ == '__main__':
    main()
