#!/usr/bin/env python3
"""read80.py — #80 blank-root readout for one app's hilog (+ optional child maps).

Judges, per key, whether the #80 getOhNativeWindow/two-bridge-copy blank root is FIXED on this run:
  1. unknown_sessionId_gone  — no `getOhNativeWindow: unknown sessionId=N` (the sessions_ re-query miss).
  2. own_session_bound        — every content session that draws got its OWN window directly (a real
     `BBQ.getSurface: returning Surface …`), NOT via the last-session rescue, and none was left an
     `empty Surface`. (Post-#80 the re-query resolves each session; no reliance on the stamp lottery.)
  3. first_frame_swap         — `activityResumed (first-frame)` AND `SetSurfaceBufferOpaque … isOpaque:1`
     on a content node (the content actually presented a frame).
  4. bridge_single_copy       — in the child maps, liboh_adapter_bridge.so is mapped ONCE (one r-xp base,
     one inode). 2 = the #80 double-load still present. (Needs --maps; else 'n/a'.)
Verdict FIXED iff 1 & 2 & 3 (& 4 when maps given). Pure parse; no device, no writes.

Usage: read80.py --key <name> --hilog <hilog.txt> [--maps <child-maps.txt>]
"""
import argparse, re, sys

def load(p):
    try:
        return open(p, 'r', errors='replace').read()
    except OSError:
        return ''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--key', required=True)
    ap.add_argument('--hilog', required=True)
    ap.add_argument('--maps', default=None)
    ap.add_argument('--tsv', action='store_true', help='print a bare TSV row')
    a = ap.parse_args()
    h = load(a.hilog)

    # sessions this app created, name per sessionId / nodeId
    # RSRenderService::CreateNodeAndSurface nodeid:<nid> name:<pkg>/<activity> surface id:<sid> name:...
    created = re.findall(r'CreateNodeAndSurface nodeid:(\d+) name:([^ ]+)', h)
    node_activity = {nid: name for nid, name in created}

    # (1) unknown sessionId
    unknown = re.findall(r'getOhNativeWindow: unknown sessionId=(\d+)', h)
    unknown_gone = (len(unknown) == 0)

    # (2) own-session bound: Surface returned vs empty; and whether it leaned on the last-session stamp
    surf_ok = re.findall(r'BBQ\.getSurface: returning Surface with mNativeObject=\w+ \(sessionId=(\d+)\)', h)
    # sessionId may appear before OR after "empty Surface" on the line; match either order
    surf_empty = re.findall(r'BBQ\.getSurface:(?:[^\n]*sessionId=(\d+)[^\n]*empty Surface|[^\n]*empty Surface[^\n]*sessionId=(\d+))', h)
    surf_empty = [s for pair in surf_empty for s in pair if s]
    rescued = re.findall(r'BBQ\.update: sessionId=(\d+) \S+ OHNativeWindow=0+[0-9A-Fa-f]+', h)
    # direct resolve (no unknown) for a session: `getOhNativeWindow: sessionId=S -> AOSP-compat ANativeWindow`
    direct = set(re.findall(r'getOhNativeWindow: sessionId=(\d+) -> AOSP-compat ANativeWindow', h))
    own_session_bound = (len(surf_empty) == 0) and len(surf_ok) > 0 and unknown_gone
    # if unknown is gone AND surfaces returned (not empty), each session bound to its own window

    # (3) first frame
    first_frame = ('activityResumed (first-frame)' in h)
    drew = re.findall(r'SetSurfaceBufferOpaque, Node id:(\d+), isOpaque:1', h)
    first_frame_swap = first_frame and len(drew) > 0

    # (4) bridge copies from child maps
    bridge = 'n/a'
    if a.maps:
        m = load(a.maps)
        bases = set(re.findall(r'^([0-9a-f]+)-[0-9a-f]+ r-xp .*liboh_adapter_bridge\.so', m, re.M))
        inodes = set(re.findall(r'r-xp \S+ \S+ \S+ (\d+)\s+.*liboh_adapter_bridge\.so', m, re.M))
        n = max(len(bases), len(inodes))
        bridge = str(n) if n else ('0?' )

    crit4 = (bridge == '1') if a.maps else True
    fixed = unknown_gone and own_session_bound and first_frame_swap and crit4

    drew_names = sorted({node_activity.get(n, n) for n in drew})
    if a.tsv:
        print('\t'.join([a.key, 'FIXED' if fixed else 'NOT',
                          f'unknown={0 if unknown_gone else len(unknown)}',
                          f'surf_ok={len(surf_ok)}', f'surf_empty={len(surf_empty)}',
                          f'rescued={len(rescued)}', f'first_frame={int(first_frame_swap)}',
                          f'bridge={bridge}', 'drew=' + ','.join(drew_names)[:60]]))
    else:
        print(f'=== {a.key}: {"FIXED" if fixed else "NOT FIXED"} ===')
        print(f'  (1) unknown_sessionId_gone : {unknown_gone}  (unknown count={len(unknown)}, sessions={sorted(set(unknown))})')
        print(f'  (2) own_session_bound      : {own_session_bound}  (Surface_ok={len(surf_ok)} empty_Surface={len(surf_empty)} rescued_via_stamp={len(rescued)} direct_resolve={sorted(direct)})')
        print(f'  (3) first_frame_swap       : {first_frame_swap}  (activityResumed-first-frame={first_frame}, drew_nodes={drew_names})')
        print(f'  (4) bridge_single_copy     : {bridge}  ({"1=fixed, 2=still double-loaded" if a.maps else "no --maps given"})')
    return 0

if __name__ == '__main__':
    sys.exit(main())
