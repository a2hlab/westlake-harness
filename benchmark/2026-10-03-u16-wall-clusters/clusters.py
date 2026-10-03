#!/usr/bin/env python3
"""U16 wall clusters, step 2: per-key first fatal -> clusters, owner (U14 / U15 / none), predicted first-fatal moves.

    clusters.py   (reads per-run.json from collect.py)  -> clusters.csv, per-key.csv

Each key is assigned by its first fatal from per-run.json (terminal, or the wall when the terminal is a consequence:
process disappeared, bind_failed, J_invokeStaticMain wrapper). Alive keys without a fatal are assigned by their
window-level mechanism (2026-10-03-white-residual-u13, cae186de0f). Every assignment names its evidence; the script
checks that the named signature really is in that key's per-run row, so the table cannot drift from the data.
Owners are the U14 / U15 deliverables in benchmark/ (dir named per cluster). `moves` = predicted number of keys
whose first fatal moves (alive-without-fatal keys: 0 by definition; their t20 picture prediction is in `picture`).
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# cluster id, name, owner, owner deliverable(s), moves, picture, confidence, [(key, signature substring that must be in
# the key's per-run row: terminal_cause / wall / terminal_kind / signal_thread / verdicts)]
CLUSTERS = [
    ('A', 'Flutter raster SIGSEGV: libflutter eglCreateWindowSurface binds platform libEGL with the AdapterAnw wrapper',
     'U14', 'u14-flutter-libandroid (fff9be31; carried by u15-flutter-libandroid-v2 9b824502)', 4,
     'past eglCreateWindowSurface; next wall unknown (libre: libmpv -> libmediandk.so Xpm mmap EINVAL, caught)', 'high',
     [('localsend', '1.raster'), ('fd-kitchenowl', '1.raster'), ('fd-fluffychat', '1.raster'), ('fd-libre', '1.raster')]),
    ('B', 'M2 full-screen WebView (typed zero WebView provider), alive white/black, no fatal',
     'none', 'route a in 2026-10-03-m2-webview-roadmap; A0 probe window 2 pending (2026-10-03-m2-a0-probe)', 0,
     'white -> own content only with a real WebView (route a: 2 after A1, 4 after A2; jiten keeps its own M5 dialog)', '-',
     [('cv2-ca-vaults-randomlydie', 'alive-white-window'), ('cv2-com-paultirk-yatoo', 'alive-white-window'),
      ('cv2-dev-obfusk-jiten-webview', 'alive-white-window'), ('cv2-timur-webrtc-check', 'alive-black-window')]),
    ('C', 'bionic `_ctype_` not found (Realm) in the native domain, bind fails',
     'U14', 'u14-native-abi-v2 (f8619ad5)', 2, 'past the Realm load (replay 0 missing)', 'high',
     [('mcdonalds', '_ctype_'), ('fd-im-vector-app', '_ctype_')]),
    ('D', 'bionic LIBC symbol not found in the native domain (Gecko `__gnu_strerror_r`, VLC `__pthread_cleanup_push`)',
     'U14', 'u14-native-abi-gecko (7605812c)', 2, 'fennec high (replay 0 missing); vlc medium (other libs not replayed)',
     'high/medium', [('fd-fennec_fdroid', 'libmozglue'), ('vlc', '__pthread_cleanup_push')]),
    ('E', 'Bitmap without ColorSpace: "can\'t create bitmap without a color space"',
     'U15', 'u15-framework-bitmap (framework 9e55e286, in the U15 bake)', 2, 'past createScaledBitmap', 'high',
     [('cv2-com-stoutner-privacybrowser-standard', 'color space'), ('fd-musicplayer', 'color space')]),
    ('F', 'M3 GLSurfaceView EGL IAE (converter bound to the wrong ANativeWindow_fromSurface), alive white, no fatal',
     'U15', 'u15-runtime-m3 (94c31177)', 0, 'IAE gone (medium); lit SPD medium, Unciv low-medium', 'medium',
     [('fd-app', 'alive-white-window'), ('fd-shatteredpixeldungeon', 'alive-white-window')]),
    ('G', 'dropped close / dialog under the Activity window (bridge), alive white, no fatal',
     'U14', 'u14-bridge-m5-m6 (7daa5435; dddmodel2 needs U13 runtime M1)', 0,
     'dddmodel2 own dialog on top (medium); AppManager white goes, own splash (medium-low)', 'medium',
     [('cv2-org-andresoviedo-dddmodel2', 'alive-white-window'), ('fd-AppManager', 'alive-white-window')]),
    ('H', 'termux finishes itself (in-process bind before onStart), alive white',
     'U14', 'u14-jar-v1 (0349eb83, InProcessBindOrder)', 1, 'first fatal moves to TermuxInstaller bootstrap check (own error dialog)',
     'high', [('termux', 'alive-white-window')]),
    ('I', 'toutiao: app-ns libicui18n.so ENOENT then SIGSEGV on the same thread (ICU 74 vs 72)',
     'U14', 'u14-appns-public-libs (341c1260 + ICU)', 1, 'both ICU walls removed; feed risk stays', 'medium',
     [('toutiao', 'platform-single')]),
    ('J', 'android.bluetooth.le.ScanCallback missing at bind', 'U14', '2026-10-03-bt-le-scancallback (stubs 87cf65cc)', 1,
     'bind passes initPlugins', 'high', [('fd-plus', 'ScanCallback')]),
    ('K', 'immich bind: VerifyError A2.b (android.net.nsd) then libcronet ATrace_beginSection',
     'U15', 'u15-stubs-nsd (94a94905) + u15-flutter-libandroid-v2 (9b824502)', 1,
     'bind passes; cronet loads; then the Flutter raster path (A)', 'medium', [('fd-immich', 'VerifyError')]),
    ('L', 'AppCompat theme: alias launch gets the application theme (line-1748 overwrite)',
     'U15', 'u15-jar-v1 (20e748e5)', 1, 'createSubDecor passes', 'high', [('fd-api', 'Theme.AppCompat')]),
    ('M', 'x: trampoline finish reaches AMS first -> second process, white at t20 by timing, no fatal',
     'U15', 'u15-jar-v1 (20e748e5, TrampolineFinishOrder)', 0, 'XLiteActivity in the first process ~11 s earlier; lit medium',
     'medium', [('x', 'alive-white')]),
    ('N', 'WifiManager is an empty boot stub (constructor only): NoSuchMethodError isScanThrottleEnabled() at main',
     'none', '- (U16 candidate: adapter-mainline-stubs WifiManager, 8 methods the app invokes, no-Wi-Fi semantics)', 1,
     'first fatal moves past the 8 WifiManager calls (high); t20 = its own "no networks / Wi-Fi off" UI (medium)', 'high',
     [('fd-wifianalyzer', 'isScanThrottleEnabled')]),
    ('O', 'window session not connected to SceneSessionManager -> addView InvalidDisplayException',
     'none', '- (mechanism known, no fix designed; chessclock only)', 0, '-', '-',
     [('cv2-com-chessclock-android', 'InvalidDisplayException')]),
    ('P', 'GetLongField JniAbort inside the app\'s own JNI getSceneInfo (null object)', 'none',
     '- (cc-wiki: on hold; the caller of the null object is undiagnosed)', 0, '-', '-',
     [('cv2-org-linaro-glmark2', 'signo(6)')]),
    ('Q', 'app `lateinit weatherView` (root cause undiagnosed; the CoroutineStart CNFE before it is our non-fatal prime)',
     'none', '-', 0, '-', '-', [('fd-breezyweather', 'dead')]),
    ('R', 'alive white, mechanism unclassified (61b)', 'none', '-', 0, '-', '-', [('fd-saber', 'alive-white')]),
    ('S', 'never launched: desktop tile not found (lit via aa start)', 'none', '- (launcher, not a runtime wall)', 0, '-',
     '-', [('cv2-com-frequent-habits', 'app_failed')]),
]


def main():
    rows = json.loads((HERE / 'per-run.json').read_text())
    by_key = {}
    for r in rows:
        by_key.setdefault(r['key'], []).append(r)
    seen = set()
    out, per_key = [], []
    for cid, name, owner, deliv, moves, picture, conf, members in CLUSTERS:
        for key, needle in members:
            runs = by_key.get(key)
            assert runs, f'{key}: not in per-run.json'
            hay = ' '.join(f"{x['terminal_cause']} {x['wall']} {x['terminal_kind']} {x['signal_thread']} {'/'.join(x['verdicts'])}"
                           for x in runs)
            assert needle in hay, f'{key}: assignment signature {needle!r} not in its row'
            assert key not in seen, key
            seen.add(key)
            r = runs[-1]
            per_key.append({'cluster': cid, 'key': key, 'board': r['board'], 'verdicts': '/'.join(r['verdicts']),
                            'bind': r['bind'], 'terminal_kind': r['terminal_kind'], 'terminal': r['terminal_cause'][:160],
                            'wall': r['wall'][:200], 'evidence_signature': needle, 'runs': len(runs), 'run': r['run']})
        out.append({'cluster': cid, 'name': name, 'keys_n': len(members), 'keys': ' '.join(k for k, _ in members),
                    'owner': owner, 'owner_deliverable': deliv, 'predicted_first_fatal_moves': moves,
                    'picture_prediction': picture, 'confidence': conf,
                    'u16_candidate': 'yes' if owner == 'none' and moves > 0 else 'no'})
    missing = sorted(set(by_key) - seen)
    assert not missing, f'unassigned keys: {missing}'
    out.sort(key=lambda c: (-c['keys_n'], c['cluster']))
    for name, data in (('clusters.csv', out), ('per-key.csv', per_key)):
        with open(HERE / name, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    tot = {o: sum(c['keys_n'] for c in out if c['owner'] == o) for o in ('U14', 'U15', 'none')}
    print(f"{len(seen)} keys, {len(out)} clusters; keys by owner {tot}; "
          f"predicted first-fatal moves U14 {sum(c['predicted_first_fatal_moves'] for c in out if c['owner']=='U14')} "
          f"U15 {sum(c['predicted_first_fatal_moves'] for c in out if c['owner']=='U15')} "
          f"U16 candidates {[(c['cluster'], c['keys_n'], c['predicted_first_fatal_moves']) for c in out if c['u16_candidate']=='yes']}")
    for c in out:
        print(f"{c['cluster']} {c['keys_n']} {c['owner']:4s} moves={c['predicted_first_fatal_moves']} {c['name'][:90]}")


if __name__ == '__main__':
    sys.exit(main())
