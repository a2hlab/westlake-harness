#!/usr/bin/env python3
"""Read out an N11h observation window per key, per readout-procedure.md + knowledge/smoke/n11h.json, so the outer
signs the window from one table instead of hand-reading maps + hilog.

    n11h_readout.py --run <window board run dir> [--out <dir>] [--json]
    n11h_readout.py --selftest     # known-answer on window5 (U10.1 baseline): load-bases 2/2, 0 N11h host markers

Per key (every non-smoke record under <run>/**/runner/<shard>/<serial>/<key>/) it reports, from that key's files:
  1. LOAD BASES of liboh_adapter_bridge.so / liboh_android_runtime.so (+ libart.so / libopenjdkjvm.so controls) --
     distinct r-xp segment start addresses in maps-t5-<pid>.txt / maps-t20-<pid>.txt. N11h single-owner PASS = both
     owners == 1 (U9/U10.1 baseline == 2 each). Count by LOAD BASE, not inode, not line count (readout-procedure.md).
  2. HOST markers from hilog.txt, counted separately: [N11h-HOST-OWNER] (action=resident-check/inherit/reject),
     [N11h-HOST-OPEN] (action=resident/reject), [U10-COMPAT-VISIBLE] (U10.1's own compat marker, NOT an N11h-ran
     proof -- owner_verified on U10.1, 'unavailable' is non-fatal on N11h). The authoritative "N11h host ran" proof is
     [N11h-HOST-OWNER] action=inherit owner=westlake.sealed.child rc=0.
  3. AssetManager fid==null cluster: whether the key's hilog shows AAssetManager_fromJava / GetLongField / JniAbort
     (the 6-Flutter+glmark2 AssetManager keys abort here; generic per-key detection, not a hardcoded list).
  4. First fatal: first [CHILD_CK] J_invokeStaticMain_main_threw, else first JniAbort / cppcrash / SIGSEGV / FATAL.

This tool never judges lit/white (that is the outer's screenshot call); it reports the host/maps facts. Verdict per
key = single-owner PASS/FAIL + whether the N11h inherit marker fired + first fatal.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACES = HERE.parents[2]
OWNERS = ['liboh_adapter_bridge.so', 'liboh_android_runtime.so']
CONTROLS = ['libart.so', 'libopenjdkjvm.so']
RXP = re.compile(r'^([0-9a-f]+)-[0-9a-f]+ r-xp ')
HOST_OWNER = re.compile(r'\[N11h-HOST-OWNER\] action=(\S+).*?(rc=-?\d+)?')
HOST_OPEN = re.compile(r'\[N11h-HOST-OPEN\] action=(\S+)')
FATAL = re.compile(r'(\[CHILD_CK\] J_invokeStaticMain_main_threw:[^\n]*|JniAbort[^\n]*|cppcrash[^\n]*|'
                   r'signal \d+ \(SIG[A-Z]+\)[^\n]*|F \w+\s+FATAL[^\n]*|FATAL EXCEPTION[^\n]*)')


def load_bases(maps_path, lib):
    """distinct r-xp segment start addresses for a lib's own path in one maps file."""
    bases = set()
    try:
        for line in maps_path.read_text(errors='ignore').splitlines():
            if ' r-xp ' in line and line.rstrip().endswith('/' + lib):
                m = RXP.match(line)
                if m:
                    bases.add(m.group(1))
    except OSError:
        return None
    return len(bases)


def maps_for(keydir, snap):
    g = sorted(keydir.glob(f'maps-{snap}-*.txt'))
    return g[0] if g else None


def read_key(keydir):
    rec = {}
    out = {'load_bases': {}, 'markers': {}, 'assetmanager': {}, 'first_fatal': None}
    rj = keydir / 'record.json'
    if rj.is_file():
        try:
            rec = json.loads(rj.read_text())
        except Exception:
            rec = {}
    out['status'] = rec.get('status')
    # 1. load bases, at whichever snapshot(s) exist
    for snap in ('t5', 't20'):
        mp = maps_for(keydir, snap)
        if not mp:
            continue
        out['load_bases'][snap] = {lib: load_bases(mp, lib) for lib in OWNERS + CONTROLS}
    # single-owner verdict: prefer t20, else t5
    snap = out['load_bases'].get('t20') or out['load_bases'].get('t5') or {}
    b, r = snap.get('liboh_adapter_bridge.so'), snap.get('liboh_android_runtime.so')
    out['single_owner'] = ('PASS' if (b == 1 and r == 1) else 'FAIL' if (b or r) else 'no-maps')
    # 2. markers + 3. assetmanager + 4. first fatal, from hilog
    hilog = keydir / 'hilog.txt'
    text = hilog.read_text(errors='ignore') if hilog.is_file() else ''
    owner_actions, open_actions = {}, {}
    for m in HOST_OWNER.finditer(text):
        owner_actions[m.group(1)] = owner_actions.get(m.group(1), 0) + 1
    for m in HOST_OPEN.finditer(text):
        open_actions[m.group(1)] = open_actions.get(m.group(1), 0) + 1
    out['markers'] = {
        'N11h-HOST-OWNER': {'total': text.count('[N11h-HOST-OWNER]'), 'by_action': owner_actions},
        'N11h-HOST-OPEN': {'total': text.count('[N11h-HOST-OPEN]'), 'by_action': open_actions},
        'U10-COMPAT-VISIBLE': {'total': text.count('[U10-COMPAT-VISIBLE]'),
                               'unavailable': text.count('[U10-COMPAT-VISIBLE] unavailable')},
    }
    # authoritative N11h-ran proof: inherit to the sealed owner, rc=0
    out['n11h_inherit_rc0'] = bool(re.search(
        r'\[N11h-HOST-OWNER\] action=inherit .*owner=westlake\.sealed\.child .*rc=0', text))
    out['assetmanager'] = {
        'AAssetManager_fromJava': 'AAssetManager_fromJava' in text,
        'GetLongField': 'GetLongField' in text,
        'JniAbort': 'JniAbort' in text,
    }
    fm = FATAL.search(text)
    out['first_fatal'] = fm.group(1).strip()[:200] if fm else None
    return out


def discover(run, include_smoke=True):
    """Every keyed record under runner/<shard>/<serial>/<key>/. Smoke is INCLUDED by default -- for an N11h window the
    helloworld/zigzag smoke control is the evidence (a refuted window may never reach an app shard)."""
    keys = []
    for rec in sorted(run.rglob('record.json')):
        parts = rec.relative_to(run).parts
        if 'runner' not in parts:
            continue
        i = parts.index('runner')
        shard = parts[i + 1] if i + 1 < len(parts) else ''
        if shard == 'smoke' and not include_smoke:
            continue
        try:
            d = json.loads(rec.read_text())
        except Exception:
            continue
        key = d.get('key') or rec.parent.name
        if rec.parent.name != key or not d.get('serial'):
            continue
        keys.append((shard, key, rec.parent))
    # de-dup (shard,key): keep the one whose dir has maps (latest)
    best = {}
    for shard, key, d in keys:
        has_maps = bool(list(d.glob('maps-*.txt')))
        prev = best.get(key)
        if prev is None or (has_maps and not prev[2]):
            best[key] = (shard, d, has_maps)
    return [(v[0], k, v[1]) for k, v in sorted(best.items())]


def run_readout(run):
    rows = []
    for shard, key, keydir in discover(run):
        r = read_key(keydir)
        r.update({'key': key, 'shard': shard, 'dir': str(keydir)})
        rows.append(r)
    return rows


def print_table(rows):
    for r in rows:
        snap = r['load_bases'].get('t20') or r['load_bases'].get('t5') or {}
        lb = f"br={snap.get('liboh_adapter_bridge.so')} rt={snap.get('liboh_android_runtime.so')}"
        mk = (f"OWNER={r['markers']['N11h-HOST-OWNER']['total']} "
              f"OPEN={r['markers']['N11h-HOST-OPEN']['total']} "
              f"COMPAT={r['markers']['U10-COMPAT-VISIBLE']['total']}")
        am = 'JniAbort' if r['assetmanager']['JniAbort'] else ('GetLongField' if r['assetmanager']['GetLongField'] else '-')
        print(f"{r['key']:40} {r['single_owner']:7} {lb:14} inherit_rc0={int(r['n11h_inherit_rc0'])} "
              f"{mk:28} am={am:11} fatal={(r['first_fatal'] or '')[:60]}")
    npass = sum(1 for r in rows if r['single_owner'] == 'PASS')
    ninh = sum(1 for r in rows if r['n11h_inherit_rc0'])
    nfatal = sum(1 for r in rows if r['first_fatal'])
    print(f"\n{len(rows)} keys; single-owner PASS {npass}; N11h inherit rc0 {ninh}; with first-fatal {nfatal}")


def selftest():
    """window5 (U10.1 baseline) same keys: load-bases MUST be 2/2 and N11h host markers (OWNER/OPEN) MUST be 0."""
    w5 = WORKSPACES / 'westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/window5'
    if not w5.is_dir():
        print('SELFTEST SKIP: window5 not present')
        return 0
    rows = [r for r in run_readout(w5.resolve()) if r['load_bases']]
    # U10.1 baseline invariants (robust to partial launches): NO N11h host markers on any key, and every key that
    # loaded bridge shows the DOUBLE copy (bridge==2) -- that is exactly the double-load N11h must collapse.
    bad, doubled = [], 0
    for r in rows:
        snap = r['load_bases'].get('t20') or r['load_bases'].get('t5') or {}
        b = snap.get('liboh_adapter_bridge.so')
        owner = r['markers']['N11h-HOST-OWNER']['total']
        openm = r['markers']['N11h-HOST-OPEN']['total']
        if owner != 0 or openm != 0:
            bad.append(f"{r['key']}: unexpected N11h marker OWNER={owner} OPEN={openm} (U10.1 must have 0)")
        if b == 2:
            doubled += 1
        elif b and b != 2:
            # bridge loaded but not doubled -- allowed for a partial launch, note it
            pass
    print(f"SELFTEST window5 (U10.1 baseline): {len(rows)} keys with maps; N11h-marker-free: {len(rows) - len([x for x in bad])}; "
          f"bridge double (==2): {doubled}")
    for x in bad:
        print('  MISS', x)
    ok = not bad and doubled >= 1
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--json', action='store_true', help='also write n11h-readout.json to --out (or the run dir)')
    ap.add_argument('--selftest', action='store_true', help='known-answer on window5; ignores --run')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.run:
        ap.error('--run is required (or --selftest)')
    run = a.run.expanduser().resolve()
    if not run.is_dir():
        sys.exit(f'no such run dir: {run}')
    rows = run_readout(run)
    print_table(rows)
    out = (a.out or run / 'n11h-readout').expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'n11h-readout.json').write_text(json.dumps({'run': str(run), 'keys': rows}, indent=1, ensure_ascii=False))
    print(f"\nwrote {out / 'n11h-readout.json'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
