# R155 device-runtime build recipe (vendored from the b6-r155 snapshot)

This is the **original author's build recipe** for the route-A R155 runtime that ships on the boards
(libart `59e1bb45…`, boot.oat kv `concurrent-copying=false`). It was found locally in
`westlake-harness-bms-deploy/bms/src/.work/b6-r155/` — a directory covered by `.gitignore`'s `.work/`,
so **it was never in the repo**. Vendored here so the R155 build method is not locked to a `.work/` dir that
can be cleaned (same lesson as DIGEST B6 "为什么慢" / E.7 — recipe + toolchain hashes must be in the repo).

Author original paths (one-time read-only vendor, recorded in `knowledge/gates/user-path-exceptions.json`):
`/opt/10.Project/16-WestLake/16.12-HanBing/adapter` (per `adapter/PROVENANCE.md`), project
`/opt/21.Game/02.unity.cardwords`.

## The three companion pieces (compile_report.html §3.6/§3.8/§4.1.1 + appendix C/H)

| piece | how it is built | read-barrier / GC |
|---|---|---|
| **host dex2oat64** | AOSP **Soong** + env `ART_USE_READ_BARRIER=false ART_DEFAULT_GC_TYPE=CMS` (`build-host.sh`) | RB off, CMS |
| **device libart.so** | hand-written cross-compile, **NOT Soong** — `adapter/build/inner/cross_compile_arm64.sh` `ART_DEFS` (line 201), `bld art` (line 768) | RB off, CMS |
| **boot image (27 files)** | `adapter/build/inner/gen_boot_image.sh` using the host dex2oat64 (`$AOSP_ROOT/out/host/linux-x86/bin/dex2oat64`) | inherits host dex2oat |

The device-libart `ART_DEFS` (verbatim, line 201) defines `-DART_DEFAULT_GC_TYPE_IS_CMS` and `-DNDEBUG` and
**does NOT define** `-DART_USE_READ_BARRIER`, `-DART_USE_GENERATIONAL_CC`, or any heap-poisoning macro. That
absence is the read-barrier-OFF switch — it is what makes `concurrent-copying=false` and lets the board load
the image. (04-15 the recipe was "CMS + RB"; **04-16 evening it was retracted** — RB forces CC+Region GC,
which crashes on OH: the kernel has no `userfaultfd` and MC is unusable. See build_patch_log appendix H.)

**[B-5] rule (from `gen_boot_image.sh`):** *libart / dex2oat / boot image 三件套必须联动重编,禁单独改其一* —
`boot.art/.oat/.vdex` are produced by dex2oat, which statically links libart; changing a GC/RB/layout macro on
libart alone leaves the boot image's validation info inconsistent → the board rejects/breaks it. This is
exactly the T6 failure mode we observed on 5cd (RB-on image → zygote SIGILL).

## Cross-check vs the board (libart `59e1bb45…` binary evidence + v3c boot.oat kv)

All five compile-time switches in this recipe match what the board runtime actually is:

| switch | recipe (cross_compile_arm64.sh) | board R155 (cx-bms binary evidence @59e1bb45) | boot.oat kv (v3c) | verdict |
|---|---|---|---|---|
| read barrier | `ART_USE_READ_BARRIER` **not defined** → off | `ValidateOatFile@0x461bb4` reads `IsConcurrentCopying`, `@0x461bb8` `tbnz`→reject; expects **false** | `concurrent-copying=false` | **verified** |
| GC type | `-DART_DEFAULT_GC_TYPE_IS_CMS` | `XGcOption` default writes `collector_type=2`; `collector_type.h` enum 2 = **CMS** | (implied by RB off) | **verified** |
| generational CC | not defined → off | constructor clears `+6 generational_cc` = false | — | **verified** |
| heap poisoning | no poisoning macro → off | heap-reference plain `ldr`, passed to `IsMarked`, not negated → poisoning off | — | **verified** |
| debug build | `-DNDEBUG` | `VMRuntime_vmLibrary` returns the `libart.so` string, `kIsDebugBuild=false` | `debuggable=false` | **verified** |

Other boot.oat kv (v3c ref, 8 keys total): `compiler-filter=speed`, `native-debuggable=false`,
`requires-image=true`, `apex-versions=(empty)`, `bootclasspath=<9 jars>`, `dex2oat-cmdline=<D600 path>`.
No difference found — the recipe reproduces the board's compile-time configuration item-by-item.

## Inventory
- `adapter/build/` — 303 files (all build scripts/headers/manifests, text; the trio scripts are in
  `adapter/build/inner/`: `cross_compile_arm64.sh` `fd306585…`, `gen_boot_image.sh` `c7d8e3dc…`).
- `build-host.sh` `168d99fa…`, `build-child.sh` `53d00b25…`, `build-declarations.h` `cd4797f9…` (b6-r155 top level).
- `adapter/PROVENANCE.md` `3e59f95b…` — the author's own vendor provenance.
- `SHA256SUMS` — 307 rows (every vendored file).
- `upstream-manifest.md` — the upstream trees the recipe consumes (OH 6.1.0.31 + AOSP r1), listed not vendored.

Full hashes in `SHA256SUMS`. This recipe is the authority for the `dex2oat-once` spec's **device libart** step
(see `specs/dex2oat-once/`), which points at `cross_compile_arm64.sh`, not a Soong `target libart`
(oc-t4's T3b Soong `target libart` is a comparison artifact only — T5b's boot image is made by the host
dex2oat64, which is Soong+env and matches this recipe).
