# Toutiao-line pre-build: JIT compiler (libart-compiler.so) — validated + staged on hw248, build is the next step

Offline, board #90. De-serialize the toutiao JIT path: the build doesn't need a board, so stage it now and — the
moment the long-wait window shows "pure slow" — go straight to a board round instead of waiting for a build. This round:
located every input, reconstructed the faithful recipe, moved the host to hw248 per the outer, and **validated patch24
against the hw248 tree**. The compiler build itself is a monitored single-instance job run next (not executed this turn).

## BUILD COMPLETE (outer chose (a)) — all three artifacts built, self-deterministic
The outer chose **(a)**: accept `08026ab6` as the control (route-A ships no libart-compiler.so on the board, so the
stale B6 `3c8e76a2` is just a reference; the current tree is byte-verified faithful and differs only by a
`logged_primclass_guard` diagnostic added after `3c8e76a2` — artifact-vs-source drift). On that same tree, patch24 was
applied and the JIT artifacts built on hw248 (`evidence/build-complete.txt`), all **self-deterministic** (two
independent fresh builds byte-identical each):
- **control** `libart-compiler.so` = `08026ab6…` (3895952 B)
- **patched** `libart-compiler.so` = `64fead06…` (3895936 B) = control + patch24. Acceptance vs control: **exports 0 diff,
  undefined 0 diff, readable-strings 0 diff**; only `jit_compiler.o` .text changed (−16 B) — exactly patch24, nothing else.
- **memfd shim** `libwestlake_jit_anon.so` = `bceae6fc…` (13248 B): exports only `_ZN3art12memfd_createEPKcj`
  (version-scripted); `__android_log_print`/`dlsym` resolve at runtime from the LD_PRELOAD host.

**N1/N2 preview** (list only, not `--apply`): the compiler's NEEDED is the standard ART lib set (incl. `libart.so` =
board 59e1bb45) and its 653 undefined `art::` symbols resolve from that `libart.so` + `libartpalette` + `libc++` (the
compiler-is-a-libart-plugin relationship); the shim NEEDs only `libc.so`. The full gate (resolve vs the deployed 59e1bb45
+ any exceptions) is a deploy-prep step, not this offline build. `jit_compiler.cc` was restored (back to `0ced8530`).
Persisted: `hw248:/home/alvin/jit-build-cc-wiki-20261002/` (3 `.so` + `patch24.patch` + `receipt.json` +
`jit_compiler.cc.orig` + `logs/` + `ref-3c8e76a2`). **No board; `APPSPAWNX_NO_JIT` / production gates untouched.** The
toutiao JIT path is now de-serialized: the moment the long-wait window shows "pure slow", these artifacts go straight to
a single-variable board window (owned by the outer / deploy lane).

## UPDATE — control BUILT on hw248 (self-deterministic), diverges from the stale 3c8e76a2 → STOPPED per outer
Per the outer's GO, the control (unpatched) `libart-compiler.so` was built on hw248 via the faithful recipe and is
**self-deterministic**: two independent fresh builds are byte-identical (`08026ab6fae27004`, 3895952 B;
`evidence/control-build-result.txt`). Inputs are byte-verified faithful: the Mac `aosp-restoration` art/ tree rsync'd to
hw248 has an **identical** locale-normalized manifest (9577 files, `2a74b309`, content diff 0), and the frozen clang is
byte-identical (`b107ce03`). **But it does NOT byte-match the reference `3c8e76a2`** (3895000 B) — so per
"复现不了就停报差异" I **stopped before patch24**. The difference is tiny and benign: `08026ab6` has 2 extra exports
(`art::mirror::DexCache::GetResolvedType(dex::TypeIndex)` + its `logged_primclass_guard` one-time-log guard) + 1 extra
embedded path (`dex_cache-inl.h`) + 952 bytes; undefined symbols identical, no build-id diff. **Root cause:** the current
`dex_cache-inl.h` (sha `32b44981`) carries a `logged_primclass_guard` diagnostic (lines 164/172/173) that `3c8e76a2`
**predates** — `3c8e76a2` is an older artifact than the current (byte-verified faithful) tree, i.e. artifact-vs-source
drift, not an environment-unfaithfulness. **Decision for the outer (patch24 not applied):** (a) accept `08026ab6` as the
control (faithful to the current FZ-005 tree, self-deterministic) and apply patch24 on it — **cc-wiki recommends (a)**;
or (b) revert the `dex_cache-inl.h` diagnostic to byte-match the stale `3c8e76a2` (regresses the tree; not recommended).

## Honest status first
- a2hlab restarted ~23:05 (Mac memory pressure); the outer moved cc-wiki's JIT build to **hw248**. Nothing of mine was
  interrupted — I had only *probed* (clang `--version`, tree/script reads), never started a build; **no half artifacts**.
- **Not built this turn.** A faithful control-reproduce + patched ×2 compiler build (76 optimizing-compiler sources) is a
  monitored multi-build; with the outer's "no half artifacts / one heavy build at a time / memory pressure" caution
  fresh, I staged + validated it rather than fire a blind background build at the end of the turn. It is GO to launch.

## Validation (go/no-go = GO) — `evidence/build-readiness.txt`
- **hw248 reachable + build-ready**: `ssh hw248` (root@1.95.76.248, 32 cores, 62 GB RAM, 203 GB free).
- **Inputs on hw248**: `$A=/home/alvin/aosp-14.0.0_r1-art` (`$A/art/compiler/jit/jit_compiler.cc` present); frozen clang
  `/opt/wl-src/.work/product-tls-generation/frozen/toolchain/bin/clang++` (= OH clang 15.0.4 feef13a3, x86_64 Linux) +
  sysroot; `cross_compile_arm64.sh` present in `/opt/build-runs/*/adapter/build/inner/`; prior libart-compiler.so builds
  exist (fn02-abi-fix).
- **patch24 applies cleanly**: the hw248 `jit_compiler.cc:75-77` (`implicit_null/so/suspend_checks_`) + the `:80
  kArm` block match patch24's `@@ -75,6 +75,11 @@` context exactly; the tree does not yet contain
  `implicit_suspend_checks_ = false` in jit_compiler.cc.
- **Tree confirmed FZ-005 (r1+22)**: `$A/art/dex2oat/dex2oat.cc:859` already has `implicit_suspend_checks_ = false`
  (patch 22). So patch 24 is the consistent **JIT counterpart** of the proven dex2oat suspend-check-off — same convention,
  exactly as the feasibility assessment predicted.

## The faithful recipe (reconstructed) — `evidence/build-readiness.txt`, `recipe/`
The reference compiler B6 `3c8e76a2` was built (on the Mac/a2hlab workspace) by
`b6-art14-recovery/build-runtime.sh` (env) → `reproduce-providers.sh` →
`benchmark/2026-09-28-bms-route-deploy/latest-source-generation/art14-recovery/build-providers.sh`, whose Layer 4
(`bms/src/adapter/build/inner/cross_compile_arm64.sh:782-892`) compiles 76 ART optimizing-compiler `.cc` + generated
`operator_out.cc` with `-fno-rtti -fvisibility=protected -I$A/art/compiler -I$A/art/dex2oat -I$BC_SRC` → `libart-compiler.so`.
`recipe/24-...explicit-suspend.patch` and `recipe/jit_anon_shim.c` are staged here for a self-contained build.

**Host note:** `3c8e76a2` is tied to the Mac `aosp-restoration` tree (a2hlab-mounted). On hw248 the control is
re-established from the hw248 FZ-005 tree: build **unpatched ×2 (byte-identical) = the hw248 control**, then **patched ×2**.
We do not chase a byte-match to `3c8e76a2` (different tree/host); faithfulness = same-tree reproduce + 2× identical.

## The build plan to run on hw248 (single instance, fresh log)
1. Fresh work dir `/home/alvin/jit-build-cc-wiki-20261002/`; copy in the current `adapter/build/inner/cross_compile_arm64.sh`
   + its driver; point `AOSP_ROOT=/home/alvin/aosp-14.0.0_r1-art`, the frozen clang/sysroot/nm/readelf/libcxx, `L03_A12_*`
   as in `build-runtime.sh`. Record all tool + source SHAs.
2. **Control**: Layer-4 build UNPATCHED ×2 → confirm byte-identical → that is the hw248 control libart-compiler.so.
3. Apply `recipe/24-...explicit-suspend.patch` to `$A/art/compiler/jit/jit_compiler.cc` (git/patch, idempotent; restore
   after) → Layer-4 build PATCHED ×2 → byte-identical. Acceptance vs control: only `jit_compiler.o` differs; exports
   (`nm -D`)/undefined IDENTICAL; `deployed_strings_diff` 0/0; `open_site_scan` unchanged (same discipline as 18763dd4).
4. **memfd shim**: compile `recipe/jit_anon_shim.c` → `libwestlake_jit_anon.so` (target aarch64-linux-ohos, frozen clang),
   `-Bsymbolic`, zero DT_NEEDED beyond libc/libdl; ×2 byte-identical.
5. **N1/N2 pre-run (list only, NO --apply)**: NEEDED closure of both `.so` inside the route dir + the libc++ prereq;
   emit the findings list for outer review; do not add exceptions, do not deploy.
6. Persist to `/home/alvin/jit-build-cc-wiki-20261002/` (sources snapshot, patch24 SHA, toolchain hashes, both `.so`,
   raw build logs tee'd fresh — not concatenated) and record path+hashes in the repo.

## Hard boundaries (unchanged)
- **No board.** This produces artifacts only.
- **Do NOT touch `APPSPAWNX_NO_JIT` / the production gates** — the truly-cold measurement certificate is a user-level
  policy, raised separately. This build does not enable JIT anywhere; it only produces the two `.so`.
- N1/N2 list-only; outer approves any exception before any future window.

## Why staged-not-built is the right call this turn
The investigation (the slow part) is done and de-serialized: host validated, patch validated, tree confirmed, recipe
reconstructed, inputs located. Launching a faithful control+patched×2 compiler build is now a mechanical monitored job —
but it is a *build*, and the outer's just-issued caution (a2hlab died of memory pressure; no half artifacts; one heavy
build at a time) means it should be a watched single-instance run with a fresh log, not a blind end-of-turn background
fire. It launches next.

## Files
- `evidence/build-readiness.txt` — a2hlab→hw248 move, inputs located, patch24 validated, recipe reconstructed.
- `recipe/24-compiler__jit__jit_compiler.cc.explicit-suspend.patch` — the one compiler patch (arm64 suspend-check off).
- `recipe/jit_anon_shim.c` — the memfd jit-cache shim source.
