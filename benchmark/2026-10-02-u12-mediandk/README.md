# U12: typed NDK media error boundary, not a working media engine

## Correction and original evidence

The two keys do **not** share a missing-library wall. Treating Chessclock as a `libmediandk` beneficiary was wrong. Window5 Subwaysurfers PID 3245/TID 3271 reports `libunity.so` needing `libmediandk.so` at original hilog **44187–44192**, then SIGABRT at **44194**, `libmain.so!FatalError+0x4dc0` at **44360**. Chessclock PID 2315 reports manifest ULE at **43043–43055**, `MediaPlayer.<clinit>:620 -> Ringtone -> ChessClock`. The actual framework SHA `3e106350…` / classes2 DEX `93c42bc9…` initializer loads **media_jni**, then calls `native_init`. See `observations.json`, PID-bound excerpts and `evidence/MediaPlayer-clinit.json`.

The existing reviewed media_jni alias/owner work is separate. This candidate predicts **one conditional loading-wall movement (Unity), zero demonstrated new lights, zero Chessclock benefit**. Exact next fatal/checkpoint/t20 are unknown. Resolving media imports is not evidence that Unity handles a missing decoder gracefully.

## Sources and implementation boundary

Local upstream `vm-copies/westlake-current` has no NDK media implementation/history (`evidence/upstream-mediandk-history.txt`). The only local donor is the deliberately API-free `mediandk-presence.c`, not a media implementation. Read-only a2hlab queries timed out; hw248 SSH was sandbox-denied. Outer supplied the hw248 sparse TUNA-mirror checkout, copied read-only to `$WORKSPACES/westlake-inputs/aosp-14.0.0_r1-src/frameworks/av`: tag `android-14.0.0_r1`, commit **402dbe885fd58af75e4c1d7e790fbf4bb22f29f9**. All **65** checksums were independently verified and snapshots are admitted in `inputs/aosp14/`, pinned by `sources.json`.

Original `media/ndk/include/media/NdkMediaError.h:70` defines `AMEDIA_ERROR_UNSUPPORTED = -10002`, **not -1002** from the earlier plan. Header prototypes are taken from the actual 14r1 source, not an SDK23 header. `api.json` records all **50** actual Unity imports, original prototype/header SHA/line and behavior. Opaque foreign handles have only forward declarations; no OH/Android object-layout casts. AArch64 `off_t=8` and `AMediaCodecBufferInfo=24` are asserted.

Full AOSP `NdkMediaExtractor.cpp:64` needs NuMediaExtractor/JNI, `NdkMediaFormat.cpp:38` needs AMessage, and codecs need Stagefright/Binder services. Copying these alone would not provide a functional route-A media stack. The permitted candidate is a correctly typed error boundary: codec and image construction produce no object, status operations return unsupported, buffer getters return NULL with size zero, output object pointers are cleared, no decoder/window/image is fabricated. Pointer/bool/count/time/void APIs use their typed failure form rather than returning the same integer everywhere.

DataSource owns a real callback holder and retains callback/userdata; delete does not invoke close (compare AOSP `NdkMediaDataSource.cpp:184`, `:220`, `:228`). Extractor owns only an explicitly unconfigured object and cannot select/read tracks. Format owns a real int32 property list with allocation/update/free; other property getters fail without inventing values. These small containers are not ABI-compatible AMessage/Stagefright objects and are never passed to those engines. `AImage_deleteAsync` closes a transferred fence; no image is produced. Unsupported diagnostics are `[U12-MEDIA-UNSUPPORTED] function status=-10002`.

## Candidate and publication

- Provider **8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58**, two identical OH clang builds, SONAME `libmediandk.so`, NEEDED **libc.so only**, exports **1 -> 52** (50 consumer APIs, Format_new, retained provenance symbol). Raw receipts: `build-receipt.json` and `evidence/build*.txt`.
- New target **`/system/android/lib64/libmediandk.so`**. No root copy existed. The old private zigzag presence copy SHA **110d02fc…** remains deliberately unchanged; `deployed_whois` reports it never mapped in its U9 coverage. That U9 report is historical, not proof of window5 provider ownership.
- Actual deployed U10.1 loader **0718f01e…**, independently hash-checked in **both route and root aliases**. Precise 5-system-library / 7-shared-SONAME source snapshot is `inputs/native-loader/`. `policy.patch` adds one trusted root mediandk row, **5 -> 6**, and changes its constexpr array bound. Shared table **7 -> 7** (mediandk already shared), SoundPool retained, `system_loader.cpp` untouched, no media_jni alias, no default fallback.
- Comparison policy **2a6ec73fd87239ae90ba6464727649f5a4d73aab7588dda392df8803c2e76c4e**, two identical builds. It is **not** a byte-exact reproduction of the frozen Linux loader. Both route/root aliases must be rebound together after that final rebuild. `policy-receipt.json` pins source and recipes; no deployment is enabled here.

## Static gates and remaining admission blocks

Provider baseline/candidate and loader deployed/candidate each have **0 open sites / 0 namespace edges**, no MULTI-NS or DEFAULT-NS. The provider adds no namespace behavior. Provider ABI: removed/drift/consumer breaks/call diffs all **0**; 51 additions explicitly allowlisted. This ABI comparison preserves the old presence symbol; **independent import enumeration** establishes coverage of all 50 media imports, not ABI diff alone. Loader ABI exports 7 -> 7, all four differences 0; libopenjdk consumer checked.

Strings: provider **1 drop / 32 add** (truthful provenance label and unsupported diagnostics); each needs outer review in `strings-review.json`. Loader rebuild vs actual deployment **0/0**, candidate vs actual deployment **0 drop / 1 add**, exactly `/system/android/lib64/libmediandk.so`. No SoundPool deletion. No JAR modified, so deployed_class_diff is not applicable.

Focused provider N2 resolves its sole libc NEEDED and **7/7 strong undefineds** against factory libc **fd3c4701…**, no inherit and no unresolved symbol. This explicit root+factory-libc search model is **not a live namespace proof**. Full package N1/N2 baseline **PASS**; candidate **REJECT** because the **103 identical private-domain findings** have no exceptions registered for the new manifest. New provider N1 findings **0**. Evidence: `namespace-gates.json`, `provider-closure.json`, raw `evidence/native-*.txt`. Reject is retained, not silently waived. Frozen loader build, exception rebind, live root-provider selection and remaining Unity import closure are mandatory admission blocks. Private presence copy is not a functional provider and must not be mistaken for the new root one.

## Reproduce offline

Set WORKSPACES/OHOS_SDK if needed. Run `collect.py`, `generate.py`, `build.py`, `policy.py`, `namespace_gates.py`, `report.py`, `finalize.py` with Python3. Compiler/linker/library/source hashes and full captured commands are retained. Large ELF products and raw outputs stay in persistent worktree `.artifacts/` (not admitted to git). Re-run frozen Linux policy build before release. Tests compile admitted C/headers in a fresh temporary directory and do not require `.artifacts`.

`offline_precheck.json` supplies confirm/refute expectations but **execution_enabled=false**. No device command, package deployment or compat-scope modification occurred. N11h 18:36:57 was refuted (two owner load-bases remain); that evidence does not authorize guessing compat relocation scope. Outer reviews this delivery before any later scope work.
