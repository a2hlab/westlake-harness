# liboh_adapter_bridge.so COMPILE-header dependency manifest & single-directory verdict

> Round 3 of the "single-directory buildable" line (2026-07-10). Round 1 closed
> SYSROOT (OH SDK), round 2 closed LINK inputs (`third_party/oh_stubs/`, 27 stubs,
> parity-verified). This round closes the **COMPILE** dimension and records the
> decisive verdict. Companion: `third_party/oh_stubs/STUBS_MANIFEST.md`,
> `../inner/compile_oh_adapter_bridge_arm64.sh` (INCS_OVERLAY_631 + round3 header).

## 0. Binding constraint (user, 2026-07-10, final form)

> The final build must be self-contained in THIS adapter directory
> (`/opt/21.Game/02.unity.cardwords/adapter`); **no OTHER external code may enter
> a compile unit — EXCEPT OH source + AOSP source, which MAY be external** (may be
> compiled / patched / linked against). The external compiler/toolchain is allowed.

Forbidden in compile units: Noice (`/opt/1F`), WestLake adapter mirrors
(`/opt/10` HanBing/Yue **adapter** trees, incl. `local_oh_headers/oh_mirror`),
GZ05 host adapter/third-party code. Allowed external: OH source tree, AOSP source
tree, toolchain.

## 1. VERDICT — A (ACHIEVED)

`liboh_adapter_bridge.so` **truly compiles and strict-links** in the single
directory under the sanctioned OH/AOSP-external exception:

- **39/39** `.cpp` → `.o` (zero failures).
- **strict** link (`-Wl,--no-undefined` equivalent; NO relaxed fallback) →
  **1.4 MB `liboh_adapter_bridge.so`**, `ELF 64-bit LSB / AArch64`, 32 `DT_NEEDED`
  (26 OH platform libs + `libnativehelper` + `libhwui` + `libEGL` + `liblog` +
  `libc++`/`libc`), 465 UND (all runtime-resolvable against the device's real OH
  platform libs — a D600 *is* OpenHarmony).
- **Compile units contain ZERO non-OH/non-AOSP external code.** Confirmed input
  inventory in §2. Host cross-compile on darwin; device-independent.

Verified twice, two independent OH source trees:
- Probe A ($OH = Yue arm64 build tree + its `oh_mirror`): 39/39 + strict ELF64.
- Probe B ($OH = HanBing OH source tree ALONE, **no oh_mirror**, in-dir overlay
  only): 39/39 + strict ELF64 — proves the WestLake `oh_mirror` (13k device
  headers) is **NOT required**; the 4 in-dir overlay headers replace it.

**Toolchain qualification (honest — addresses codex adversarial review):** the
"39/39 + strict ELF64" holds for the compile in EITHER of two forms — (i) the
external OH tree's OWN clang + the in-dir `libcxx_compat.h` as-is (historical
Linux path), or (ii) the OH SDK clang + a 4-block recalibration of that shim (see
§4). The one combination that does NOT compile is **unmodified in-dir shim + SDK
clang** (all 39 fail on the `std::__promote` clash); do not read "39/39" as a
claim about that combo. So A = "single-directory compilable **given** (a) the
external OH tree carries a built `gen/` and (b) a libcxx-matching toolchain" — an
OH/AOSP-and-toolchain-qualified A, not an unconditional one. codex found **no**
hard reason to downgrade to B; 32 DT_NEEDED / 465 UND only mean runtime/device
viability is a separate, still-unproven question, which does not overturn
"compilable."

## 2. Compile-input inventory (what enters each `.o`)

| Class | Source | External? | Compliance |
|---|---|---|---|
| Bridge `.cpp` (39) | `framework/{core,activity,window,surface,broadcast,contentprovider,package-manager}/jni/` | IN-DIR | ✓ |
| Adapter headers | `framework/**` | IN-DIR | ✓ |
| HWUI/skia compat shim | `framework/hwui-shim/skia_compat_headers/` (149 h) | IN-DIR | ✓ |
| bionic→musl libcxx shim | `framework/appspawn-x/bionic_compat/include/libcxx_compat.h` | IN-DIR | ✓ (see §4 caveat) |
| **6.1.0.31 interface overlay (4 h)** | **`build/oh_headers_631_overlay/`** (this dir) | IN-DIR | ✓ |
| OH inner_api / foundation / base / commonlibrary / third_party | external OH **source** tree `$OH_ROOT` | external OH | ✓ exception |
| skia m133 (`include/core`, `include/codec`, `include/effects`, `include/utils`, `modules`, `client_utils/android`) | `$OH_ROOT/third_party/skia/m133` (OH third_party) | external OH | ✓ exception |
| OH **generated** headers (gen/) | `$OH_ROOT/out/<board>/gen/**` (OH build artifact) | external OH | ✓ exception (see §3) |
| AOSP (`libnativehelper` jni.h, `system/core`, `liblog`, `libbase`, `androidfw`, `hwui`, `fmtlib`, `incfs`) | external AOSP **source** tree `$AOSP_ROOT` | external AOSP | ✓ exception |
| Compiler + musl sysroot + builtins | OH SDK aarch64 clang++ 15.0.4 (6.1.0.105/api23) | external toolchain | ✓ allowed |

Reference trees actually used for verification (any equivalent OH/AOSP tree works):
- OH source (complete, has skia+platform+gen): `/opt/10.Project/16-WestLake/16.12-HanBing/oh` — `sdk_version = 26.0.0.18` (api24 generation), built `out/rk3568/gen` (4726 gen headers, mtime 2026-04-17).
- AOSP source: `/opt/10.Project/16-WestLake/16.13-Yue/local-arm64-build-YUE/aosp-arm64-d600`.
- Toolchain: `/opt/17-TestLab/17.03-D600/apps/d600-sdk-full/native` (SDK 6.1.0.105, clang 15.0.4).

## 3. Generated headers (gen/) — provenance & the ONE residual "floor"

The bridge's `-I` set includes 3 OH **generated** header dirs (IDL/GN codegen):
`.../gen/foundation/window/window_manager/wmserver`,
`.../gen/foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_core`,
`.../gen/third_party/jsoncpp/jsoncpp-1.9.6/include`. These are **OH build-time
artifacts** (produced by running GN/ninja over OH `.idl`/gyp inputs), NOT static
source.

Under the current constraint this is **fully compliant** and NOT a blocking floor,
because the user's rule explicitly permits building the external OH source tree
("生成头也可以在外置 OH 源码树里 build 产出"). The verification trees already
carry a built `gen/` (HanBing `out/rk3568/gen`), so no on-the-fly OH build was
needed here.

The only honest residual: **REGENERATION** of gen/ from pristine OH source (if a
tree without a prior build were used) requires running the OH build once. That is
an OH-tree operation (allowed), not a violation. If a fully build-free path is ever
demanded, the 3 gen dirs (~tens of headers) can be vendored into this overlay as
static artifacts with provenance — but that is optional convenience, not required.

## 4. Known compile gaps this round closed (in `compile_oh_adapter_bridge_arm64.sh`)

1. **Overlay was UNWIRED.** The README promised an `INCS_OVERLAY_631` segment that
   did not exist in the script. On an OH tree older than the device (api24 vs
   6.1.0.31) this caused 8 `override hides virtual` errors:
   - `app_scheduler_adapter.h` — `ScheduleMemoryLevel` (2→1 params), 6 TUs.
   - `session_stage_adapter.h` — `NotifyAppForceLandscapeConfigEnableUpdated`
     (1→0 params), 2 TUs.
   Fixed by prepending the overlay. **Include LEVEL matters**:
   `session_stage_adapter.h` includes `"session/container/include/zidl/..."`, so
   the `-I` must be the `window_scene` PARENT, not the `zidl` leaf.
2. **skia roots incomplete** — added `include/codec`, `include/effects`,
   `include/utils` (needed by `skia_codec_register.cpp`, `color_space.h`).
3. **skia dangling-symlink fallback** — some OH checkouts symlink
   `third_party/skia/m133` to a `/mnt/mac/...` Linux bind-mount form that dangles
   off-Linux; added an `R3_SKIA_ROOT` real-path fallback.
4. **`pixel_map.h` / `event_handler.h`** — added OH `graphic_2d/rosen/modules/
   platform/{image_native,eventhandler}` `-I` (ws_common / display_manager /
   input_manager chains).

**SDK-libcxx skew caveat (NOT fixed here — out of scope file):** under the SDK
clang, the in-dir `libcxx_compat.h` polyfills (`std::__promote`, `std::span`,
`isinf`/`signbit`/…, `std::abs`) clash with the SDK's newer libcxx-ohos
(`_LIBCPP_VERSION` 15004) which already provides them. Resolutions: build with the
external OH tree's OWN clang (shim matches, historical path), OR recalibrate the 4
shim blocks to no-op when the libcxx already ships the symbol. See the script's
round3 header block.

## 5. Overlay contents (4 device-6.1.0.31 interface headers, unchanged this round)

- `.../app_manager/include/appmgr/app_scheduler_host.h`
- `.../app_manager/include/appmgr/app_scheduler_interface.h` (`ScheduleMemoryLevel` 2→1)
- `.../window_scene/session/container/include/zidl/session_stage_stub.h`
- `.../window_scene/session/container/include/zidl/session_stage_interface.h`
  (`NotifyAppForceLandscapeConfigEnableUpdated` 1→0)

Provenance & "明确不包含" caveats: see `README.md` in this directory and root
`PROVENANCE.md`. These are OH interface declarations (device-version snapshot);
they encode the 6.1.0.31 ABI shape the adapter overrides against.
