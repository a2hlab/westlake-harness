# B1 build — input re-provisioning receipt (persistent) + remaining build steps

Outer ring assigned cc-wiki the B1 end-to-end rebuild (846 signatures for the 5 drifted functions + internal
callers; `abi_diff` exit 0, then the 5ea window). Part C/D's build inputs had been cleaned from temp dirs, so they
were re-fetched from hw248 to **persistent** locations (never temp again, per the 2026-10-01 rule). Source line +
SHA where applicable.

## Re-provisioned (persistent)
| input | persistent path | source | note |
|---|---|---|---|
| board 6.1.0.31 link libs | `$WORKSPACES/westlake-inputs/oh61-link-inputs/system-lib64/` (301 libs, SHA256SUMS, SOURCE.txt) | `hw248:/opt/build-runs/m1-full-generation-20260824-r43-icu76/meta/immutable-base/system/lib64` | 11/12 recipe `-l` libs verified present; `libnative_drawing.so` from DevEco sysroot (part D) |
| OH header mirror (OH_ROOT base) | `$WORKSPACES/westlake-inputs/oh61-oh-root/oh_mirror/` (13414 `.h`) | `hw248:/opt/wl-src/adapter/sources/oh61-v7-b2133b5b/local_oh_headers/oh_mirror` | the exact N2 mirror part C used (BR-8 prepend) |
| skia m133 headers | `$WORKSPACES/westlake-inputs/oh61-oh-root/oh610_lts_source/third_party/skia/m133/` (3080 `.h`) | `hw248:/opt/build-trees/oh610_lts_source` (headers-only) | |
| wukong100 gen headers | `.../oh610_lts_source/out/wukong100/gen/` (1193 `.h`) | same | jsoncpp + ibundle_mgr_ext (E6) |
| openssl generated include | `.../oh610_lts_source/out/wukong100/obj/third_party/openssl/build_all_generated/include/` | same | |
| window_manager libs | `.../oh610_lts_source/out/wukong100/window/window_manager/` | same | libwmutil(.base)/libsession_manager .z.so |
| minizip | `$WORKSPACES/westlake-inputs/oh61-oh-root/minizip/` (`libz.a` + `zlib-src/contrib/minizip/{unzip,ioapi}.c`) | `hw248:/opt/build-trees/oh610_lts_source/out/wukong100/obj/third_party/zlib/libz.a` + `third_party/zlib` | compile unzip.o/ioapi.o locally w/ DevEco clang at build time |

## Already local (no fetch)
- adapter source (build root): `$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b68-generation/adapter`
- libc++ `__h` headers: `$WORKSPACES/oh61-bms-kit-b79/prebuilts/clang/ohos/linux-x86_64/llvm/include/libcxx-ohos/include/c++/v1`
- resource_management: `$WORKSPACES/oh61-bms-kit-b79/base/global/resource_management`
- OH 6.3.1 overlay: `$WORKSPACES/westlake-harness-wiki/bms/src/adapter/build/oh_headers_631_overlay`
- generated mock session header: `.work/b68-generation/generated/imock_session_manager_interface.h`
- `$HOME/aosp`; DevEco SDK clang `/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native`

## Still to fetch (at link time)
- **aosplib** (AOSP `.so` for linking): `hw248:/home/alvin/westlake-generation-n2-*/payload/android/lib64` (part D `AOSP_LIB_DIR`). Fetch the specific `-l` AOSP set when linking (libnativehelper/liblog/etc.), not the whole payload.

## Remaining build steps (the actual rebuild)
1. **Assemble OH_ROOT** mirroring part C's `$PARTC/oh`: `oh_mirror` prepended (BR-8) + `oh610_lts_source`
   subtrees + oh61-bms-kit-b79 `foundation/` + overlay_631. Wire a `run.sh` with the env from part-D `run-link.sh`
   but pointing `OH61_LINK_INPUTS`→the new `system-lib64`, `OH_ROOT`→the assembled root, `BRIDGE_MINIZIP_DIR`/
   `BRIDGE_LIBZ_A`→the new minizip, `AOSP_LIB_DIR`→the fetched aosplib.
2. **Apply the 5-function 846-signature reverts** per `b1-revert-spec.md` to the `b68-generation/adapter` source
   (keep patch copies here for durability/landing). Verify each function still carries the evolved signature in
   this snapshot before reverting.
3. **Compile** (61 TUs, DevEco clang, `-nostdinc++ -isystem <__h>`); iterate on `-I` as part C did.
4. **Link** (strict `-z defs --no-undefined`, the new link inputs + minizip + aosplib) → B1 artifact.
5. **`abi_diff --old <846> --new <B1> --consumer <runtime> --json b1-abi-diff.json`** → must be **exit 0** (drift 0,
   consumer breaks 0). If non-zero, a function still carries an evolved signature → fix + rebuild.
6. Fill `t3-b1-board-run-plan.json` placeholders (B1 artifact path + sha256 into `t3-smoke-b1-5ea.json`) and open
   the 5ea window (after cc-t3's J10c unlock). The plan's `offline_precheck` now carries `expect:{confirm, refute}`
   (board_run rule 6ced77b7a).

## Status
- **Input re-provisioning: DONE** (all persistent; only aosplib deferred to link time).
- Next focused block: OH_ROOT assembly + the 5-function source reverts + compile/link + `abi_diff` exit 0.

## BUILD BLOCKER (2026-10-01, discovered at the revert step): the designated source tree is inconsistent
`ADAPTER_ROOT` from part-D `run-link.sh` = `$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b68-generation/adapter`.
That shared `.work` generation tree is now in a **non-buildable, mixed state** — it is NOT the clean source that
compiled 7cf8ebcc, and it has been mutated since part D (plausibly by other lanes' N10/N11 work in the same tree):
- `oh_window_manager_client.h` declares **one** `createSession` — the 5-int form `(…, androidWindowType, displayId,
  requestedWidth, requestedHeight, int androidFlags, uint64_t ohTokenAddr)` with **no default** on `androidFlags`.
- but `android-runtime/src/adapter_bridge.cpp:801` calls `createSession(…, requestedWidth, requestedHeight,
  ohTokenAddr)` — **4 ints, no `androidFlags`** → too few args → **would not compile** against that decl.
  (window_session_adapter.cpp:72/:149 DO pass the 5th int — so the callers disagree with each other.)
- the resolver ctor is in yet another shape: `ComponentResolverServiceV1(…, ResolveFaultInjectorV1*,
  ComponentStateReaderV1* stateReader = nullptr)` — a *defaulted* 4th param (3-arg calls compile, but the export
  still mangles 4-arg).
So b68-generation is a half-migrated tree: some call sites already on 846 arity, some on the evolved arity, decls
inconsistent — it will not build, and its ABI would not match 7cf8ebcc even if forced.

**Decision needed (outer ring): which source snapshot to build B1 from?** Options:
1. The exact source that produced 7cf8ebcc (part-D receipt cites the N2 "most-hits" recipe source; if archived on
   hw248 `/opt/wl-src/adapter/sources/oh61-v7-b2133b5b`, fetch it clean and apply the B1 reverts there);
2. A designated clean/pinned adapter source for the deployed bridge;
3. Reconcile b68-generation to a consistent state first (risky — it is shared/mutated by other lanes).
All build inputs (headers, link libs, minizip) are already persistent and ready; only the **source snapshot** is
blocked. Once confirmed, apply `b1-revert-spec.md` to that tree → compile → link → `abi_diff` exit 0.

## Source-tree reality (2026-10-01): no tree is clean-846; build from a private reconciled b68 copy
Verified three trees for the 5 drifted functions:
| tree | createSession | injectKey/Touch | component_resolver | state |
|---|---|---|---|---|
| pristine N2 `hw248:/opt/wl-src/adapter/sources/oh61-v7-b2133b5b` | 4-int (846) | 6-param (846) | **absent** (predates it) | consistent but INCOMPLETE vs 846 |
| 846 (frozen binary) | 4-int | 6-param | present: ctor 3-arg / Configure 5-arg | no clean source snapshot (B1 irreducible) |
| b68-generation (part-D ADAPTER_ROOT) / 7cf8ebcc | 5-int (+androidFlags) | 8-param (+ohEventId+`std::function`) | ctor 4-arg (+`ComponentStateReaderV1*=nullptr`) | has everything but EVOLVED past 846, and b68 is mid-revert/INCONSISTENT (won't compile) |

846 sits BETWEEN N2 and b68. N2 is too early (no component_resolver that 846 exports); b68 has every TU but all
three functions evolved past 846 and the tree is half-reverted (createSession decl 5-int but one caller already
4-int). So neither builds to 846 as-is.

**Chosen path (self-serve):** snapshot b68-generation into a PRIVATE copy (so other lanes' mutations to the shared
`.work` tree can't interfere), then COMPLETE the 846 revert there so all 5 functions + their callers are 846-arity
and consistent:
- createSession: decl→4-int (drop `androidFlags`); callers window_session_adapter.cpp:72 (drop `androidFlags`),
  :149 (drop `LEGACY_DEFAULT_FULLSCREEN_FLAG`); adapter_bridge.cpp:801 is already 4-int; drop
  `applyAndroidFlagsToWindowSessionProperty`.
- injectKeyEvent/injectTouchEvent: drop `ohEventId`+`std::function<void()>`; drop the EventCompletionRouter use;
  update oh_input_manager_bridge.cpp caller.
- ComponentResolverServiceV1 ctor + ConfigureComponentResolverRuntimeV1: remove the `ComponentStateReaderV1*`
  param (a `=nullptr` default still EXPORTS the 4-arg mangling, so it must be removed, not defaulted, for abi_diff
  exit 0) + drop `stateReader_` uses; update callers.
Then build (recipe + persistent inputs) → `abi_diff --old 846 --new B1` exit 0 → fill the plan → 5ea window.
