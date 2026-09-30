# N6: Flutter window boundary through the existing route-a implementation

The earlier GL-missing attribution was wrong. N5 LocalSend PID 16312 already mapped
platformsdk EGL/GLESv3 and Mali. Its raster-thread stack enters platform
`eglCreateWindowSurface` and dies in vendor `ANativeWindow_getFormat`.
The nearby `/system/lib64/libGLESv3.so` warning comes from OH EGL's
`FindBuiltinWrapper`; that function has a driver fallback. It is not proof that
GL was unavailable. See `source-evidence/n5-localsend-stack.txt` and the preserved
N5 maps/hilog in `../2026-10-01-n5-window/`.

## Existing route and candidate

Ordinary framework EGL JNI (`native-checks/egl.cpp`) unwraps its Java Surface's
AdapterAnw using `oh_anw_get_oh` before calling EGL. HWUI has the equivalent
native boundary in sections 4/5 of real-work
`src/adapter/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp`, commit
`be16148da9ae7bb89c62e81e144ed0bceb5c4669`, SHA `f3913dd335d8bd1a0a651def3239d3a41821879ac8f82d6ae9be2a842e7b89a8`.
The preserved source exactly matches that checkout. R155 HWUI is the signed U5
`be59260f` artifact; we do not rebuild it.

`src/flutter_egl.cpp` copies that existing window conversion, successful-create
owner bookkeeping, successful-swap notification and successful-destroy erasure.
Adaptations: omit pixel-readback diagnostics and their GL imports; use the
already visible logging entry point rather than add a hilog dependency. No
surface is forcibly destroyed, no EGL error is synthesized, no missing function
is treated as success. The R155 lazy function-resolution behavior is retained.

Candidate `westlake-generation-n6-b70b3d00` (beside this worktree), manifest
`423ea1ff84627c71d445bbfef18766cba9646421bc0d73d94ab07389d1110d16`, is based on
N5 `b446d8db`. Exactly one payload differs from N5:
`payload/android/lib64/westlake_flutter/libwestlake_native_abi.so`, SHA
`b70b3d0001772d181d99a7e9e964149e98557f6eced0ab50f5fa167e3b996391`.
The non-Flutter `westlake_native` copy stays `d2053066`; host, ANL, runtime,
platform EGL/GLES, JAR, installer and boot images stay unchanged from N5.
Relative to U5 this is the two N5 ANL aliases plus one Flutter-private ABI.

The existing host selects this ABI only for the six Flutter package paths.
The old ABI already has `DF_1_GLOBAL`; N6 retains it and adds four `LIBEGL`
exports. OH musl's `decode_dyn` and `add_can_search_so_list_in_dso` make that
object available during engine relocation. **Actual engine binding remains a
required device observation**, not a conclusion from the export table.
Require `[OH_EglHijack] detected ANW shim ... unwrapped ...` in the Flutter
process, a surface result, and t20 screenshots. A wrapper that never executes
has not tested the intended repair. EGL/GLES driver identities must stay the
same; the missing absolute-path warning may persist independently.

## Checks and remaining gate

- Same frozen OH clang `b107ce03`; VM direct build previously authorized.
- Strict link (`-z defs`, `--no-undefined`, fatal warnings); two identical builds.
- Eight deterministic window/owner paths exercise the copied production code.
- All 26 old exports retained; four EGL exports added. Twelve new strong imports
  have definitions in exact libc/libc++ inputs. N5 already maps this libc++.
- Frozen registry check passes; no frozen source changed.
- N1 rejects 28 and N2 rejects 156 findings. No gate relaxed and no exception
  installed. `EXCEPTION-PROPOSAL.md/json` bind 184 rows to this candidate and
  complete inputs: 126 U5-common, 57 N5 traversal, one new libc++ edge.
- Deployment dry-run must reject before Board access until outer approval.

The superseded draft `westlake-generation-n6-1f6549ae` adds an unnecessary hilog
edge and is **not for deployment**. Only `b70b3d00` is proposed.

## Predictions and authorized-window protocol

All six Flutter apps are predicted to pass the N5 dependency layer; window
translation may move LocalSend's raster failure past native-window setup.
Plugin, texture, Vulkan and rendering failures remain possible; no UI success
is predicted as certain. HW/ZZ/aegis/catima should retain U5 behavior.

After candidate-bound outer exception approval: lock 5ea for <=30 minutes,
read boot/U5 fingerprint and J6 receipt, collect U5 samples for the six targets
with early process maps, then expose the package JAR only for transactional
native deployment and restore J6. Run HW/ZZ first, then six Flutter targets and
aegis/catima using master batch `--reinstall --hilog 20 --shots 5,20` (controls
use their manifest). Compare each app against same-board U5: adapter bridge,
runtime, appexecfwk base, liblog, bionic compat inode counts **and payload SHA
sets must not gain duplicates**. Missing baseline maps are unknown, not a pass.
LocalSend's known U5 two-inode liblog is allowed only as that observed baseline.
Collect EGL/GLES/libc++ identities and wrapper-dispatch logs too.

Any control regression or newly duplicated singleton stops the window. Restore
`westlake-generation-n4-order-216b68fb` using the captured U5 rollback state,
restore J6 `2488052f`, verify runtime `73ecf422dba2` and bootimage `0876029078e2`,
and unlock. Use explicit state receipt rather than an inferred generation name.
Post raw facts, t20 paths and first fatal stack for external visual review.

**Current status: offline only; no N6 device writes, no N6 screenshots, runtime
binding and rendering unverified.** Gate exceptions need approval before a
concrete deployment command is enabled; no bypass flag is provided.

## Subsequent approved experiment

The one-time window is complete; N6 is not accepted. See [window evidence](../2026-10-01-n6-window/README.md). LocalSend still reaches platform EGL directly; copied private entry binding remains unverified. U5 was restored and the grant revoked.
