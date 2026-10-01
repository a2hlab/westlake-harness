#!/usr/bin/env python3
"""Per-round app-event timeline; first lit-vs-white divergence."""
import json, re, sys
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/lab'))
import lab_paths  # noqa: E402
BASE = lab_paths.workspaces() / 'westlake-harness-t4/benchmark/2026-10-01-u8-flaky-repeat'  # the runs live in oc-t4's worktree

PATS = {
    'createSession': re.compile(r'createSession: success, sessionId=(\d+), surfaceNodeId=(\d+)'),
    'set_last_session': re.compile(r'oh_wm_set_last_session_local session=(\d+)'),
    'getOhNativeWindow_ok': re.compile(r'getOhNativeWindow.*(?:rc=0|-> AOSP-compat ANativeWindow=|SET_BUFFER_GEOMETRY.*rc=0)'),
    'getOhNativeWindow_fail': re.compile(r'getOhNativeWindow.*(?:returned null|unknown sessionId|rc=-|failed)'),
    'BBQ_create': re.compile(r'BBQ\.create name=VRI\[([^\]]+)\]'),
    'BBQ_update': re.compile(r'BBQ\.update: sessionId=(\d+).*OHNativeWindow=([0-9A-Fa-fx]+)'),
    'unknown_session': re.compile(r'unknown sessionId=(\d+)'),
    'EGL_surface': re.compile(r'eglCreateWindowSurface.*(?:success|surface=|rc=0)', re.I),
    'first_frame': re.compile(r'first-frame|OnDrawListener|first frame', re.I),
}

def run_dirs(key):
    found = {}
    for r in ['r1', 'r2', 'r2b', 'r3', 'r4', 'r5']:
        for base in ['61b', '61b-cont']:
            hits = sorted((BASE / base / r).glob(f'*/61b0657200000000000000000324012c/{key}'))
            if hits:
                found[r] = hits[0]
    return found

def extract(path):
    out = {k: [] for k in PATS}
    for n, line in enumerate(open(path / 'hilog.txt', encoding='utf-8', errors='replace'), 1):
        ts = line.split()[1] if len(line.split()) > 1 else ''
        for name, pat in PATS.items():
            m = pat.search(line)
            if m:
                out[name].append({'line': n, 'ts': ts, 'text': line.strip()[:180], 'groups': list(m.groups()) if m.groups() else None})
    return out

def main():
    keys = ['wikipedia', 'fd-noice']
    lit = {'wikipedia': ['r1', 'r2b', 'r3'], 'fd-noice': ['r1', 'r3', 'r4']}
    white = {'wikipedia': ['r2', 'r4', 'r5'], 'fd-noice': ['r2', 'r2b', 'r5']}
    result = {}
    for key in keys:
        dirs = run_dirs(key)
        rounds = {}
        for r, d in dirs.items():
            rounds[r] = extract(d)
        result[key] = {'lit': lit[key], 'white': white[key], 'dirs': {r: str(d) for r, d in dirs.items()}, 'rounds': rounds}
    Path('/tmp/tl.json').write_text(json.dumps(result, indent=1, ensure_ascii=False))

    for key in keys:
        print(f"\n{'='*60}\n{key}  lit={lit[key]} white={white[key]}\n{'='*60}")
        for name in PATS:
            counts = {r: len(result[key]['rounds'].get(r, {}).get(name, [])) for r in sorted(result[key]['rounds'])}
            if any(v > 0 for v in counts.values()):
                print(f"  {name}: {counts}")
        # sessions per round
        for r in sorted(result[key]['rounds']):
            evs = result[key]['rounds'][r]
            sessions = [e['groups'][0] for e in evs.get('createSession', []) if e['groups']]
            print(f"  {r}: sessions={sessions}")

if __name__ == '__main__':
    main()
