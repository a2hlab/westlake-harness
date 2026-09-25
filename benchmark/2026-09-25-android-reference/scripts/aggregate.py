#!/usr/bin/env python3
"""Fold runs/*/summary.json into results.json (board entry #26).

Tab names come from the video, not from drive.sh: tapping 热点 scrolls the tab
strip, so the later fixed-x taps land on different categories, and a second
launch pins 推荐 at the left. images/tab-strips-*.png is the check.
"""
import json
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RUNS = ['F1', 'F2', 'F3', 'S1', 'S2', 'S3']
FIRST = {'hotspot': '热点', 'shenzhen': '小视频', 'rebang': '小说', 'tuijian': '推荐'}
SECOND = {'hotspot': '热点', 'shenzhen': '小视频', 'rebang': '热榜', 'tuijian': '推荐'}
# S1: Toutiao's login promo (TransparentAccountLoginActivity) opened ~8 s into
# the launch and took focus; all four taps landed on it. Launch-phase numbers
# stand, tap-phase visual numbers do not. drive.sh closes it since S2.
TAPS_INVALID = {'S1'}


def num(s):
    return None if s is None else float(re.match(r'[\d.]+', s).group())


def rng(xs):
    xs = [x for x in xs if x is not None]
    return {'n': len(xs), 'min': min(xs), 'median': statistics.median(xs), 'max': max(xs)} if xs else None


def main():
    runs = {}
    for r in RUNS:
        d = json.loads((HERE / 'runs' / r / 'summary.json').read_text())
        labels = FIRST if r.startswith('F') else SECOND
        for t in d['taps']:
            t['tab'] = 'consent' if t['name'] == 'consent' else labels[t['name']]
            if r in TAPS_INVALID and t['name'] != 'consent':
                t['invalid'] = 'tap landed on the login promo, not the tab strip'
        d['mode'] = 'first launch (pm clear)' if r.startswith('F') else 'second launch (data of the preceding F run)'
        runs[r] = d

    def cond(prefix, valid_taps):
        rs = [runs[r] for r in RUNS if r.startswith(prefix)]
        tr = [runs[r] for r in RUNS if r.startswith(prefix) and r not in TAPS_INVALID] if valid_taps else rs
        taps = [t for d in tr for t in d['taps']]
        out = {
            'runs': [d['run'] for d in rs],
            'am_start_total_ms': rng([num(d['am_start']['TotalTime']) for d in rs]),
            'inject_to_main_thread_ms': rng([t.get('inject_to_main_ms') for t in taps]),
            'tab_to_content_ms': {},
            'tab_to_page_switch_ms': rng([t.get('switch_ms') for t in taps if t['tab'] != 'consent']),
            'choreographer_skipped': {ph: sorted(x for d in rs for x in d['choreographer_skipped'][ph]) for ph in ('launch', 'taps')},
            'davey_ms': {ph: sorted(x for d in rs for x in d['davey_ms'][ph]) for ph in ('launch', 'taps')},
            'gfxinfo_janky_pct': {ph: [num(d['gfxinfo'][ph]['Janky frames'].split('(')[1]) for d in rs] for ph in ('launch', 'taps')},
            'main_thread_longest_slice_ms': {ph: [d['main_' + ph]['top'][0]['ms'] if d['main_' + ph]['top'] else 0 for d in rs] for ph in ('launch', 'taps')},
            'main_thread_slices_ge_500ms': {ph: [d['main_' + ph]['slices_ge_500ms'] for d in rs] for ph in ('launch', 'taps')},
        }
        for tab in dict.fromkeys(t['tab'] for t in taps if t['tab'] != 'consent'):
            out['tab_to_content_ms'][tab] = [t.get('content_ms') for t in taps if t['tab'] == tab]
        return out

    sha = dict(reversed(l.split()) for l in (HERE / 'runs' / 'raw-sha256.txt').read_text().splitlines())
    results = {
        'schema': 1,
        'date': '2026-09-25',
        'board_entry': '#26 (.octos/OUTER_LOOP_REVIEW.md)',
        'device': {
            'serial': 'N100CU025C18D000128', 'product': 'uis7885_2h10_native (UNISOC)',
            'android': '16 (SDK 36)', 'build_type': 'userdebug', 'abi': 'arm64-v8a',
            'screen': '1200x1920 @ 320 dpi (same as the OH boards)',
            'network': 'WiFi; ping www.toutiao.com 5/5, 35-74 ms before the runs',
        },
        'apk': {
            'package': 'com.ss.android.article.news', 'versionName': '13.9.0', 'versionCode': 13900,
            'sha256': 'a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395',
            'install': 'already installed 2026-01-14, base.apk byte-identical to app-inputs/toutiao/toutiao.apk; not reinstalled',
        },
        'data_safety': {
            'backup': '/data/user/0, /data/user_de/0 and Android/data of the package tarred with --selinux --numeric-owner before the first pm clear (16860+5+60 entries; one runtime socket not archivable)',
            'restore': 'pm clear, then extract; re-tarred listing vs backup listing: 0 differences in mode/owner/size/mtime/path for all three trees; relaunch opens the feed with no consent dialog and the original local channel (广州)',
            'not_restorable': 'pm clear also resets runtime permission grants; the pre-run grant state was not recorded. After the runs no dangerous permission is granted and the notification prompt is left undecided (dismissed with BACK)',
            'backup_kept_at': '/data/local/tmp/tt26-backup (root-only, 1.5 GB); delete when no longer wanted',
        },
        'method': {
            'launch': 'am start -W on the launcher activity; F = pm clear first, S = force-stop only (reuses the data of the preceding F run)',
            'taps': 'input tap at fixed coordinates: consent (F only) then four tab taps 7.3 s apart; system notification prompt and login promo closed with BACK first',
            'inject_to_main_thread': 'atrace (input view gfx am wm dalvik + app): main-thread deliverInputEvent begin minus that event\'s eventTimeNano. Android counterpart of Westlake\'s post->run',
            'tab_to_content': 'screenrecord frames timed by the Winscope metadata track (per-frame CLOCK_MONOTONIC plus realtime offset); page switch = feed region (y 240-1700) differs from the pre-tap frame, content = first such frame with grey std > 30 (blank loading page ~0.3, skeleton 13-22, real items 35-85). Includes 89-313 ms of `input` command overhead before the event reaches the app (tapcmd_to_main_ms)',
            'jank': 'dumpsys gfxinfo (reset after the launch phase), logcat Choreographer "Skipped N frames" and HWUI "Davey!" for the app pid, atrace main-thread top-level slices',
            'native': '/proc/<pid>/maps and nativeloader logcat lines; find over the data dirs for any .so / metasec copy',
            'image_format': 'magic bytes of every Fresco disk-cache entry (cache/image_cache/v2.ols100.1/*.cnt)',
        },
        'reference': {'first_launch': cond('F', True), 'second_launch': cond('S', True)},
        'westlake_comparison': {
            'post_to_run_ms_launch_25': {
                'source': 'benchmark/2026-09-25-touch-factorial/results.json on analysis/touch-factorial-25 (bc20d1cc), outer-loop verified; DOWN of each of two processes per cell',
                'offline fresh': [21499, 21374], 'online fresh': [11451, 13217],
                'offline reused': [10656, 8331], 'online reused': [11662, 13186],
                'range_down_and_up': [8227, 21499],
                'note': '1 ms only in the same process once launch work is over; the #21 warm1 "1 ms" was that case, not a data/network effect',
            },
            'post_to_run_ms_21': [11016, 11065, 16730, 16642],
            'oh_cause_25': 'UI thread blocked on the SourcePackageRegistry class lock while another thread runs PackageParser.collectCertificates over the whole APK',
            'android_counterpart': 'AOSP verifies signatures at install time in system_server and answers runtime queries from cache (behaviour, not measured here)',
            'android_inject_to_main_ms_max': 71.6,
        },
        'metasec': {
            'android_mapped_from': '/data/app/<codePath>/lib/arm64/libmetasec_ml.so (6/6 runs, r-xp + rw-p)',
            'android_loader': 'nativeloader: "Load .../lib/arm64/libmetasec_ml.so using class loader ns clns-9 ...: ok" once per run in the main process',
            'app_lib_dir_created': False,
            'copies_in_data_dirs': 0,
            'app_librarian': 'directory exists but holds only an empty version dir: the Librarian extract-and-copy fallback never ran',
            'implication': 'On Android the first load succeeds in the app classloader namespace, which sees public NDK libs (libandroid.so with ASensorManager_*). The app_lib copy seen on OH (#23) is the app\'s fallback after that first load failed, not normal behaviour; making the first load succeed removes the copy path entirely.',
        },
        'thumbnails': {
            'android_formats': {r: runs[r]['image_cache'] for r in RUNS},
            'android_feed_video_covers': 'HEIC: all four 960x540 covers in the exploration cache are ftypheic, and they are the covers on screen (images/heic-feed-covers.jpg)',
            'android_other': 'WebP for article/gallery pictures and portrait covers, PNG for icons, a few JPEG and GIF',
            'android_libs_loaded': 'libimagepipeline, libttheif_dec, libbdheif, libgifimage, libstatic-webp all mapped from lib/arm64 via clns-9',
            'oh_failure': 'every Toutiao run: [SOURCE-NATIVE-LOAD-FAIL] libbdheif.so namespace=0 "_ZNSt6__ndk119__shared_weak_countD2Ev: symbol not found" (sensor-online-1 L7745, 400-900 times per run), then "Rejecting re-init ... nativeheif.Heif"; libgifimage fails on "_ZNKSt6__ndk119__shared_weak_count13__get_deleter..." (sensor-online-3 L21092)',
            'cause': 'not an NDK API gap: namespace 0 resolves libc++_shared.so to OH /system/lib64 (search path puts /system/lib64 before the app lib dir; both copies mapped, maps-early L954 app copy, L1685 system copy). the OH SDK libc++_shared.so (toolchains/ohos-sdk, aarch64) exports 0 std::__ndk1 symbols (its ABI namespace is std::__n1) while the APK copy exports 1760; the board\'s /system/lib64 copy was not read (board read-only this round; check: llvm-nm -D <copy> | grep -c __ndk1). In sensor-online-3, 15 distinct app libraries fail on a __ndk1 symbol (libbdheif, libgifimage, libquick, libvcbasekit, libnpth*, libanimax, libkeva, liblynx*, libjato, libnapi, liblivestrategy)',
            'conclusion': 'Grey 16:9 video covers on OH are explained: they are HEIC on the wire and the HEIF decoder library cannot load. Whether the smaller article thumbnails are HEIC too is not proven from OH logs (no URLs or content types are logged)',
            'fix': 'add libbdheif.so (with libttheif_dec.so) and libgifimage.so to the Android-ABI native targets, the mechanism already used for libsscronet; do not shim C++ ABI symbols. Wider option (higher risk): let namespace 0 resolve the APK libc++_shared.so for app libraries',
            'disproved_if': 'thumbnails stay grey with libbdheif loaded (then check BitmapFactory/WebP and upload), or grey tiles turn out to be JPEG/WebP bytes',
        },
        'work_thread_sigabrt': {
            'signature': 'sigaction #16 signal=6 flags=0x18000004 callback=<libsafe-mode-native-lib.so+0xb28> immediately followed by "Fatal signal 6 (SIGABRT), code -6 (SI_TKILL)", Thread "work_thread", empty backtrace, x13 = " is null" (ASCII)',
            'seen_in': 'all 7 Toutiao runs in applib23 that get past startup (sensor-online-1 L18046 tid 5283, -2 L22485 tid 9820, -3 L24837 tid 14703, baseline1 L18771, diag1 L22519, fix1 L23390, fresh-online-1 L21648)',
            'thread_creator': 'com.umeng.mc.e.a() (classes17.dex) is the only code referencing "work_thread": new HandlerThread("work_thread")',
            'native_work': 'libumeng-spy.so loads 0.3-0.9 s before every abort; Java_com_umeng_umzid_Spy_getNativeID calls signal(SIGCHLD=17) at 0x7bfc and fork() at 0x7c00',
            'sigaction_16': 'not a SIG_DFL reset: flags and callback are byte-identical to #3, which libsafe-mode-native-lib.so installed at startup for SIGILL/TRAP/ABRT/BUS/FPE/SEGV/STKFLT/SYS; #9-#15 are Chromium crashpad (libwebviewchromium.so+0x4099190). So #16 is crashpad restoring SafeMode\'s handler before re-raising',
            'process_exit': 'not by this abort, and no cppcrash collected for it: diag1 and fix1 are alive (state S) at the final check; in the other five the process is gone by the final check but the same pid keeps logging 26-51 s after the abort first (sensor-online-1 pid 3485: 15:41:39 before, last line 15:42:05)',
            'hypothesis': 'the abort happens in the child forked by getNativeID (it inherits the thread name work_thread): fresh tid never seen elsewhere, app survives, and the shim\'s sigaction counter repeats #16 afterwards in the app (fresh-online-1 L21646 then L22640; diag1 L22517 then L23391), as a copy of the counter would in a child. Alternative still open: the handler chain parks the thread',
            'next_steps': [
                'board, read-only: ls /data/log/faultlog/temp /data/log/faultlog/faultlogger | grep cppcrash-<abort tid> (the harness only collects cppcrash-<app pid>)',
                'fork/abort/raise interposers in the preloaded libwebview_bionic_shim.so logging pid, tid, comm and dladdr(caller), tagged [WESTLAKE-FORK]/[WESTLAKE-ABORT]',
                'A/B: withhold libumeng-spy.so (Spy.<clinit> catches the load failure); if the abort disappears, attribution is confirmed',
                'side effect to check: after umeng installs its SIGCHLD handler (waitpid(-1) loop) no [WESTLAKE-REAP] line appears again',
            ],
        },
        'raw_archive': {
            'path': 'VM a2hlab: ~/a2hlab/android-ref26/ (runs/<RUN>/screen.mp4, atrace.txt, logcat.txt; harness copy; exploration cache)',
            'sha256': sha,
        },
        'fixture_notes': [
            'run.sh backgrounded adb logcat through a shell function, so kill hit the subshell and the reader kept appending later runs to earlier logcat.txt files; fixed in scripts/run.sh, the archived logs were cut at END+10 s, and every summary.json re-derived from the cut logs is byte-identical (all logcat metrics are filtered by app pid)',
            'tab labels are read from the video (images/tab-strips-*.png): the strip auto-scrolls after 热点, so the fixed-x taps hit 小视频/小说 (first launch) and 小视频/热榜 (second launch), not the names in drive.sh',
            'S1 tap phase is invalid (login promo took focus); drive.sh closes it since S2',
        ],
        'runs': runs,
    }
    (HERE / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=1) + '\n')
    for k in ('first_launch', 'second_launch'):
        print(k, json.dumps(results['reference'][k], ensure_ascii=False))


if __name__ == '__main__':
    main()
