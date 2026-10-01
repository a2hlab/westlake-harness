# U8 no-first-fatal repair routing (offline)

## Correction before prescription

The adopted audit found **11 dead keys in five termination groups**, not eleven missing fatal lines. This plan has **4 primary J routes and 7 primary native routes**; it does not promise eleven newly lit apps. Two Mozilla SIGKILL senders remain unknown.

Three tempting J-only fixes are wrong or insufficient:

- **fd-plus:** U8 runtime JNI `nativeLockCanvas` at `0x197054` returns zero (`mov x0,xzr; ret`), and unlock at `0x19705c` does nothing. The AOSP Java guard is correct. Current Westlake's nonzero-pointer donor still locks no real buffer. Native repair must acquire, draw, post and release the actual buffer; swallowing the guard is not success.
- **toutiao:** earlier Application bootstrap fails on `libflipped.so → libstdc++.so` (hilog:30443), before the Activity's app-owned map lookup returns null Boolean. U8 **does have** identity-verified `libstdc++.so`; the defect is unresolved private loader closure. No C++ imports exist in this libflipped, making the existing SONAME-only shell a valid candidate for this particular edge, not a universal C++ runtime. The missing `enableGlobal` writer is not yet proven caused by that failure; never globally default `ConcurrentHashMap.get` to false.
- **Predicate / Locale:** J repairs concern BOOT-visible types/libcore, not automatically a runtime J10g JAR overlay. Predicate is a compatibility ABI absent from the copied AOSP14 core/java tree, not a recovered AOSP14 source class.

## Identity and source rule

Baseline: `RUNTIME e953c0921536`, `BOOTIMAGE 4db882a81732`. The immutable termination audit was adopted as `8f998d4199`. Only the seven signed sequential run roots are used, including `5cd-seq-v1-rest`; concurrent runs and later windows are excluded.

All selected AOSP files were hash-checked against the local same-tag `SHA256SUMS` (6611 entries). Tag: `android-14.0.0_r1`; frameworks/base HEAD: `299fe6f5d6fc6f1af7c3411dcf4e5efdf7217368`. libcore/bionic per-repository HEAD was not supplied, so it is not fabricated. `sources.json` includes original line snippets, SHA entries and separately labeled donor commits. The real-work donor is **not** an AOSP14 original and not proof of deployed code.

`artifact_identity` exits **0** for libhwui, liboh_android_runtime, libbionic_compat and libstdc++; exact hashes, DT_NEEDED and receipt are in `no-fatal-fixplan-evidence/native.json`. U8 compat exports android_set_abort_message already, but not android_dlopen_ext or __gnu_strerror_r. Native closure work must check consumer-domain visibility, symbol versions and singleton ownership, not only a global export list.

## Per-key repair table

Expected beneficiaries count **possible wall movement**, not termination cures or new screenshot-confirmed UI. Mozilla's count 2 is a shared loader-wall count; proven SIGKILL death unlocks = **0**. No counts are summed across overlapping native symbol repairs.

| Key | Primary / secondary layer | Wall | Wall beneficiaries | First evidence |
|---|---|---|---:|---|
| `cv2-com-nbossard-packlist` | J / none | legacy-predicate-boot-type | 1 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-cv2/20261001T122027-e3c3b085/5cd1e3dd00000000000000000923012c/cv2-com-nbossard-packlist/hilog.txt:41026` |
| `cv2-com-nononsenseapps-notepad` | J / none | self-provider-query-null | 1 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-cv2/20261001T122027-e3c3b085/5cd1e3dd00000000000000000923012c/cv2-com-nononsenseapps-notepad/hilog.txt:46916` |
| `fd-musicplayer` | J / native (libhwui color metadata) | bitmap-source-color-space-null | 1 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-v1/20261001T120453-7582ddda/5cd1e3dd00000000000000000923012c/fd-musicplayer/hilog.txt:42398` |
| `fd-plus` | native / J (retain existing guard and lifecycle) | software-surface-lock-zero-jni | 1 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-v1-rest/20261001T124951-f0a9fa0b/5cd1e3dd00000000000000000923012c/fd-plus/hilog.txt:75474` |
| `toutiao` | native / J (bind success/order; app-map writer unknown) | application-bootstrap-libstdcxx-closure-before-null-boolean | 1 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-v1/20261001T120452-13a8b24d/61b0657200000000000000000324012c/toutiao/hilog.txt:70038` |
| `cv2-com-kaajjo-libresudoku` | J / native (LocaleNative/ICU metadata if required) | locale-display-country-null-before-crash-activity | 1 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-cv2/20261001T122904-44eb39c6/61b0657200000000000000000324012c/cv2-com-kaajjo-libresudoku/hilog.txt:71629` |
| `fd-meet` | native / none | android-set-abort-message-not-visible | 1 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-v1/20261001T120453-7582ddda/5cd1e3dd00000000000000000923012c/fd-meet/hilog.txt:23949` |
| `ppsspp` | native / none | android-dlopen-ext-missing-before-exit-minus-one | 1 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-v1/20261001T120452-13a8b24d/61b0657200000000000000000324012c/ppsspp/hilog.txt:33705` |
| `cv2-com-bytehamster-flowitgame` | native / none | hwui-requires-khr-damage-extension | 1 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5ea-seq-cv2/20261001T122134-78628011/5ea34a4500000000000000001123012c/cv2-com-bytehamster-flowitgame/hilog.txt:53765` |
| `fd-fennec_fdroid` | native / none | mozglue-gnu-strerror-r-before-unknown-sigkill | 2 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/5cd-seq-v1/20261001T120453-7582ddda/5cd1e3dd00000000000000000923012c/fd-fennec_fdroid/hilog.txt:50267` |
| `firefox` | native / none | mozglue-gnu-strerror-r-before-unknown-sigkill | 2 | `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-u8-sweep/61b-seq-v1/20261001T120452-13a8b24d/61b0657200000000000000000324012c/firefox/hilog.txt:64194` |

## Repair and validation details

### cv2-com-nbossard-packlist — legacy-predicate-boot-type

**Repair:** Add exactly com.android.internal.util.Predicate<T> with boolean apply(T), erased apply(Object)Z. Reuse cc-t3 compatibility draft; app IOUtils$1 already implements behavior. Put it on an effective BOOT classpath, regenerate/check image visibility if stubs are image-bound; adding only J10g runtime jar is not proven sufficient.

**Call order / source:** `$WORKSPACES/westlake-harness-t3/benchmark/2026-10-01-j10-prep/src/Predicate.java:10`; `$WORKSPACES/westlake-harness-t3/benchmark/2026-10-01-j10-prep/src/Predicate.java:13`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/app/Application.java:346`.

**Acceptance probes (future window, not executed):**
- Resolve interface from the actual app parent class loader; IOUtils$1 loads and apply(Object) dispatches to its String implementation.
- Application.attachBaseContext/ACRA.init completes without Predicate/IOUtils linkage exception; only then assess t20 screenshot.

**Limit:** No original class exists in the copied AOSP14 core/java tree; compatibility ABI inferred from APK, not an AOSP14 donor. Historical removal-version claim not independently verified.

### cv2-com-nononsenseapps-notepad — self-provider-query-null

**Repair:** Install MyContentProvider with its authority, attachInfo/onCreate and live Transport before app UI; route acquireUnstableProvider/query to the actual provider SQLiteDatabase.query. Preserve projection, selection args, URI variants, cancellation and ref ownership. Do not return a fabricated empty Cursor.

**Call order / source:** `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/app/ActivityThread.java:6983`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/app/ActivityThread.java:7753`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/app/ActivityThread.java:7765`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/content/ContentResolver.java:1213`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/content/ContentResolver.java:1230`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/content/ContentResolver.java:1243`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/content/CursorLoader.java:72`.

**Acceptance probes (future window, not executed):**
- Record provider installation/authority acquisition and null stage; exercise content://com.nononsenseapps.notepad.MyContentAuthority/{task,tasklist,lists_with_count}.
- DrawerCursorLoader three COUNT(1) queries yield real one-row counts; list-with-count projection remains _id,count,title; valid empty data does not crash.
- Malformed URI and failed provider preserve legitimate failure semantics; run signed lit provider app as negative control.

**Limit:** Raw log proves null Cursor but not whether acquisition, query or remote failure returned null. AOSP CursorLoader is a lifecycle analogue; app uses AndroidX CursorLoader. J10g needs actual provider path audit, not generic query null suppression.

### fd-musicplayer — bitmap-source-color-space-null

**Repair:** Guard source.getColorSpace in createBitmap(source,...): only for a valid non-ALPHA_8 bitmap whose color metadata is missing, use ColorSpace.Named.SRGB before forwarding to createBitmap(..., colorSpace). Preserve known gamut/F16 metadata and the public explicit-null argument rejection. Audit libhwui Bitmap.nativeComputeColorSpace metadata as the deeper native fix.

**Call order / source:** `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/graphics/java/android/graphics/Bitmap.java:956`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/graphics/java/android/graphics/Bitmap.java:979`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/graphics/java/android/graphics/Bitmap.java:1203`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/graphics/java/android/graphics/Bitmap.java:1874`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/libs/hwui/jni/Bitmap.cpp:946`.

**Acceptance probes (future window, not executed):**
- Replay createScaledBitmap from an otherwise valid non-ALPHA_8 source with absent native color space; dimensions/pixels remain correct.
- ALPHA_8 retains allowed null color space; valid Display-P3/F16 is not replaced; public explicit null argument for non-ALPHA_8 still throws.
- Track art metadata and libhwui owner; t20 remains human-signed.

**Limit:** Config/color provenance must be checked before sRGB fallback; raw trace alone does not prove which native allocation discarded metadata.

### fd-plus — software-surface-lock-zero-jni

**Repair:** Fix runtime Surface.nativeLockCanvas to validate the Surface, lock a real ANativeWindow buffer, bind Canvas and retain the locked Surface reference. nativeUnlockCanvasAndPost detaches Canvas and unlocks/posts the same buffer; nativeRelease balances the retained reference. A nonzero pointer-only donor can avoid the guard but cannot prove rendering.

**Call order / source:** `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/view/Surface.java:473`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/view/Surface.java:506`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/view/Surface.java:510`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/view/Surface.java:512`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/jni/android_view_Surface.cpp:213`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/jni/android_view_Surface.cpp:222`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/jni/android_view_Surface.cpp:239`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/jni/android_view_Surface.cpp:255`; `$WORKSPACES/vm-copies/westlake-current/framework/android-runtime/src/android_graphics_compat_shim.cpp:274`; `$WORKSPACES/vm-copies/westlake-current/framework/android-runtime/src/android_graphics_compat_shim.cpp:287`.

**Acceptance probes (future window, not executed):**
- A successful lock produces nonzero mLockedObject and a real writable buffer; draw distinct pixels and verify posted output.
- Unlock without lock and double lock continue to throw; invalid Surface propagates an error; release count remains balanced.
- fd-plus refreshMapInternal no longer fails guard, then verify map pixels and t20 screenshot, not just process survival.

**Limit:** Deployed U8 lock function 0x197054 is mov x0,xzr; unlock at 0x19705c is ret. Current Westlake donor returns pointer but explicitly lacks real buffer and unlock is no-op. J guard is correct AOSP behavior, not the repair layer.

### toutiao — application-bootstrap-libstdcxx-closure-before-null-boolean

**Repair:** Make libflipped.so DT_NEEDED libstdc++.so resolve in its own app namespace. U8 already contains an identity-verified libstdc++.so SONAME-only shell; this libflipped imports no C++ symbols, so fix domain search/permitted placement rather than inventing a general C++ ABI. Then enforce successful Application.attachBaseContext/bind before Activity construction and verify app-owned enableGlobal population.

**Call order / source:** `$WORKSPACES/vm-copies/westlake-current/framework/appspawn-x/bionic_compat/src/libstdcxx_compat.c:5`; `$WORKSPACES/vm-copies/westlake-current/framework/appspawn-x/bionic_compat/src/libstdcxx_compat.c:11`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/app/LoadedApk.java:1458`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/app/Application.java:346`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/app/ActivityThread.java:6959`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/app/ActivityThread.java:6998`.

**Acceptance probes (future window, not executed):**
- Private namespace closure resolves libflipped and the shell without unrestricted inheritance; JNI_OnLoad/Flipped initialization succeeds.
- Application bind no longer logs FAILED; inspect actual X/A9Q.c writer before MainActivity DEX offset 0x46 Boolean.booleanValue.
- No global ConcurrentHashMap.get default false, Boolean rewrite or suppressed attach exception; constructor completes, then obtain signed screenshot.

**Limit:** 30443 is a proven earlier bootstrap dependency failure; it plausibly prevents map initialization, but the enableGlobal writer and causation to the later NPE remain unproven. libstdc++.so is deployed globally, not globally missing.

### cv2-com-kaajjo-libresudoku — locale-display-country-null-before-crash-activity

**Repair:** In boot Locale.getDisplayCountry, preserve primary and default-locale LocaleNative lookups, then return original countryCode if both return null. Keep empty-region behavior and valid translations unchanged. Audit LocaleNative/ICU separately; do not fake all language names or silently disable crash handler.

**Call order / source:** `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/libcore/ojluni/src/main/java/java/util/Locale.java:2173`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/libcore/ojluni/src/main/java/java/util/Locale.java:2185`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/libcore/ojluni/src/main/java/java/util/Locale.java:2187`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/libcore/ojluni/src/main/java/java/util/Locale.java:2189`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/libcore/ojluni/src/main/java/java/util/Locale.java:2538`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/libcore/ojluni/src/main/java/java/util/Locale.java:2539`.

**Acceptance probes (future window, not executed):**
- Both lookups null => original country code, never null; primary success and default success preserve result; empty region remains empty.
- ArrangementKt.getDisplayName / welcome screen no longer throws; CrashActivity is not required for normal start.
- Separately test crash-handler Activity start; do not infer caller of exit(0) across IPC gap.

**Limit:** Null String.isEmpty is mapped to country path at Locale.java:2539 in the exact 14r1 source. System.exit(0) follows a failed CrashActivity start, but exit caller itself was not decoded. BOOT/libcore replacement requires identity/image discipline.

### fd-meet — android-set-abort-message-not-visible

**Repair:** Expose one real android_set_abort_message implementation in the consuming private linker scope with compatible symbol version lookup. Reuse identity-verified libbionic_compat.so owner / real-work abort_message_compat.cpp; preserve first-message-wins and crash-tool magic layout. Do not replace it with a logging-only or no-op stub.

**Call order / source:** `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/android_set_abort_message.cpp:71`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/android_set_abort_message.cpp:76`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/android_set_abort_message.cpp:94`; `$WORKSPACES/01.OH61AOSP16/real-work/src/adapter/framework/appspawn-x/bionic_compat/src/abort_message_compat.cpp:42`.

**Acceptance probes (future window, not executed):**
- Resolve libc++_shared.so android_set_abort_message@LIBC before constructors; verify DT_NEEDED closure and one selected provider identity.
- Two messages retain first-message content; crash metadata is readable; null input handling follows documented compatible behavior.
- Meet loader no longer aborts at this import; subsequent React Native/Gecko symbols are separate walls.

**Limit:** U8 globally exports android_set_abort_message from libbionic_compat.so; missing relocation indicates consumer visibility/resolution, not absent implementation. Additional Meet libraries also import the symbol.

### ppsspp — android-dlopen-ext-missing-before-exit-minus-one

**Repair:** Implement Android android_dlopen_ext ABI on the native boundary: retain filename/flags/extinfo and caller context, implement supported FD/offset/namespace/reserved-address semantics or explicitly reject unsupported flags with a loader error. Check android_set_abort_message too. Do not unconditionally ignore extinfo and forward to dlopen.

**Call order / source:** `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libdl/libdl.cpp:68`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libdl/libdl.cpp:135`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libdl/libdl.cpp:137`.

**Acceptance probes (future window, not executed):**
- libppsspp_jni.so relocation for android_dlopen_ext@LIBC resolves in its declared scope.
- Test null extinfo ordinary dlopen plus supported FD/offset and invalid/unsupported flags, including namespace isolation and accurate dlerror.
- Check app actual call-site/extinfo usage; show the earlier loader error moved, then independently trace exit(-1) if it persists.

**Limit:** 33705 loader failure precedes System.exit(-1) at35593; it is not proven that repairing import removes the explicit exit. AOSP function forwards to __loader_android_dlopen_ext; do not copy the wrapper without a real backend.

### cv2-com-bytehamster-flowitgame — hwui-requires-khr-damage-extension

**Repair:** Prefer a real EGL damage extension only if advertised and callable. Otherwise adapt HWUI initExtensions and swapBuffers together: capability-aware KHR/EXT path, real full-frame eglSwapBuffers fallback with compatible buffer-age/damage bookkeeping and EGL error handling. Reuse Westlake EGL boundary fallback as a reference, not a complete HWUI gate repair.

**Call order / source:** `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/libs/hwui/renderthread/EglManager.cpp:305`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/libs/hwui/renderthread/EglManager.cpp:610`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/libs/hwui/renderthread/EglManager.cpp:613`; `$WORKSPACES/vm-copies/westlake-current/framework/android-runtime/src/oh_egl_boundary.cpp:79`; `$WORKSPACES/vm-copies/westlake-current/framework/android-runtime/src/oh_egl_boundary.cpp:94`.

**Acceptance probes (future window, not executed):**
- Absent KHR/EXT uses actual full-frame swap, no fatal init assertion; supported KHR/EXT still uses correct entry point and rectangles.
- Missing advertised function fails safely/falls back; EGL_BAD_SURFACE/BAD_NATIVE_WINDOW retain recovery behavior; no false extension advertisement.
- Verify rendered pixels and t20; signed lit HWUI apps stay lit.

**Limit:** APK has zero arm64 native members; consumer is deployed libhwui.so, which DT_NEEDs libEGL.so. Parent reported exit code134, not an observed signal6. Filtering extensions only under WESTLAKE_EGL_TEST_NO_DAMAGE in donor does not prove that environment existed in U8.

### fd-fennec_fdroid — mozglue-gnu-strerror-r-before-unknown-sigkill

**Repair:** Implement/export ABI-correct __gnu_strerror_r in the native compatibility scope: fill caller buffer with POSIX strerror_r semantics, preserve errno and return char* buffer. Verify libmozglue first; libxul also imports android_dlopen_ext/android_set_abort_message. Independently investigate SIGKILL sender with explicit victim evidence.

**Call order / source:** `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/strerror.cpp:188`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/strerror.cpp:205`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/strerror.cpp:207`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/strerror.cpp:208`.

**Acceptance probes (future window, not executed):**
- libmozglue.so __gnu_strerror_r@LIBC resolves; known/unknown/truncated error strings have correct pointer and errno behavior, never alias int-return strerror_r directly.
- Capture app/process-group death and explicit killer evidence if another SIGKILL occurs; do not label lmkd/AMS without a killing record.
- A moved swallowed loader error does not count as a cured SIGKILL or a new lit app.

**Limit:** Gecko swallowed loader exception precedes parent signal9, but causal link and sender are unknown. Only two-key loader-wall exposure is counted; death-unlock estimate remains unknown.

### firefox — mozglue-gnu-strerror-r-before-unknown-sigkill

**Repair:** Implement/export ABI-correct __gnu_strerror_r in the native compatibility scope: fill caller buffer with POSIX strerror_r semantics, preserve errno and return char* buffer. Verify libmozglue first; libxul also imports android_dlopen_ext/android_set_abort_message. Independently investigate SIGKILL sender with explicit victim evidence.

**Call order / source:** `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/strerror.cpp:188`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/strerror.cpp:205`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/strerror.cpp:207`; `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/bionic/libc/bionic/strerror.cpp:208`.

**Acceptance probes (future window, not executed):**
- libmozglue.so __gnu_strerror_r@LIBC resolves; known/unknown/truncated error strings have correct pointer and errno behavior, never alias int-return strerror_r directly.
- Capture app/process-group death and explicit killer evidence if another SIGKILL occurs; do not label lmkd/AMS without a killing record.
- A moved swallowed loader error does not count as a cured SIGKILL or a new lit app.

**Limit:** Gecko swallowed loader exception precedes parent signal9, but causal link and sender are unknown. Only two-key loader-wall exposure is counted; death-unlock estimate remains unknown.

## App-callsite evidence and shared native scope

`no-fatal-fixplan-evidence/dex.json` pins APK and per-DEX SHA with byte offsets. Packlist's `IOUtils$1.apply(Object)Z` delegates to an implemented String overload. Notepad's real `MyContentProvider.query` delegates to SQLite; `lists_with_count` and three `COUNT(1)` queries require actual row semantics, not a synthetic empty Cursor. Its loader is AndroidX; AOSP CursorLoader is only a call-order analogue. Musicplayer's createScaledBitmap trace maps to the exact 14r1 source forwarding a possibly null source ColorSpace; native Bitmap metadata provenance remains a prerequisite for a restricted J fallback.

Toutiao `MainActivity.<init>` uses `enableGlobal` then `X/A9Q.a` then `Boolean.booleanValue` at **byte offset 0x46**. `X/A9Q.a` is exactly ConcurrentHashMap.get; its static initializer creates an empty map and method `c` writes it. This does **not** identify the actual enableGlobal writer. AOSP order is Application creation/attach, provider installation, Application.onCreate, then Activity launch; do not continue to UI after failed bind.

ELF dynamic/symbol tables, not string hits, prove native consumers:

| Repair | Importing assigned keys | Count | Implementation requirement |
|---|---|---:|---|
| android_set_abort_message | fd-meet, ppsspp, fd-fennec_fdroid, firefox | 4 | Real first-message storage; current compat owner exists, consumer scope unresolved |
| android_dlopen_ext | ppsspp, fd-fennec_fdroid, firefox (libxul) | 3 | Real supported linker/extinfo semantics; fail unsupported flags explicitly |
| __gnu_strerror_r | fd-fennec_fdroid, firefox; fd-meet later (libjsi/libreactnative) | 3 | GNU char* buffer return with preserved errno; two Mozilla first walls plus Meet's later import exposure, not POSIX int alias |
| EGL_KHR_swap_buffers_with_damage | flowitgame via framework libhwui → libEGL | 1 | Real damage path or coordinated HWUI full-frame fallback; no fake extension |

Neither PPSSPP exit(-1) nor Mozilla SIGKILL is promoted from temporal proximity to proven cause. Flowitgame parent wait is exit code134, not an observed fatal signal6. Native proposals are real implementations or explicitly scoped compatibility SONAME shells, never generic success stubs.

## Handoff

Replays use the adopted U7/corpus-v2 input inventories; no private scratch manifest is required:

```sh
WORKSPACES="${WORKSPACES:?}" WESTLAKE_FIXPLAN_REPLAY=1 python3 \
  benchmark/2026-10-01-u8-death-clusters/no-fatal-fixplan-tests/test_fixplan.py -v
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc cargo test \
  --manifest-path tools/spec-checks/Cargo.toml --test u8_no_fatal_fixplan
```

The optional originals replay is skipped in portable fixture-only runs; the delivery's 9/9 replay included the real local AOSP/donor files, raw hilog, APK/DEX members and deployed library hashes. `sources.json` donor commits were independently checked with `git show <commit>:<path>` against their recorded file SHA. Native host-execution tests use the host compiler; known-answer ELF fixtures use `env-mac.sh`'s ELF compiler, never interchange them.

- **cc-t3:** J4 candidates (Predicate BOOT visibility, actual notepad provider path, narrowly gated Bitmap metadata fallback, Locale BOOT/libcore fallback). Do not count them as J10g effective until owner/classloader identity and replay are proven.
- **cx-t0:** native7 candidates and shared symbol closure; fd-plus needs actual Canvas buffer ownership, toutiao needs libflipped private closure plus J lifecycle success. Meet's abort owner already exists. No board window is authorized by this report.
- Raw line/SHA references and future acceptance probes are executable review inputs, not evidence that repairs have been implemented.
- Delivery manifest: `no-fatal-fixplan-landing-paths.txt`; retro18 preflight receipt in `no-fatal-fixplan-evidence/validation.json`. Additive README/DIGEST entries are in `documentation.json` to avoid copying unrelated lane edits.
