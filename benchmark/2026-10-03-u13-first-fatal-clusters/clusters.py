#!/usr/bin/env python3
"""Cluster per-run.json by first-fatal mechanism, map each cluster to the U14 parts, rank the unowned ones.

    clusters.py [--out-dir .]

Cluster rule (two layers, from per-run.json):
  by terminal  when the terminal is the fault itself (a signal with a native frame on the app's thread, a Java exception
               thrown by the platform API that failed);
  by wall      when the terminal is a consequence (process disappeared, bind_failed, a DI NPE, a bare SIGABRT from
               JniAbort, J_invokeStaticMain wrapping a ULE): the earliest wall is the mechanism.
The mechanism of each key is assigned below with the hilog line it rests on (`evidence/walls.txt`); the U14 owner and
the predicted first-fatal move come from the owners' own prediction tables (paths in OWNERS).
"""
import argparse
import csv
import json
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent

OWNERS = {
    'U14 Flutter libandroid fff9be31': 'benchmark/2026-10-03-u14-flutter-libandroid (prediction table)',
    'U14 native_abi 7605812c': 'benchmark/2026-10-03-u14-native-abi-gecko + gecko-fatal-before-bind (replay)',
    'U14 app-ns public libs 341c1260': 'benchmark/2026-10-03-u14-appns-build (prediction table, Wall 1)',
    'U14 app-ns 341c1260 + ICU 9b36b989/4886bc5c': 'benchmark/2026-10-03-u14-appns-build + toutiao-next-wall',
    'U14 stubs 87cf65cc': 'benchmark/2026-10-03-bt-le-scancallback',
    'U14 bridge 7daa5435 M5': 'benchmark/2026-10-03-u14-bridge-m5-m6/predictions.csv (with the M1 correction)',
    'U14 bridge 7daa5435 M6': 'benchmark/2026-10-03-u14-bridge-m5-m6/predictions.csv',
    'U14 JAR 0349eb83': 'benchmark/2026-10-03-u14-jar-v1',
    'U13 runtime 18763dd4 (GetLongField)': 'U13 window 1: the 4 Flutter keys moved past exactly this JniAbort',
    'U13 runtime 18763dd4 (M1 shim)': 'U13 window 1 sign-off: fd-noice 0/2 -> 6/6 (same app)',
    'U13 JAR v2/v3 bbc3f530': 'benchmark/2026-10-03-u13-jar-v2, u13-jar-v3-gcm',
    'theme probe (u13-java-walls-2)': 'benchmark/2026-10-03-u13-java-walls-2 section 2 (disabled probe)',
    'aa start fallback (cx-t0)': 'benchmark/2026-10-03-frequent-habits-ability-capture',
}

# id: (title, cluster_by, mechanism, owner or None, {key: (prediction, confidence, note)})
CLUSTERS = [
    ('C1', 'Flutter raster SIGSEGV ANativeWindow_getFormat+60 (libflutter -> platform libEGL with the AdapterAnw)',
     'terminal', 'SIGSEGV on 1.raster, #00 libnativewindow ANativeWindow_getFormat+60 <- mali <- platform '
     'eglCreateWindowSurface; earlier walls in the same process are caught (fluffychat AudioPortEventHandler ULE, '
     'libre libmpv -> libmediandk ENOENT)',
     'U14 Flutter libandroid fff9be31',
     {'localsend': ('moves', 'high', ''), 'fd-kitchenowl': ('moves', 'high', ''),
      'fd-fluffychat': ('moves', 'high', ''), 'fd-libre': ('moves', 'high', '')}),
    ('C2', 'bionic-only LIBC symbol, provider not in the app namespace scope (relocation; consequence terminal)',
     'wall', 'MUSL-LDSO relocating failed, symbol not found, use_vna_hash=1 van_hash=50d63 (LIBC); the symbol is '
     'exported by libbionic_compat but compat is not in scope for these libraries (gecko replay reproduces the board '
     'order only without compat)', None, {}),
    ('C2a', '... covered: native-cluster packages whose missing symbols the U14 GLOBAL native_abi now exports', 'wall',
     'firefox/fennec libmozglue __gnu_strerror_r (+9 queued); vlc libvlc __pthread_cleanup_push; ppsspp libppsspp_jni '
     'android_dlopen_ext (+ __errno, strtoll_l, strtoull_l, all in 7605812c)',
     'U14 native_abi 7605812c',
     {'firefox': ('moves', 'high', 'replay 0 missing for every Gecko lib'),
      'fd-fennec_fdroid': ('moves', 'high', 'replay 0 missing'),
      'vlc': ('moves', 'medium', 'first symbol exported; the other vlc libs were not replayed'),
      'ppsspp': ('moves', 'medium', 'relocation resolves; next = android_dlopen_ext extinfo calls get ENOTSUP '
                 '(015aa3a6 behaviour), u12-ppsspp-dlext')}),
    ('C2b', '... NOT covered, native domain: `_ctype_` (Realm)', 'wall',
     'bind_failed: librealmc / librealm-jni.so.10.19.0 `_ctype_` symbol not found; U13 compat b8a87f6f exports '
     '_ctype_ but compat is out of scope in native_private; U14 native_abi 7605812c has no _ctype_',
     None,
     {'mcdonalds': ('0', 'high', 'U12 run; U13 compat-ctype predicted a conditional move, scope says 0'),
      'fd-im-vector-app': ('0', 'high', 'U12 run; same import in librealm-jni')}),
    ('C2c', '... NOT covered, normal domain: `__register_atfork` (React Native / Hermes)', 'wall',
     'fd-meet libhermes.so + libreactnative.so __register_atfork, then libc++_shared android_set_abort_message; '
     'compat b8a87f6f does not export __register_atfork, native_abi does but org.jitsi.meet is not in the native '
     'cluster. Same symbol in x libcrashlytics (caught, not x\'s terminal)',
     None, {'fd-meet': ('0', 'high', 'U12 run')}),
    ('C3', 'GetLongField JniAbort (SIGABRT on main)', 'wall',
     '#05 JavaVMExt::JniAbort <- #06 JNI::GetLongField (U12 runs)', 'U13 runtime 18763dd4 (GetLongField)',
     {'fd-saber': ('moves (U13)', 'high', 'Flutter-private package: next expected C1 -> fff9be31 (medium)'),
      'cv2-org-linaro-glmark2': ('moves (U13)', 'high', 'next unknown (GLSurfaceView native)')}),
    ('C4', 'NDK API symbol missing in a private domain (relocation, unversioned)', 'wall',
     'fd-immich libcronet ATrace_beginSection (Flutter-private libandroid fff9be31 has no ATrace_*), after a bind '
     'VerifyError A2.b (Unresolved Reference d7.c); mindustry libarc slCreateEngine (native domain)', None,
     {'fd-immich': ('0', 'high', 'U13 run; bind also fails on VerifyError A2.b'),
      'mindustry': ('0', 'medium', 'U12 run; app-ns public libs 341c1260 only if the native domain takes the bridge '
                    'inherit, unverified')}),
    ('C5', 'Bitmap.createBitmap: "can\'t create bitmap without a color space"', 'terminal',
     'IllegalArgumentException at android.graphics.Bitmap.createBitmap(Bitmap.java:1203)', None,
     {'cv2-com-stoutner-privacybrowser-standard': ('0', 'high', 'U13 run: the U12 webkit wall moved here'),
      'fd-musicplayer': ('0', 'high', 'U12 run; earlier bg NCDFE MediaStore$Audio$Artists (kept alive)')}),
    ('C6', 'libGLESv3/GLES public lib ENOENT in the app namespace', 'wall',
     'subwaysurfers libvkquality NEEDED libGLESv3.so ENOENT -> SIGABRT main', 'U14 app-ns public libs 341c1260',
     {'subwaysurfers': ('moves', 'high (owner table)', 'U12 run')}),
    ('C7', 'ICU (public lib + 74/72) for toutiao', 'wall',
     'U12 t20: unbound_at_capture; long wait: libicui18n ENOENT -> ICUWrapper (toutiao-icu-wall)',
     'U14 app-ns 341c1260 + ICU 9b36b989/4886bc5c',
     {'toutiao': ('moves', 'high (owner)', 'cc-wiki: lit shell with feed risk; t20 hilog sees only CronetInit '
                  'NetworkInfo.getSubtype NSME (kept alive)')}),
    ('C8', 'missing android.bluetooth.le class at bind', 'wall', 'bind_failed: ClassNotFoundException ScanCallback',
     'U14 stubs 87cf65cc', {'fd-plus': ('moves', 'high', 'U12 run')}),
    ('C9', 'ITelephonyRegistry NPE (telephony.registry)', 'terminal',
     'NPE TelephonyRegistryManager.listenFromListener', 'U13 JAR v2/v3 bbc3f530',
     {'x': ('moves (U13)', 'high', 'U12 run, U13 not run on 61b; window 2')}),
    ('C10', 'AES/GCM (R3 GcmDefaultNonce)', 'terminal', 'IllegalStateException GCM cipher needs to be initialised',
     'U13 JAR v2/v3 bbc3f530', {'cv2-com-lcdcode-moodcairns': ('moves (U13)', 'high', 'U12 run, window 2')}),
    ('C11', 'Theme.AppCompat rejected', 'terminal', 'IllegalStateException AppCompatDelegateImpl.createSubDecor',
     'theme probe (u13-java-walls-2)', {'fd-api': ('probe', '-', 'U13 run; earlier bg ULE LocalSocketImpl.bindLocal')}),
    ('C12', 'single-key fatal walls, unowned', 'terminal/wall', 'see per key', None,
     {'fd-wifianalyzer': ('0', 'high', 'NoSuchMethodError WifiManager.isScanThrottleEnabled() (stubs) on main'),
      'cv2-com-chessclock-android': ('0', 'high', 'U13 run: InvalidDisplayException at WindowManagerGlobal.addView; '
                                     'earlier NSME ActivityManagerAdapter.nativeConsumeConnectionFailure(I)Z'),
      'fd-breezyweather': ('0', 'high', 'J_invokeStaticMain: lateinit property weatherView has not been initialized '
                           '(first_fatal.py: unknown)'),
      'burgerking': ('0', 'high', 'SIGSEGV pc 0 on pool-4-thread-1, unwind failed (native cluster)')}),
    ('C13', 'RenderThread SIGSEGV lottery (lit reference key)', 'terminal',
     'fd-fitness: #00 libskia_canvaskit sktext::gpu::StrikeCache::generateStrike+156 on RenderThread', None,
     {'fd-fitness': ('lottery', '-', 'U13 run 0/1; U12 3/4; k/n in window 2')}),
    ('C14', 'no observed termination, alive at t20, owned', 'none (window state)', 'bound, no fatal line', None,
     {'fd-AppManager': ('white goes', 'medium', 'U14 bridge 7daa5435 M6'),
      'fd-mobile': ('own dialog', 'high', 'U14 bridge 7daa5435 M5'),
      'cv2-org-andresoviedo-dddmodel2': ('own dialog', 'medium', 'U14 bridge 7daa5435 M5 (+U13 M1)'),
      'termux': ('launcher', 'medium', 'U14 JAR 0349eb83 + M6 (not lit at t20)'),
      'noice': ('moves (U13)', 'medium', 'U13 runtime 18763dd4 (M1 shim): same app as fd-noice, 6/6 in window 1')}),
    ('C15', 'no observed termination, alive at t20, unowned (white/black residual)', 'none (window state)',
     'bound, no fatal line in the target pids; first-fatal clustering cannot split them', None,
     {k: ('0', '-', n) for k, n in (
         ('cv2-ca-vaults-randomlydie', ''), ('cv2-com-bytehamster-flowitgame', ''), ('cv2-com-degeder-yam', ''),
         ('cv2-com-paultirk-yatoo', ''), ('cv2-dev-obfusk-jiten-webview', ''), ('cv2-timur-webrtc-check', 'black'),
         ('fd-app', 'bg NSME MediaStore.scanFile (kept alive)'), ('fd-shatteredpixeldungeon', ''),
         ('fd-tutanota', 'reference dead, alive t5/t20'))}),
    ('C16', 'never launched (launcher tile absent)', 'none', 'app_failed: broken webp icon', 'aa start fallback (cx-t0)',
     {'cv2-com-frequent-habits': ('lit via aa start', 'high', 'not a runtime wall')}),
]

OWNER_OF = {'fd-AppManager': 'U14 bridge 7daa5435 M6', 'fd-mobile': 'U14 bridge 7daa5435 M5',
            'cv2-org-andresoviedo-dddmodel2': 'U14 bridge 7daa5435 M5', 'termux': 'U14 JAR 0349eb83',
            'noice': 'U13 runtime 18763dd4 (M1 shim)'}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out-dir', default=str(HERE))
    out = Path(ap.parse_args().out_dir)
    runs = {r['key']: r for r in json.loads((HERE / 'per-run.json').read_text())}
    seen, clusters, rows = set(), [], []
    for cid, title, by, mech, owner, keys in CLUSTERS:
        for k, (pred, conf, note) in keys.items():
            assert k in runs and k not in seen, k
            seen.add(k)
            r = runs[k]
            o = owner or OWNER_OF.get(k)
            rows.append(OrderedDict(cluster=cid, key=k, board=r['board'], generation=r['generation'],
                                    runtime_jar=r['runtime_jar'], bind=r['bind'], terminal_kind=r['terminal_kind'],
                                    signal_thread=r['signal_thread'], owner=o or 'UNOWNED', predicted=pred,
                                    confidence=conf, note=note, terminal=r['terminal_cause'][:160],
                                    wall=r['wall'][:200], facts=r['facts'], run=r['run']))
        if keys:
            ks = sorted(keys)
            owned = [k for k in ks if (owner or OWNER_OF.get(k))]
            clusters.append(OrderedDict(id=cid, title=title, cluster_by=by, mechanism=mech, keys=len(ks),
                                        owner=owner or ('mixed' if owned else 'UNOWNED'),
                                        u13_measured=sum(runs[k]['generation'] == 'u13' for k in ks),
                                        predicted_movers=[k for k in ks if keys[k][0].startswith('moves')],
                                        bind=sorted({runs[k]['bind'] for k in ks}), members=ks))
    missing = set(runs) - seen
    assert not missing, missing
    clusters.sort(key=lambda c: (-c['keys'], c['id']))
    (out / 'clusters.json').write_text(json.dumps({'population': len(runs), 'clusters': clusters},
                                                  indent=1, ensure_ascii=False) + '\n')
    with open(out / 'per-key.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for c in clusters:
        print(c['keys'], c['id'], c['owner'], c['u13_measured'], c['members'])


if __name__ == '__main__':
    main()
