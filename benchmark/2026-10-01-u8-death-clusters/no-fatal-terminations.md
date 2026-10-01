# U8 no-first-fatal termination audit (11 keys)

## Correction first

The old index’s `first_fatal=None` was not evidence of silent death. At dispatch commit `452b8f18f`, `scripts/lab/run_index.py:33` only matched FATAL EXCEPTION, Fatal signal, JNI DETECTED ERROR, Reason:Signal and Unable to start activity. The original logs contain **6 main_threw → System.exit(1), 2 other System.exit calls, 1 skia/hwui abort and 2 APPSPAWN SIGKILL results**. No frozen score or existing cluster file is edited here. The previous table’s “10” label actually listed the assigned **11** keys.

Rule: bind the app PID from exact APPSPAWN spawn success, retain system-emitted victim records, and separate **exit mechanism / preceding wall / killer identity**. AMS Ability scheduler death, WMS client death and AppMS OnRemoteDied cleanup confirm death; they do not establish its original cause.

## Scope and identity

Only the six signed `*-seq-{v1,cv2}` roots plus `5cd-seq-v1-rest` are used. Invalid concurrent attempts and later J10/N11 windows are excluded. `fd-plus` uses the rest shard. The unchanged first_fatal implementation SHA256 is `d497514debd442e6df5b0647888424df6c9386e0b0a3c0e7fc7ef87239c72404`.

U8 signed state: `{'RUNTIME': 'e953c0921536', 'BOOTIMAGE': '4db882a81732', 'name': 'U8'}`. Source-map SHA256 `a0443fe5bf3be9b8e1cbf8b75726ef47f786ee6388e118f3a712639c4c892b23`; outer-signoff SHA256 `852488d17a5571b8bf931c0ea09a98b13a2a728216c8ff015c18330c3a905524`. Each row pins record/APK identity, raw hilog, process snapshots, fault inventories and diagnostics by SHA256 in JSON.

All **11 are signed dead**, all target PIDs are absent from `processes-t20.txt`. Only `fd-plus` and `toutiao` survive the t5 snapshot. Each `faultlogs/` is empty, and each before/after inventory has **0 new entries**. Thus fault capture provides no crash stack, even for the explicit hwui abort. No target-bound memory kill or watchdog/ANR kill was recovered; absence does not prove these mechanisms impossible.

## Groups (descending size)

| Observed termination group | Count | Keys |
|---|---:|---|
| java-main-threw-system-exit-1 | 6 | cv2-com-nbossard-packlist, cv2-com-nononsenseapps-notepad, fd-meet, fd-musicplayer, fd-plus, toutiao |
| sigkill-sender-unknown | 2 | fd-fennec_fdroid, firefox |
| native-hwui-abort | 1 | cv2-com-bytehamster-flowitgame |
| system-exit--1 | 1 | ppsspp |
| system-exit-0 | 1 | cv2-com-kaajjo-libresudoku |

## Per-key evidence

Within each subsection, file:line references resolve under its **Source** directory (`$WORKSPACES/` prefix). JSON retains original line text, timestamp, emitter PID/TID and explicit victim identity.

### cv2-com-nbossard-packlist

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-cv2/20261001T122027-e3c3b085/5cd1e3dd00000000000000000923012c/cv2-com-nbossard-packlist/`
- Package `com.nbossard.packlist`; target PID `[18643]`; signed `dead`; group `java-main-threw-system-exit-1`.
- Identity: `hilog.txt:33402` names the exact child package and PID.
- First matched app terminal: `hilog.txt:40980` — `[stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.NoClassDefFoundError: org.acra.util.IOUtils`.
- Parent wait result: `hilog.txt:41160` — `[appspawn_service.c:118]com.nbossard.packlist with pid 18643 exit with code:1`.
- first_fatal root: `hilog.txt:41026` — `[stderr] Caused by: java.lang.ClassNotFoundException: com.android.internal.util.Predicate`.
- Death notification (not killer): `hilog.txt:41099` — `[ABR1882]Ability on scheduler died: 'com.nbossard.packlist.gui.MainActivity'`.
- Assessment: **verified Java terminal chain**. ACRA IOUtils initialization exposes missing com.android.internal.util.Predicate; the innermost ClassNotFoundException is :41026, not the earlier coroutine presence probe.

### cv2-com-nononsenseapps-notepad

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-cv2/20261001T122027-e3c3b085/5cd1e3dd00000000000000000923012c/cv2-com-nononsenseapps-notepad/`
- Package `com.nononsenseapps.notepad`; target PID `[23111]`; signed `dead`; group `java-main-threw-system-exit-1`.
- Identity: `hilog.txt:33016` names the exact child package and PID.
- First matched app terminal: `hilog.txt:46915` — `[stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.NullPointerException: Attempt to invoke interface method 'boolean android.database.Cursor.moveToFirst()' on a null object reference`.
- Parent wait result: `hilog.txt:47038` — `[appspawn_service.c:118]com.nononsenseapps.notepad with pid 23111 exit with code:1`.
- first_fatal root: `hilog.txt:46916` — `[stderr] java.lang.NullPointerException: Attempt to invoke interface method 'boolean android.database.Cursor.moveToFirst()' on a null object reference`.
- Death notification (not killer): `hilog.txt:46987` — `[ABR1882]Ability on scheduler died: 'com.nononsenseapps.notepad.activities.main.ActivityMain_'`.
- Assessment: **verified Java terminal chain**. DrawerCursorLoader.onLoadFinished receives a null Cursor (:46917); origin of that null remains unproven.

### fd-fennec_fdroid

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-v1/20261001T120453-7582ddda/5cd1e3dd00000000000000000923012c/fd-fennec_fdroid/`
- Package `org.mozilla.fennec_fdroid`; target PID `[18232]`; signed `dead`; group `sigkill-sender-unknown`.
- Identity: `hilog.txt:15288` names the exact child package and PID.
- Parent wait result: `hilog.txt:50355` — `[appspawn_service.c:114]org.mozilla.fennec_fdroid with pid 18232 exit with signal:9`.
- Death notification (not killer): `hilog.txt:50331` — `[ABR1882]Ability on scheduler died: 'org.mozilla.fennec_fdroid.App'`.
- Assessment: **SIGKILL verified; sender and killing cause unknown**. Gecko background exception is explicitly swallowed/process kept alive (:50267). libmozglue.so lacks __gnu_strerror_r (:50294), then APPSPAWN signal 9 (:50355). No PID-bound lmkd/memmgr/watchdog/ANR kill evidence was found; do not call the caught exception or OnRemoteDied cleanup the SIGKILL sender.

### fd-meet

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-v1/20261001T120453-7582ddda/5cd1e3dd00000000000000000923012c/fd-meet/`
- Package `org.jitsi.meet`; target PID `[30293]`; signed `dead`; group `java-main-threw-system-exit-1`.
- Identity: `hilog.txt:9263` names the exact child package and PID.
- First matched app terminal: `hilog.txt:23949` — `[stderr] [CHILD_CK] J_invokeStaticMain_main_threw: com.facebook.soloader.B: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so: Error relocating /data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so: android_set_abort_message: symbol not found`.
- Parent wait result: `hilog.txt:24224` — `[appspawn_service.c:118]org.jitsi.meet with pid 30293 exit with code:1`.
- first_fatal root: `hilog.txt:23949` — `[stderr] [CHILD_CK] J_invokeStaticMain_main_threw: com.facebook.soloader.B: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so: Error relocating /data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so: android_set_abort_message: symbol not found`.
- Death notification (not killer): `hilog.txt:24247` — `[ABR1882]Ability on scheduler died: 'org.jitsi.meet.MainActivity'`.
- Assessment: **verified Java terminal chain**. SoLoader fails relocating libc++_shared.so: android_set_abort_message is unavailable.

### fd-musicplayer

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-v1/20261001T120453-7582ddda/5cd1e3dd00000000000000000923012c/fd-musicplayer/`
- Package `org.fossify.musicplayer`; target PID `[1630]`; signed `dead`; group `java-main-threw-system-exit-1`.
- Identity: `hilog.txt:9590` names the exact child package and PID.
- First matched app terminal: `hilog.txt:42397` — `[stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.IllegalArgumentException: can't create bitmap without a color space`.
- Parent wait result: `hilog.txt:42689` — `[appspawn_service.c:118]org.fossify.musicplayer with pid 1630 exit with code:1`.
- first_fatal root: `hilog.txt:42398` — `[stderr] java.lang.IllegalArgumentException: can't create bitmap without a color space`.
- Death notification (not killer): `hilog.txt:42638` — `[ABR1882]Ability on scheduler died: 'org.fossify.musicplayer.activities.MainActivity'`.
- Assessment: **verified Java terminal chain**. Bitmap.createBitmap (:42401) rejects absent color space; this is not an AMS/memory kill.

### fd-plus

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-v1-rest/20261001T124951-f0a9fa0b/5cd1e3dd00000000000000000923012c/fd-plus/`
- Package `net.osmand.plus`; target PID `[5581]`; signed `dead`; group `java-main-threw-system-exit-1`.
- Identity: `hilog.txt:15177` names the exact child package and PID.
- First matched app terminal: `hilog.txt:75473` — `[stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.IllegalStateException: Surface was not locked`.
- Parent wait result: `hilog.txt:75709` — `[appspawn_service.c:118]net.osmand.plus with pid 5581 exit with code:1`.
- first_fatal root: `hilog.txt:75474` — `[stderr] java.lang.IllegalStateException: Surface was not locked`.
- Death notification (not killer): `hilog.txt:75677` — `[ABR1882]Ability on scheduler died: 'net.osmand.plus.activities.MapActivity'`.
- Assessment: **verified Java terminal chain**. Surface.unlockSwCanvasAndPost (:75475) reports Surface was not locked. It is still present at t5 (:325) and absent at t20.

### cv2-com-bytehamster-flowitgame

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5ea-seq-cv2/20261001T122134-78628011/5ea34a4500000000000000001123012c/cv2-com-bytehamster-flowitgame/`
- Package `com.bytehamster.flowitgame`; target PID `[16618]`; signed `dead`; group `native-hwui-abort`.
- Identity: `hilog.txt:46543` names the exact child package and PID.
- First matched app terminal: `hilog.txt:53765` — `ASSERT FAILED cond=!extensions.has("EGL_KHR_swap_buffers_with_damage") msg=Missing required extension EGL_KHR_swap_buffers_with_damage`.
- Parent wait result: `hilog.txt:53988` — `[appspawn_service.c:118]com.bytehamster.flowitgame with pid 16618 exit with code:134`.
- Death notification (not killer): `hilog.txt:53866` — `[ABR1882]Ability on scheduler died: 'com.bytehamster.flowitgame.Main'`.
- Assessment: **verified native abort**. Skia assertion says Missing required extension EGL_KHR_swap_buffers_with_damage (:53765), followed by hwui abort (:53766). APPSPAWN records code 134, NOT signal 6; no crash stack was captured.

### cv2-com-kaajjo-libresudoku

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-cv2/20261001T122904-44eb39c6/61b0657200000000000000000324012c/cv2-com-kaajjo-libresudoku/`
- Package `com.kaajjo.libresudoku`; target PID `[22895]`; signed `dead`; group `system-exit-0`.
- Identity: `hilog.txt:39114` names the exact child package and PID.
- First matched app terminal: `hilog.txt:71689` — `[OpenjdkJvm.cc:344] System.exit called, status: 0`.
- Parent wait result: `hilog.txt:71715` — `[appspawn_service.c:118]com.kaajjo.libresudoku with pid 22895 exit with code:0`.
- Death notification (not killer): `hilog.txt:71740` — `[ABR1882]Ability on scheduler died: 'com.kaajjo.libresudoku.MainActivity'`.
- Assessment: **exit verified; trigger inferred from same-thread sequence**. NPE at Locale.getDisplayName (:71629–71630), CrashActivity start (:71682) returns 2097205 (:71688), then System.exit(0) (:71689). This is an error-handler-shaped exit despite code 0; exact exit caller was not decoded. first_fatal root is unknown because IPC lines break adjacency.

### firefox

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-v1/20261001T120452-13a8b24d/61b0657200000000000000000324012c/firefox/`
- Package `org.mozilla.firefox`; target PID `[30409]`; signed `dead`; group `sigkill-sender-unknown`.
- Identity: `hilog.txt:27465` names the exact child package and PID.
- Parent wait result: `hilog.txt:64245` — `[appspawn_service.c:114]org.mozilla.firefox with pid 30409 exit with signal:9`.
- Death notification (not killer): `hilog.txt:64228` — `[ABR1882]Ability on scheduler died: 'org.mozilla.firefox.App'`.
- Assessment: **SIGKILL verified; sender and killing cause unknown**. Same Mozilla sequence: swallowed Gecko exception (:64194), missing __gnu_strerror_r (:64200), APPSPAWN signal 9 (:64245). No PID-bound lmkd/memmgr/watchdog/ANR kill evidence was found.

### ppsspp

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-v1/20261001T120452-13a8b24d/61b0657200000000000000000324012c/ppsspp/`
- Package `org.ppsspp.ppsspp`; target PID `[2013]`; signed `dead`; group `system-exit--1`.
- Identity: `hilog.txt:27327` names the exact child package and PID.
- First matched app terminal: `hilog.txt:35593` — `[OpenjdkJvm.cc:344] System.exit called, status: -1`.
- Parent wait result: `hilog.txt:35614` — `[appspawn_service.c:118]org.ppsspp.ppsspp with pid 2013 exit with code:255`.
- Death notification (not killer): `hilog.txt:35655` — `[ABR1882]Ability on scheduler died: 'org.ppsspp.ppsspp.PpssppActivity'`.
- Assessment: **exit verified; underlying exit caller unknown**. LoadLibrary failed at :33705: libppsspp_jni.so cannot resolve android_dlopen_ext. System.exit(-1) occurs about three seconds later (:35593); APPSPAWN code 255 is consistent with -1 modulo 256. The caught loader error is a candidate trigger, not a proven fatal chain or decoded exit callsite.

### toutiao

- Source: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-v1/20261001T120452-13a8b24d/61b0657200000000000000000324012c/toutiao/`
- Package `com.ss.android.article.news`; target PID `[23202]`; signed `dead`; group `java-main-threw-system-exit-1`.
- Identity: `hilog.txt:15466` names the exact child package and PID.
- First matched app terminal: `hilog.txt:70005` — `[stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.RuntimeException: Unable to instantiate activity ComponentInfo{com.ss.android.article.news/com.ss.android.article.news.activity.MainActivity}: java.lang.NullPointerException: Attempt to invoke virtual method 'boolean java.lang.Boolean.booleanValue()' on a null object reference`.
- Parent wait result: `hilog.txt:70208` — `[appspawn_service.c:118]com.ss.android.article.news with pid 23202 exit with code:1`.
- first_fatal root: `hilog.txt:70038` — `[stderr] Caused by: java.lang.NullPointerException: Attempt to invoke virtual method 'boolean java.lang.Boolean.booleanValue()' on a null object reference`.
- Death notification (not killer): `hilog.txt:70119` — `[ABR1882]Ability on scheduler died: 'com.ss.android.article.news.activity.MainActivity'`.
- Assessment: **verified Java terminal chain**. MainActivity constructor unboxes null Boolean (:70038, frame :70040). Target PID is present at t5 (:348), absent at t20. No user data or inputs were changed.

## Reproduce and validation

```sh
python3 benchmark/2026-10-01-u8-death-clusters/no-fatal-collect.py \
  --workspaces "$WORKSPACES" --output /tmp/no-fatal-terminations.json
python3 benchmark/2026-10-01-u8-death-clusters/no-fatal-tests/test_terminations.py
```

`termination_events.py` adds victim-bound APPSPAWN code/signal, manager notifications, memory-kill and watchdog/ANR matching without changing first_fatal or index/scoring contracts. Tests include unrelated victim/package, diagnostic-method strings, zero exits, ignored signals and warning-only ANR. Full raw logs are not copied into the public repo; all selected lines carry original coordinates.

Integration uses `no-fatal-landing-paths.txt` so the already-landed libandroid-copy listing is not overwritten. Documentation additions live in `no-fatal-evidence/documentation.json`. Validation receipts follow there; no board operation or new UI claim is made.

Validated against isolated master `f4ed880dd47b0c6284d5b44f84424d52d1fb9091` plus only these 11 new paths: 7 focused Python tests; 117 raw file hashes and 301 original coordinates; collector replay 11/11; spec gate exit 0 (raw Cargo 101, 192 passed, 9 approved exceptions, 0 unexpected); path gate exit 0 (12,452 files, 25 existing exceptions, 0 violations); known-answer suite 82 tests, 3 skips, exit 0; lifecycle 4/4 and fresh explain 3/3. Registry-only frozen check covers 8 entries but 0 deployed artifacts; the three original prediction CSV hashes are separately unchanged.

Retro-18 preflight: executed from this lane worktree using the canonical master `scripts/lab/land.py` (the lane lacks that new helper and merge is denied at `.git/ORIG_HEAD.lock`). It checks this lane’s listing/size/user-paths without copying or committing: **11 files, 0 too large, 0 user-path hits, exit 0**. Local staging is separately denied at `index.lock`; existing 12 staged U7 skeleton paths remain untouched. Outer landing remains required.
