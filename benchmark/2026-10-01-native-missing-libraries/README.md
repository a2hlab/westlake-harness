# Four missing-library walls: pinned native handoff

## What was wrong; the new rule

The original LIBZ plan misread both SONAMEs as absent. The r109c alias really has **SONAME `libz.so`, DT_NEEDED `libshared_libz.z.so`**. U8 contains no `libz.so` in its manifest or payload inventory. Restoring a root alias would repeat the N8 regression; restore only the private alias and its dependency closure.

The Chessclock cluster named the wrong library. U8 `MediaPlayer.<clinit>` loads **`media_jni`**, then calls `native_init`; the APK has no native libraries. Adding `libmediandk.so` cannot repair this call. The generic media stubs in the old plans are not donors and are not copied.

U8's Android OpenSLES DSO exports two relevant extension IIDs but **no `slCreateEngine`**. Mindustry also logs that opening the real OH DSO from its app namespace is inaccessible. A manifest row or IID-only DSO is insufficient. The new rule is to prove the receiver, owner, complete consumer import set, namespace route and activation checkpoint separately.

## Evidence and proposed changes

`evidence.json` contains four APK hashes, exact ELF imports, PID-filtered original lines and the MediaPlayer DEX initializer. The collector runs `artifact_identity` before interpreting six deployed receiver/provider artifacts. OH audio is independently bound to U8's N2 system snapshot, not falsely included in the runtime fingerprint. The three plan files are checked both against their exported SHA256 and commit `e8903af49`.

| Component | Keys / fatal coordinates in `evidence.json` | Proposed files and effect | t20 |
|---|---|---|---|
| Private zlib | Element PID 23527: hilog 28197–28200 / 37819–37823; BurgerKing PID 26922: 69517–69519 / 69652–69654 | Restore `westlake_native/libz.so` and unchanged `libshared_libz.z.so`; exact package search/permitted prefix in host callback | unknown |
| OpenSLES owner | Mindustry PID 3208: 34208 inaccessible OH absolute path; 34210 / 34234 / 34265 missing engine | Add dependency-free `westlake_audio/libOpenSLES.so`, bind the real default-owner OH engine and IIDs before loading `libarc`; private prefix even for the non-private original ClassLoader route | unknown |
| Media JNI owner | Chessclock PID 26481: 34651 / 34674 registered methods; 39504 / 39508–39510 fatal chain | Add exact `libmedia_jni.so` → existing runtime mapping to JSON/header; resident-only SystemLoader lookup and activation log | unknown |

These are **four first-wall movement candidates**, not four promised new lit apps. Later walls and media playback remain unknown.

### Donors and closure

- Alias: `$WORKSPACES/01.OH61AOSP16/real-work/.state/build-oh-component-hw248/m1-route-a-generation-20260825-r109c-zlib-global/route-a-generation/pass1/zlib/libz.so`, 1,904 bytes, SHA256 `50b9ab6af637c8573736a595417f6177d5845d21fc48da5b8e1299a078b1e48d`. Recipe `real-work/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin/build_route_a_generation_in_container.sh:581`, commit `be16148da9ae7bb89c62e81e144ed0bceb5c4669`, source SHA `d11e2a71d416b586db245727a4bb2222b77df803621e3e271e13682320e75648`. Do not change the real provider's SONAME.
- Zlib provider: U8 `payload/android/lib64/libshared_libz.z.so`, SHA `ab0820c6a33c58f2b5aa6d7b5f967f0eae42319baa2d7a42b779d1583f8a14fc`, unchanged when copied into the private closure. BurgerKing imports `crc32`, which this provider exports. Element has a `DT_NEEDED` edge but no undefined symbol matching the checked zlib API family; do not infer absence of the dependency from that narrow symbol observation. The provider itself needs `libc.so`; **N2 must verify this edge against actual effective search/permitted paths, never inheritance**. Fresh findings need fresh outer approval, not an old exception recycled by hash.
- Real OH audio: U8 system snapshot `native/native-checks/system-elf/05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100`, same SHA, target `/system/lib64/libOpenSLES.so`. All four standard Mindustry imports are present; `SL_IID_BUFFERQUEUE` supplies the exact Android queue pointer through the facade. The backend is opened in `default`, **not** by adding broad OH system directories to app search. Its existing system closure stays in that owner.
- Media JNI owner: deployed runtime SHA `216b68fbb3a40b5ac7a90b726f6d8184fa7cdba848ccde56c809abd400a660df`; Chessclock's own PID already reports **49/49** registrations, `native_init=1 native_setup=1`, and no exported `JNI_OnLoad`. This is a registered **stub** implementation, not a real decoder. Source `real-work/src/adapter/framework/android-runtime/src/android_media_MediaPlayer.cpp`, tree commit `be16148da9ae7bb89c62e81e144ed0bceb5c4669`, SHA `a0ba386b451ae2ced2092d1dea7a81788a8c3740e13d1c5ce22928299b460994`. No new media methods or second runtime DSO are introduced.
- Deferred, **not this batch**: zigzag `libmediandk.so` SHA `110d02fc4bbb32ed241358c6329f6aa5e4849f021e5b224f9ae2b826f8fa75fb` exports presence provenance, no AMedia implementation. Its original plans target other clients; neither proves a Chessclock unlock.

## Integration for cx-t0

1. Read `source-bases.json` and `patches.json`. Every patch binds base and proposed SHA256. **The host base is U8's source snapshot SHA `7fe4369d26d5c832099177984a0d1fc7d75c0deabc40ef5f7237ab593ab2cd47`, also byte-equal to the N11 host-baseline copy; it is not the older main-tree host.** Materialize that base at the patch target in scratch, apply with `patch --fuzz=0 -p1`, then rebase onto the actual N10b/U9 build input preserving its fixes. Never overwrite a newer host wholesale. Policy/loader bases are the master snapshot recorded in `source-bases.json`, not an assertion that source files alone are deployed evidence.
2. Place `missing-library-route.h` and `opensles-owner.h` on the host include path and retain the build's `-D_GNU_SOURCE` for `Dl_info`. Apply `stock-host.patch`; it augments exact Element/BurgerKing/Mindustry package-component paths before namespace creation, and binds audio after namespace inheritance but before returning to the native consumer. The pre-existing `native_private` JNI-owner activation predicate uses the **original** search prefix: adding zlib search visibility does not newly activate an unrelated runtime preload. Unrelated packages, including substring lookalikes, remain unchanged.
3. Apply **all four** media patches: JSON, header, SystemLoader and policy checker; rebuild **`libnativeloader.so`**, including every same-generation payload/route copy. The checker changes exactly one permitted logical alias tuple, not arbitrary SONAME/path mismatch; app callers, noncanonical paths and realpath redirects retain rejection. SystemLoader uses `RTLD_NOLOAD` only for the registered runtime alias, after it is already mapped. Its log is `[U9-MEDIA-OWNER] ... resident-only=1`.
4. Stage pinned payload additions in scratch:

   ```sh
   python3 benchmark/2026-10-01-native-missing-libraries/stage_overlay.py \
     --workspaces "$WORKSPACES" --output /tmp/u9-missing-library-overlay
   ```

   This outputs **only an overlay**, refuses an existing destination, and deliberately does not create a deployable package. Merge its three `files` rows into the next native package and matching `live_hashes`, rebuild host/loader and all N1/N2 sidecars, and retain source/patch/toolchain receipts. Never add `/system/android/lib64/libz.so` and never replace the global Android OpenSLES IID shim; the new facade is **Mindustry-private**.
5. The 3,904-byte AArch64 facade is encoded in `facade.so.b64`, SHA **`82a70946bd4ec6885207d6987e992465c026e77e0000bedb2556bd6b68c0c871`**. Two fresh builds match. `build-facade.sh` reproduces it with a pinned OH compiler; `facade-build.json` pins compiler, linker, compiler headers and sources. `-Bsymbolic` keeps its internal IID writes in this facade rather than an older same-named global object. It has **zero DT_NEEDED** and covers exactly all five `libarc` OpenSLES imports, not the full Android multimedia API.
6. `abi-diff.json`: exit **0**, five exports added, two API IID objects retained at size 8, zero signature drift and zero consumer breaks. Removed `_init/_fini` are CRT hooks, not client APIs; no constructor is used. The matching OH SDK/Android NDK engine prototypes plus host forwarding tests establish the six C arguments; `abi_diff` alone cannot infer unmangled C parameter types.
7. After rebuilding, require `deploy_generation` preflight, **N1/N2 exit 0 or freshly approved exact findings**, candidate artifact identities, and outer authorization. Copy the top-level `offline_precheck` fragment from `offline-precheck.json` only after those conditions hold; its three per-component fragments define distinct positive/negative observations. This file **does not authorize a window**.

## Activation and negative controls

- Zlib: target PID `[U9-LIB-ROUTE] ... root=/system/android/lib64/westlake_native`, private alias/provider maps and resolved `crc32`, then no old libz fatal chain. Check HelloWorld/ZigZag to guard the former root-alias regression.
- Audio: target PID `[U9-SL-OWNER]`, exact `dladdr` paths for OH engine and private binder, queue pointer equality, one OH backend loaded instance, then `libarc` relocation succeeds. Missing engine/IID, wrong owner, inaccessible path, failed binding or conflicting rebinding is a failure, never a fake successful engine. No changes are applied to PPSSPP or unrelated apps.
- Media: target PID `[U9-MEDIA-OWNER]`, same registered owner and native_init/Ringtone checkpoint with no manifest denial or additional runtime instance. The host test executes the actual patched SystemLoader with mocked filesystem/sealed-open operations; namespace type is only forward-declared, not emulated. It tests trusted/untrusted callers, redirect, supplied path, absent resident owner, deferred mediandk rejection and unchanged ICU behavior.
- **t20 needs signed screenshots**. Logs, an exported function, process survival and the constructor checkpoint do not establish own UI or real audio playback.

## Validation

Run `python3 .../test_handoff.py` and the three `native_missing_library_*` Rust selectors. Final counts, isolated-master `spec_checks.py`/path-gate exit codes, lifecycle verdicts, listing hash and index-lock outcome are in `validation.json`. No board was accessed, no frozen prediction CSV was changed, no push was made.
