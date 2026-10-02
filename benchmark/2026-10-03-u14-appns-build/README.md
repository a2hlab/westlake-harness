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

**Build host + source corrected (outer 02:47/02:53):** the U13 host `2a87118e` was built **on the Mac** with DevEco
clang (not the hw248 Linux recipe), and its source + reproduce receipt are in `benchmark/2026-10-02-u12-private-zlib/`
(`build.py` + `build-receipt.json`: candidate1 = candidate2 = `2a87118e`; source `candidate-stock-host.c` =
`u11-native-batch/.artifacts/r1/host`, sha `507bf160`; link recipe = `MASTER/benchmark/2026-10-01-u10-bundle`). All
inputs validated present on this Mac. **The deployed source has the multi-owner inherit logic** (not the clean worktree
copy), so the patch is revised against `candidate-stock-host.c` (bridge inherit, line 330); see
`evidence/libz-and-deployed-inherit.txt`.

**Why staged, not built this turn:** the patch had to be re-derived against the real deployed source + reconciled with
the libz/private-zlib interaction this turn. With that settled, the Mac build is mechanical: run the `u12-private-zlib`
logic UNPATCHED ×2 → reproduce `2a87118e` (N10b gate; stop on mismatch) → apply the revised patch to
`candidate-stock-host.c` ×2 → `deployed_strings_diff` = only the added soname string; `open_site_scan` sites/edges
unchanged. Mirrors the staged-then-built JIT pattern.

## libz / Element (outer 02:53) — already handled by U13's private zlib; keep it out of the public-lib set
Element (`im.vector.app`) fails on `librealm-jni.so` → `libz.so` ENOENT **in U10.1T8**. `libz.so` is AOSP-public, but
the U12 **private zlib** (`U11ZlibRoot`, `zlib-route.h`) already prepends `westlake_native` (with `libz.so` `50b9ab6a`)
to the app search path for **exactly `{im.vector.app, burgerking}`** — Element is enrolled. So **U13 (host `2a87118e`)
already fixes Element's libz**; the U10.1T8 report predates the private zlib. The public-lib patch therefore **excludes
`libz.so`**: the enrolled apps get it from the private-zlib prefix (`LOCAL_NS_PREFERED`, one copy), and adding it to the
inherit too would let the platform libz load as a **second copy** (the outer's double-libz constraint). GL/ICU libs are
safe to add even where a private app also inherits `libGLESv3` via `system_owner` — both edges point at the one DEFAULT
copy, so the linker dedupes; only libz has a separate provider, hence the exclusion.

## Prediction table (by first-fatal)
| key | enrolled? | first-fatal | needs |
|---|---|---|---|
| **toutiao** | no (normal path) | libicui18n.so ENOENT | **Wall 1** (public-lib inherit) **and Wall 2** (ICU 74↔72, option b) — both |
| **fd-stk** | no | libGLESv2.so (via libSDL2) | Wall 1 |
| **subwaysurfers** | no | libGLESv3.so (via libvkquality) | Wall 1 |
| **Element / fd-im-vector-app** | yes (native_private) | libz.so (via librealm-jni) **in U10.1T8** | **already fixed in U13** (private zlib `{im.vector.app, burgerking}`); NOT via the public-lib patch |
| mcdonalds | yes (native_private) | `_ctype_` (bionic/musl libc), **after** libz | a different wall (bionic `_ctype_`); its libz already resolves |
| fd-fluffychat/fd-immich/fd-kitchenowl/fd-saber/localsend | — | GetLongField/AAssetManager (U13 `18763dd4`) | U13 asset fix first; Wall 1 is their 2nd wall |

## ③ Where mcdonalds's libz came from — the bridge (outer 02:53), so libz exclusion is safe
mcdonalds (native_private, **not** in `U11ZlibRoot`) doesn't bundle libz, yet its `librealmc.so` loaded libz and died at
`_ctype_` (a bionic libc symbol missing in OH musl — a separate compat wall). The deployed `libnativeloader.so` (which
assembles `bridge_shared_sonames`) contains `libz.so`, and the `if (wants_bridge)` bridge inherit runs for **every** app
— so **libz is already universal via the bridge**. The private zlib (`westlake_native/libz.so`, crc32) is a *fuller* libz
for `{im.vector.app, burgerking}` whose realm/mmkv needs crc32, prepended to win (`LOCAL_NS_PREFERED`).
**So excluding libz from the patch creates no second copy** — libz is already provided by the bridge for everyone; the
patch doesn't touch it. The only libz duplication is the intentional private-zlib coexistence for those two apps, which
predates and is independent of this patch. (`evidence/libz-and-deployed-inherit.txt` §3.)

## Build targets — both pinned, Mac DevEco clang (next step)
- **Wall 1 (host):** `benchmark/2026-10-02-u12-private-zlib/build.py` reproduces `2a87118e`; apply the revised patch to
  `candidate-stock-host.c` (bridge inherit, line 330).
- **Wall 2 (libicuuc):** U13 deployed `libicuuc.so` = `f74827d9`; faithful recipe local at
  `benchmark/2026-10-03-u13-compat-ctype/` (`build.py` + `build-receipt.json`). Reproduce `f74827d9` ×2, then re-link with
  an alias object exporting the 7 `_74` names tttext dlsyms (`ubrk_open/close/first/next/setText`, `u_charType`,
  `u_hasBinaryProperty` → their `_72` impls); `nm -D` diff = only those 7 aliases.
Both reproduce-gates must pass byte-identical before patching (N10b); stop + report on any mismatch.

## Wall-1 reproduce gate + patch — RAN; semantically faithful but NOT byte-localized to the path (evidence/host-reproduce-gate.txt)
I replicated the host build in this dir (`recipe/reproduce_host.py`: read-only recipe
`MASTER/benchmark/2026-10-01-u10-bundle/r2-host-build-receipt.json` + DevEco clang + sysroot/reused-objects referenced by
`$WORKSPACES`; sources read-only in `./inputs`, outputs in `./.artifacts`; no board, no a2hlab). **Correction to my
earlier "path-only" claim:** on the outer's (a) instruction I listed every differing byte — and the delta is **not**
confined to the path strings.
- my-unpatched (`87ffee1f`) vs `2a87118e`: same size 646760, **136010 bytes differ** — `.debug_*` ~126187 (allowed by
  (a)), but also **`.rodata` 8766 + `.text` 737** (not allowed). Same-length path replacement fixed only **37** bytes.
- **Root cause:** clang orders `.rodata` string literals **by content**; the `__FILE__` path strings differ in *content*
  (wiki/bms, u14/u12), so they sort to different positions → the whole `.rodata` string pool shifts **+460 bytes** →
  `.text` address-reference immediates (all 374 diffs are `theirs = mine + 0x1cc`, no opcode change) and jump tables
  shift. So (a)'s own section criterion (".text et al byte-identical, only path rodata differs") **fails**.
- **Semantic checks (the right lens — address shifts are noise):** `abi_diff` exports **15/15, 0 added/removed/drift/
  breaks → ABI identical**; `deployed_strings_diff` → the **only** real differences are the 2 build paths
  (`candidate-stock-host.c`, `resident-compat.h`); `.rodata` string **set identical** (497≡497). So the code, ABI, and
  string set are identical — the only real difference is the embedded build-input **path content**.

**Patch validated semantically** (my-patched `341c1260`, ×2 identical, vs my-unpatched — both from my path so it cancels):
`deployed_strings_diff` → the **only** new string is `libicui18n.so:libicuuc.so:libGLESv2.so:libGLESv3.so:libvulkan.so:libjnigraphics.so`;
`abi_diff` → exports 15/15, **0 change**. (Raw byte-diff is pervasive only because the added `snprintf` block grows
`.text` by 568 bytes and shifts addresses.)

**Decision for the outer.** Byte-identity to `2a87118e` needs u12-private-zlib's exact input **path content** (clang's
content-ordered string pool makes any path-content change non-local) = **(b)**, which is **ruled out** (don't touch
cx-bms). The achievable result is **(A′): accept semantic faithfulness** (ABI identical + string-set identical + only
the build path differs) + the semantic patch validation above — U14 host candidate = `341c1260`. I did **not** widen the
acceptance bar myself; `341c1260` stands or falls on the outer's (A′)-vs-byte-identity call. **Wall-2 (`libicuuc
f74827d9`, `u13-compat-ctype/build.py`) has the same path-content consideration — not started pending that call.**

## Files
- `evidence/wall2-selection.txt` — the maps + OH-lib scan proving option (a) unsafe → option (b).
- `evidence/wall2b-collision-judgment.txt` — why option (b) does NOT collide with OH `libhmicuuc`'s real `_74` (ns +
  RTLD_LOCAL isolation), and the b′ fallback.
- `evidence/build-staging.txt` — the fix artifact (appspawn-x host), the pinned base `2a87118e`, the Mac build
  toolchain/recipe/inputs, and the launch-ready reproduce+patch plan.
- `evidence/libz-and-deployed-inherit.txt` — the real deployed multi-owner inherit structure, the private-zlib scope
  `{im.vector.app, burgerking}`, the Element/libz answer, and the double-libz exclusion.
- `recipe/win-u14-appns-public-libs.patch` — the Wall-1 patch, **revised against the deployed source**
  (`candidate-stock-host.c`, bridge inherit line 330), libz excluded.
- `recipe/wall2-b-icu74-alias.md` — the Wall-2 option-(b) `_74` alias build approach + caveats + the (c1) alternative.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; **no board access** (respecting the 02:35 lock window — OH libs came from a local snapshot). The appspawn-x host
build is the runtime/appspawn owners' to deploy; this stages a candidate. Sources read read-only from
`westlake-harness-bms`, `westlake-inputs`, `vm-copies/apks-77`, `westlake-harness-u7-executor`; hw248 inputs probed
read-only.
