#!/usr/bin/env python3
"""Reduce one Android reference run (runs/<TAG>/) to numbers.

Clocks: drive.log stamps are CLOCK_REALTIME; screenrecord's Winscope V2 track
stores the realtime->elapsed offset and per-frame elapsed ns; atrace uses the
boot clock and ViewRootImpl's eventTimeNano is CLOCK_MONOTONIC. On this phone
(never suspended, stay-on while plugged) V1 monotonic and V2 elapsed differ by
<1 us, so all four land on one axis.
"""
import json, re, struct, subprocess, sys
from pathlib import Path

import numpy as np

W, H, SCALE = 120, 192, 10          # decoded frame size; 1200x1920 / 10
FEED_ROWS = (24, 170)                # y 240..1700: feed list above bottom nav
FEED_THR = 3.0                       # mean |diff| on 0..255 grey
CONTENT_STD = 30.0                   # see visual()


def winscope(mp4):
    d = mp4.read_bytes()
    o = d.find(b'#VV1NSC0PET1ME2#') + 16
    ver, off = struct.unpack_from('<Iq', d, o)
    n = struct.unpack_from('<I', d, o + 12)[0]
    ts = struct.unpack_from('<%dQ' % n, d, o + 16)
    return off / 1e9, np.array(ts, dtype=np.float64) / 1e9


def frames(mp4):
    raw = subprocess.run(
        ['ffmpeg', '-loglevel', 'error', '-i', str(mp4), '-fps_mode', 'passthrough',
         '-vf', f'scale={W}:{H},format=gray', '-f', 'rawvideo', '-'],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)


def drive(path):
    ev = []
    for line in path.read_text().splitlines():
        p = line.split()
        if p[0].startswith('TAP_'):
            ev.append({'name': p[0][4:], 'x': int(p[1]), 'y': int(p[2]), 'real': float(p[3])})
        elif p[0] in ('LAUNCH', 'LAUNCHED', 'GFX_RESET', 'END', 'DISMISS_PERM'):
            ev.append({'name': p[0], 'real': float(p[1])})
    return ev


LINE = re.compile(r'^\s*(.*?)-(\d+)\s+\(\s*([\d-]+)\)\s+\[\d+\]\s+\S+\s+([\d.]+): tracing_mark_write: (.*)$')


def atrace(path, pid):
    """Main-thread (tid==pid) top-level slices and deliverInputEvent begins."""
    stack, top, deliver = [], [], []
    for line in path.open(errors='replace'):
        m = LINE.match(line)
        if not m or int(m.group(2)) != pid:
            continue
        ts, msg = float(m.group(4)), m.group(5)
        if msg.startswith('B|'):
            name = msg.split('|', 2)[2] if msg.count('|') >= 2 else ''
            stack.append((name, ts))
            if name.startswith('deliverInputEvent src='):
                et = re.search(r'eventTimeNano=(\d+)', name)
                deliver.append({'begin': ts, 'event_time': int(et.group(1)) / 1e9 if et else None,
                                'depth': len(stack) - 1})
        elif msg.startswith('E|') and stack:
            name, t0 = stack.pop()
            if not stack:
                top.append({'name': name, 'begin': t0, 'dur': ts - t0})
    return top, deliver


def logcat_jank(path, pid):
    skipped, davey = [], []
    for line in path.open(errors='replace'):
        p = line.split(None, 5)
        if len(p) < 6 or p[1] != str(pid):
            continue
        m = re.search(r'Skipped (\d+) frames', line)
        if m:
            skipped.append((float(p[0]), int(m.group(1)), p[2] == str(pid)))
        m = re.search(r'Davey! duration=(\d+)ms', line)
        if m:
            davey.append((float(p[0]), int(m.group(1))))
    return skipped, davey


GFX_KEYS = ['Total frames rendered', 'Janky frames', 'Janky frames (legacy)', '50th percentile',
            '90th percentile', '95th percentile', '99th percentile', 'Number Missed Vsync',
            'Number High input latency', 'Number Slow UI thread', 'Number Slow bitmap uploads',
            'Number Slow issue draw commands', 'Number Frame deadline missed']


def gfxinfo(path):
    out, text = {}, path.read_text(errors='replace')
    for k in GFX_KEYS:
        m = re.search(r'^' + re.escape(k) + r': (.*)$', text, re.M)
        if m:
            out[k] = m.group(1).strip()
    return out


def img_formats(path):
    counts, big = {}, {}
    for line in path.read_text().splitlines():
        p = line.split()
        if len(p) < 3:
            continue
        b = bytes.fromhex(p[2])
        k = ('heic' if b[4:12] == b'ftypheic' else 'avif' if b[4:12] == b'ftypavif'
             else 'isobmff:' + b[8:12].decode('latin1') if b[4:8] == b'ftyp'
             else 'webp' if b[8:12] == b'WEBP' else 'png' if b[1:4] == b'PNG'
             else 'gif' if b[:3] == b'GIF' else 'jpeg' if b[:2] == b'\xff\xd8' else 'other')
        counts[k] = counts.get(k, 0) + 1
        if int(p[1]) >= 15000:   # feed-card sized payloads
            big[k] = big.get(k, 0) + 1
    return counts, big


def visual(fr, ft, t_tap, t_next):
    """Tap -> feed page switched (any change) and -> first frame with content.

    The feed region of a category that is still loading is a near-uniform white
    page (grey std ~0.3) or a skeleton (std 13-22); a page with real items has
    std 56-85, the text-only hot list (热榜) ~35. So content = first frame after
    the tap whose feed region both differs from the pre-tap frame and has
    std > CONTENT_STD.
    """
    i0 = int(np.searchsorted(ft, t_tap)) - 1
    F = slice(*FEED_ROWS)
    base = fr[i0, F]
    switch = content = None
    for i in range(i0 + 1, len(ft)):
        if ft[i] >= t_next:
            break
        if np.abs(fr[i, F] - base).mean() <= FEED_THR:
            continue
        switch = ft[i] if switch is None else switch
        if fr[i, F].std() > CONTENT_STD:
            content = ft[i]
            break
    ms = lambda t: None if t is None else round((t - t_tap) * 1000)
    return {'switch_ms': ms(switch), 'content_ms': ms(content)}


def main(run):
    run = Path(run)
    pid = int(re.search(r'APP_PID (\d+)', (run / 'meta.txt').read_text()).group(1))
    off, ft = winscope(run / 'screen.mp4')
    fr = frames(run / 'screen.mp4')
    assert len(fr) == len(ft), (len(fr), len(ft))
    ev = drive(run / 'drive.log')
    for e in ev:
        e['el'] = e['real'] - off
    t_launch = next(e['el'] for e in ev if e['name'] == 'LAUNCH')
    top, deliver = atrace(run / 'atrace.txt', pid)
    taps = [e for e in ev if 'x' in e]
    out = {'run': run.name, 'pid': pid, 'frames': len(ft),
           'am_start': dict(re.findall(r'^(LaunchState|TotalTime|WaitTime): (\S+)', (run / 'amstart.txt').read_text(), re.M)),
           'taps': []}
    for k, e in enumerate(taps):
        t_next = taps[k + 1]['el'] if k + 1 < len(taps) else e['el'] + 7.5
        # first main-thread deliverInputEvent whose event was generated after the tap command
        d = [x for x in deliver if x['event_time'] and e['el'] - 0.05 <= x['event_time'] < t_next]
        row = {'name': e['name'], 't_since_launch_s': round(e['el'] - t_launch, 2)}
        if d:
            row['inject_to_main_ms'] = round((d[0]['begin'] - d[0]['event_time']) * 1000, 1)
            row['tapcmd_to_main_ms'] = round((d[0]['begin'] - e['el']) * 1000, 1)
            row['events_on_main'] = len(d)
        if e['name'] != 'consent':
            row.update(visual(fr, ft, e['el'], t_next))
        out['taps'].append(row)
    t_reset = next(e['el'] for e in ev if e['name'] == 'GFX_RESET')
    t_end = next(e['el'] for e in ev if e['name'] == 'END')
    for label, lo, hi in (('launch', t_launch, t_reset), ('taps', t_reset, t_end)):
        s = [x for x in top if lo <= x['begin'] < hi]
        long_ = sorted((x for x in s if x['dur'] >= 0.1), key=lambda x: -x['dur'])
        out['main_' + label] = {
            'slices_ge_100ms': len(long_), 'slices_ge_500ms': sum(x['dur'] >= 0.5 for x in long_),
            'busy_in_ge_100ms_s': round(sum(x['dur'] for x in long_), 2),
            'top': [{'name': x['name'][:90], 'ms': round(x['dur'] * 1000), 't_since_launch_s': round(x['begin'] - t_launch, 2)}
                    for x in long_[:6]]}
    skipped, davey = logcat_jank(run / 'logcat.txt', pid)
    t_reset_real = t_reset + off
    out['choreographer_skipped'] = {
        'launch': [n for t, n, _ in skipped if t < t_reset_real],
        'taps': [n for t, n, _ in skipped if t >= t_reset_real]}
    out['davey_ms'] = {'launch': [n for t, n in davey if t < t_reset_real],
                       'taps': [n for t, n in davey if t >= t_reset_real]}
    out['gfxinfo'] = {'launch': gfxinfo(run / 'gfx_launch.txt'), 'taps': gfxinfo(run / 'gfx_taps.txt')}
    maps = (run / 'native-maps.txt').read_text()
    out['native'] = {
        'metasec_paths': sorted(set(re.findall(r'(/\S*libmetasec_ml\.so)', maps.split('---')[0]))),
        'app_lib_dir': 'app_lib ' in maps or '/app_lib\n' in maps,
        'data_dir_hits': [l for l in maps.split('---')[1].splitlines() if l.strip()]}
    counts, big = img_formats(run / 'imgmagic.txt')
    out['image_cache'] = {'all': counts, 'ge_15KB': big}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
