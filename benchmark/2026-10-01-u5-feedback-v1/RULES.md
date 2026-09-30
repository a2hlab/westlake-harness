# U5-feedback-v1 rule catalog

Static risks and observed training signatures are separate. All calls/imports below are requirements, not proof of startup execution or first-wall order.

## flutter-jni-field-id

- Observed signature: `fid == null + GetLongField + FlutterJNI.nativeRunBundleAndSnapshotFromLibrary`.
- Static condition: DEX invoke instruction referencing FlutterJNI runBundleAndSnapshotFromLibrary or nativeRunBundleAndSnapshotFromLibrary.
- Requirement: FlutterJNI native field IDs must be initialized before GetLongField; DEX presence does not prove a null ID.
- Known missed keys: `fd-fluffychat`, `fd-immich`, `fd-libre`, `fd-saber`.
- All static matches (6): `fd-fluffychat`, `fd-immich`, `fd-kitchenowl`, `fd-libre`, `fd-saber`, `localsend`.

- `fd-fluffychat`: `classes.dex sha=6eeceea6b967 method=a5.a.i:(La5/a$b;)V offset=0035 dexdump-line=1363676`; original U5 log lines `28453,28455,28456,28458` (full witnesses in results.json).
- `fd-immich`: `classes.dex sha=4e53ee99dc9b method=h7.b.c:(Lf7/D;)V offset=002e dexdump-line=1232789`; original U5 log lines `32880,32882,32883,32885` (full witnesses in results.json).
- `fd-libre`: `classes.dex sha=37ce12950d75 method=bh.run:()V offset=0258 dexdump-line=203944`; original U5 log lines `41197,41199,41200,41202` (full witnesses in results.json).
- `fd-saber`: `classes.dex sha=1db6cfc2f1e2 method=fj.a:(Ln4;)V offset=002b dexdump-line=462514`; original U5 log lines `38961,38963,38964,38966` (full witnesses in results.json).

## private-runtime-reload

- Observed signature: `Flutter private preload libandroid.so + Xpm check failed for liboh_android_runtime.so, errno for mmap is: 22`.
- Static condition: FlutterJNI bundle invocation AND private westlake_flutter/libandroid.so DT_NEEDED liboh_android_runtime.so.
- Requirement: Private preload must reuse the resident runtime in its effective namespace; neither file presence nor DT_NEEDED proves XPM failure.
- Known missed keys: `fd-kitchenowl`, `localsend`.
- All static matches (6): `fd-fluffychat`, `fd-immich`, `fd-kitchenowl`, `fd-libre`, `fd-saber`, `localsend`.

- `fd-kitchenowl`: `payload/android/lib64/westlake_flutter/libandroid.so sha=ee2fb82c6351`; original U5 log lines `30190,30318,30465,30480,30490,30495,30509,30521` (full witnesses in results.json).
- `localsend`: `payload/android/lib64/westlake_flutter/libandroid.so sha=ee2fb82c6351`; original U5 log lines `25830,26180,26189,26204,26213,26218,26232,26244` (full witnesses in results.json).

## realm-libz

- Observed signature: `Error loading shared library libz.so (needed by librealm-jni*.so or librealmc.so)`.
- Static condition: AArch64 Realm consumer has DT_NEEDED libz.so.
- Requirement: Resolve libz.so in the actual Realm consumer namespace, not merely in the package.
- Known missed keys: `fd-im-vector-app`, `mcdonalds`.
- All static matches (2): `fd-im-vector-app`, `mcdonalds`.

- `fd-im-vector-app`: `lib/arm64-v8a/librealm-jni.so sha=7693a9d21679`; original U5 log lines `40538,40540,40555,50157,50159,50160,50216` (full witnesses in results.json).
- `mcdonalds`: `lib/arm64-v8a/librealm-jni.so sha=7693a9d21679`; original U5 log lines `37692,37712,37717,37726` (full witnesses in results.json).

## vibrator-lock

- Observed signature: `Null reference used for synchronization + SystemVibratorManager.getVibratorIds`.
- Static condition: DEX invoke Vibrator/SystemVibrator.hasVibrator()Z or VibratorManager/SystemVibratorManager.getVibratorIds()[I.
- Requirement: Construct a non-null SystemVibratorManager lock before monitor-enter; invocation does not establish the producer state.
- Known missed keys: `fd-app`, `fd-shatteredpixeldungeon`.
- All static matches (15): `fd-android`, `fd-app`, `fd-etar`, `fd-fitness`, `fd-k9`, `fd-minetest`, `fd-netguard`, `fd-plus`, `fd-shatteredpixeldungeon`, `fd-stk`, `mindustry`, `ppsspp`, `subwaysurfers`, `toutiao`, `x`.

- `fd-app`: `classes.dex sha=bc6c0c544c92 method=com.badlogic.gdx.backends.android.AndroidHaptics.<init>:(Landroid/content/Context;)V offset=002d dexdump-line=586961`; original U5 log lines `39077,39092,39093,39111,39123,39124` (full witnesses in results.json).
- `fd-shatteredpixeldungeon`: `classes.dex sha=4b1042a743ba method=h0.<init>:(Lp;)V offset=002b dexdump-line=1354357`; original U5 log lines `23034,23049,23050,23067,23079,23080` (full witnesses in results.json).

## mozglue-strerror

- Observed signature: `relocating failed dso=libmozglue.so s=__gnu_strerror_r`.
- Static condition: libmozglue.so strong undefined __gnu_strerror_r.
- Requirement: Provide __gnu_strerror_r in the libmozglue load scope; megazord is a different consumer.
- Known missed keys: `firefox`, `fd-fennec_fdroid`.
- All static matches (2): `fd-fennec_fdroid`, `firefox`.

- `firefox`: `lib/arm64-v8a/libmozglue.so sha=dda52952be2a`; original U5 log lines `59412` (full witnesses in results.json).
- `fd-fennec_fdroid`: `lib/arm64-v8a/libmozglue.so sha=723bff3716e6`; original U5 log lines `45884` (full witnesses in results.json).

## ppsspp-dlopen-ext

- Observed signature: `libppsspp_jni.so: android_dlopen_ext: symbol not found`.
- Static condition: libppsspp_jni.so strong undefined android_dlopen_ext.
- Requirement: Provide android_dlopen_ext in the libppsspp_jni load scope.
- Known missed keys: `ppsspp`.
- All static matches (1): `ppsspp`.

- `ppsspp`: `lib/arm64-v8a/libppsspp_jni.so sha=8956cbe542ac`; original U5 log lines `33885` (full witnesses in results.json).

## jitsi-abort-message

- Observed signature: `libc++_shared.so: android_set_abort_message: symbol not found`.
- Static condition: libc++_shared.so strong undefined android_set_abort_message.
- Requirement: Provide android_set_abort_message in the libc++_shared load scope.
- Known missed keys: `fd-meet`.
- All static matches (9): `burgerking`, `fd-im-vector-app`, `fd-meet`, `fd-minetest`, `fd-mpv`, `fd-plus`, `toutiao`, `vlc`, `x`.

- `fd-meet`: `lib/arm64-v8a/libc++_shared.so sha=3e852764502d`; original U5 log lines `36246,36248,36256,36258,36262,36264` (full witnesses in results.json).

## Input layer

| Category | Keys |
|---|---|
| split-key | burgerking, firefox, mcdonalds, subwaysurfers, x |
| non-aarch64-sidecar | fd-seal, toutiao |
| apk-pin-mismatch | subwaysurfers |

Subway retains both split and pin-drift flags. `noice` and `x` have null apps.json pins, resolved from metadata; null is not a mismatching pin. `fd-client` has one APK and seven DEX files: multidex is not split.

## Re-evaluation criterion

For each risk, require the exact consumer/API signature in an APK/sidecar/generation-bound target PID. JNI and Java causal context must also share a TID. Absence of a signature is unknown, not a pass; require positive execution beyond the matching operation to show crossing. Earlier failures mask later risks. Evaluate t20 independently by the outer reviewer's actual screenshot, never from process survival. Input-blocked keys are excluded from runtime-wall scoring until their input identity is repaired and re-frozen.
