# U14 app-ns public libs — build staging: Wall-2 fix selection (option b) + Wall-1 candidate reproduce plan

Static analysis + build staging, offline, board #90, **no board access** (OH libs read from a local snapshot, not a
locked board). Follows `2026-10-03-u14-appns-public-libs`. Two deliverables: ① the safety criterion that picks the
Wall-2 fix, and ② the located, validated, launch-ready reproduce+patch build for the Wall-1 candidate.

## ① Wall-2 fix selection — option (a) is UNSAFE, use option (b) (evidence/wall2-selection.txt)
The Android app process maps **both** ICU stacks (U12 stage-A `maps-t5-*.txt`, e.g.
`window1/.../helloworld/maps-t5-28322.txt`):
- ours: `/system/android/lib64/{libicuuc,libicui18n,libicu_jni}.so` (ICU 72, data `/system/android/etc/icu`);
- OH's: `/system/lib64/platformsdk/{libhmicuuc,libhmicui18n,libintl_register,libintl_util,libglobal_resmgr}.z.so`.

Scanning the OH libs (local snapshot `westlake-inputs/oh61-link-inputs/system-lib64/platformsdk`, **no board access**):
`libhmicuuc.z.so` **reads `/system/usr/icu`** and requires **ICU 74** (`icudt74l`, `u_setDataDirectory_74`,
`udata_setCommonData_74`). So `/system/usr/icu` is shared between tttext and OH's own ICU. **Option (a)** (per-app remap
of `/system/usr/icu` to an ICU-72 dir) would feed `icudt72l` to `libhmicuuc`, which expects `icudt74l` → **breaks OH ICU
(resmgr/intl/i18n) inside the app process. Rejected.**

**→ Option (b): add `_74` alias exports to our Android `libicuuc.so`** (`recipe/wall2-b-icu74-alias.md`). Only callers
that dlsym the `_74` names (tttext) are affected; OH's `libhmicuuc` keeps its own `_74` + its 74 data. The alias set is
small and stable — `ubrk_open/close/first/next/setText`, `u_charType`, `u_hasBinaryProperty` (all break-iterator /
property C API, all in libicuuc). Build: re-link libicuuc with an alias object (`.set <sym>_74, <sym>_72`), keeping the
`_72` cohort; one library, no second copy. Caveats (enumerate the real dlsym set from relocations; handle the
`icudt74l_dat` data symbol; 72-code-answering-74 is safe only for the stable C ABI) and the honest alternative (c1:
align our Android ICU to 74 since OH already is) are in the recipe.

## ② Wall-1 candidate — located, validated, launch-ready (evidence/build-staging.txt)
**Fix artifact corrected again:** the `dlns_inherit` patch compiles into the **`appspawn-x` host executable**
(`westlake_stock_host_main.c` → `build_stock_host` → `appspawn-x-stock`, pass1/pass2 byte-repro built in), **not**
`libapp_native_loader.so` and not the child `.so`.
- **Base to reproduce (pinned):** the U13 deployed host `appspawn-x` =
  `2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e`
  (`u13-final-assembly/.artifacts/bundle-v3/native/payload/runtime/appspawn-x`). (Not r3 `65cc3535`, not n11h `65ac5089`.)
- **Toolchain validated on hw248:** `/opt/wl-src/.work/product-tls-generation` + frozen `clang-15` present. The direct
  recipe is Linux-only (checks `/etc/os-release`) → build on **hw248** (a2hlab reserved for the U13 executor during the
  lock window, per the outer 02:35).
- **Patch:** `recipe/win-u14-appns-public-libs.patch` (context-verified at the `dlns_inherit` site, line 217) adds the
  AOSP public sonames `libicui18n.so:libicuuc.so:libGLESv2.so:libGLESv3.so:libvulkan.so:libjnigraphics.so` to the
  app↔bridge inherit; `libandroidio.so`/`libjavacore.so` excluded.
- **Launch-ready plan:** (1) reproduce `2a87118e` UNPATCHED ×2 (the N10b faithfulness gate — if it does not match, STOP
  and report the delta, do not build on an unfaithful base); (2) apply the patch, build PATCHED ×2; (3) acceptance vs
  base: `open_site_scan` unchanged, `deployed_strings_diff` differs ONLY by the added soname string (+ the one
  LOGI/branch), exports/undefined identical; (4) persist + record shas.

**Why staged, not built this turn:** a faithful reproduce of `2a87118e` needs the **exact U13 host source snapshot** +
its `frozen.sha256` env; `u13-final-assembly` records no host repro receipt, and the N10b discipline explicitly rejects
a reproduction built from a near-miss source (n11h: "a reproduction using a different source basename is not an accepted
baseline"). The one input to confirm is that U13 host source snapshot. With it, the monitored hw248 build is a mechanical
single-instance run (small: a few `.c` + link, pass1/pass2). This mirrors the staged-then-built pattern used for the JIT
compiler (`2026-10-02-toutiao-jit-build`).

## Prediction table (by first-fatal)
| key | needs | after the fixes |
|---|---|---|
| **toutiao** | Wall 1 (libicui18n visible) **and** Wall 2 (ICU 74↔72 via option b) | lit only with both |
| **fd-stk** | Wall 1 only (libGLESv2 via libSDL2) | lit with Wall 1 |
| **subwaysurfers** | Wall 1 only (libGLESv3 via libvkquality) | lit with Wall 1 |
| fd-fluffychat/fd-immich/fd-kitchenowl/fd-saber/localsend | U13 `18763dd4` (GetLongField) first; Wall 1 is their 2nd wall | — |

## Files
- `evidence/wall2-selection.txt` — the maps + OH-lib scan proving option (a) unsafe → option (b).
- `evidence/build-staging.txt` — the fix artifact (appspawn-x host), the pinned base `2a87118e`, toolchain on hw248, the
  launch-ready reproduce+patch plan, and the one input to confirm.
- `recipe/win-u14-appns-public-libs.patch` — the Wall-1 patch (context-verified).
- `recipe/wall2-b-icu74-alias.md` — the Wall-2 option-(b) `_74` alias build approach + caveats + the (c1) alternative.
- `results.json`, `landing-paths.txt`.

## Boundaries
Offline; **no board access** (respecting the 02:35 lock window — OH libs came from a local snapshot). The appspawn-x host
build is the runtime/appspawn owners' to deploy; this stages a candidate. Sources read read-only from
`westlake-harness-bms`, `westlake-inputs`, `vm-copies/apks-77`, `westlake-harness-u7-executor`; hw248 inputs probed
read-only.
