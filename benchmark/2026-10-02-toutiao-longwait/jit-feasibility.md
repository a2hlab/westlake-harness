# Part 2 — JIT on route-A: feasibility assessment of cc-t3's plan (one page, assessment only, no build)

Reviewing `benchmark/2026-10-02-jit-experiment-plan` (cc-t3). Verdict: **technically feasible and low-risk to build —
the recipe, patches, and a prior build of the artifact all exist in-repo — but the payoff is narrow (toutiao + marginal
start-time), so the build should be gated on Part 1's result.** All four of cc-t3's claims I could check statically hold.

## 1. Source — where it is (verified)
| artifact | location | verified |
|---|---|---|
| OH JIT fix (`jit_memory_region.cc` `#if __OHOS__` anon branch) | a2hlab `~/a2hlab/ws/aosp-art-15` @`047ccf02924f`, file sha `e4b634051a68`; raw in `jit-experiment-plan/source/oh-jit-art15.diff` (80 lines) | file present, 80-line diff with git provenance |
| AOSP-14 port (record) | `source/23-...oh-jit.patch` (83 lines) | present; plan says `git apply --check` passes on art-r1 3c05e56adf |
| compiler suspend patch (the one new change) | `source/24-...explicit-suspend.patch` (17 lines) | **read & confirmed**: 5-line insert in `compiler/jit/jit_compiler.cc` setting `implicit_suspend_checks_=false` for `kArm64` — the exact JIT mirror of patch 22 (dex2oat) |
| memfd shim (no-libart option) | `source/jit_anon_shim.c` (56 lines) | present; refuses only the `jit-cache` name, lets `jit-zygote-cache` pass |
| build recipe for `libart-compiler.so` | **in-repo**: `bms/src/adapter/build/inner/cross_compile_arm64.sh:782-892` = "Layer 4: libart-compiler.so (JIT compiler)", compiles `jit/jit_compiler.cc` (`:792`) with `-fno-rtti -fvisibility=protected -I.../art/compiler -I.../art/dex2oat`; `-D__OHOS__` is in `COMMON_BASE` (`:189`) | **read & confirmed in this repo**, not just hw248 |

So "source" is not a gap: the fix, the port, the one new patch, the shim, and the build recipe are all on disk here;
the only off-repo input is the FZ-005 compiler tree (hw248 `/home/alvin/aosp-14.0.0_r1-art`, r1 + the 22-patch series —
`knowledge/toolchains/art-r155/patches/01..22` present in-repo, patch 22 = `22-dex2oat__implicit-suspend-checks-off.patch`).

## 2. Can the FZ-005 toolchain build it? — yes, and it already did once
- FZ-005 is the **dex2oat/AOT** toolchain (host `dex2oat64 ae865ddd`, 22 patches, frozen 2026-10-01, DIGEST 454). Its
  tree contains the full optimizing compiler (dex2oat links it), which is exactly what `libart-compiler.so` is — so the
  same tree builds the JIT compiler lib. `cross_compile_arm64.sh` Layer 4 is the target-arm64 recipe for it.
- **Proof it builds:** the B6 compiler `3c8e76a2` (westlake-harness-bms-deploy `.work/b6-art14-recovery`, cited by
  cc-t3 + DIGEST 656) is a `libart-compiler.so` already built from the 14 tree whose `art::` imports all resolve against
  the board route libs. It is unusable **only** because it lacks patch 24. So the delta from a working artifact is:
  **apply patch 24 + rebuild Layer 4 + 2× byte-identical**. That is the whole build.
- Effort: **small** — one 5-line patch on top of a tree+recipe that has produced this .so before; a Layer-4 cross build
  (minutes, like the dex2oat bakes) on the x86_64 Linux host (a2hlab/hw248 — the frozen clang is x86_64 Linux).

## 3. Gates the artifact(s) must pass (before any board window)
Two new `.so` (`libart-compiler.so`, `libwestlake_jit_anon.so`). From cc-t3's table, cross-checked against the gate set:
- **native_predeploy N1/N2** on both .so (NEEDED-closure inside the route dir + libc++ prereq). New undefined/NEEDED →
  add entries to `knowledge/gates/native-predeploy-exceptions.json` (object/reason/evidence), outer-approved.
- **`deploy_generation.py` single-ART check** keys on `libart.so`/`libopenjdkjvm.so` only → the two new libs do not trip
  it (confirmed: neither is libart/openjdkjvm).
- **`check_frozen.py`** — the two libs are new artifacts, not frozen items; libart `59e1bb45`, FZ-002 provider, FZ-005
  toolchain, boot image all **unchanged** by the overlay, so nothing frozen is weakened.
- **Two PRODUCTION gates block a future JIT-on generation** (not the board overlay):
  `appspawn-x/tests/test_production_config.py:47` and `generation/verify_generation.py:175` assert
  `APPSPAWNX_NO_JIT == "1"`. A board overlay does not run them, but any built generation would fail → they need an
  exceptions file (`knowledge/gates/production-config-exceptions.json`), a one-time gate-code change (outer-approved).
  The **"truly-cold" measurement certificate** (ZigZag/Unity cert, `security_specialization/REPORT.md` Q5) is a
  USER-LEVEL policy — turning JIT on breaks that contract's premise, so it must be shown to the user, not just gated.
- AGENTS persistence: record the FZ-005 tree ref, patch-24 sha, toolchain hash, and the Layer-4 build log to a
  persistent location (hw248 `/home/alvin/`), repo keeps path+hash.

## 4. Risk — low, bounded by cc-t3's stop rule
- **Suspend-check mismatch** (the one real correctness hazard): covered by patch 24 (same fix as patch 22, which is
  proven on-board via T6c/T7c self-UI).
- **OH refuses anonymous RX (XPM)** in the route-A child domain: not a crash — ART logs "could not create JIT code
  cache" and runs without JIT ("JIT not engaged", inconclusive, roll back). Fallback = the file-backed `O_TMPFILE` dual
  view (shim returns an app-owned 0700 fd).
- **G2.14n** (why JIT was disabled): was a 32-bit SIGILL where disabling JIT left the crash unchanged → JIT was
  *eliminated* as the cause, not implicated; platform is now arm64/R155. Not a correctness blocker.
- Stop rule (cc-t3): any SIGILL/SIGSEGV with pc in `[anon:dalvik-jit-code-cache]`/`jit-code-cache` → stop + roll back.

## 5. Recommendation — feasible, but gate on Part 1; and for toutiao, JIT beats install-AOT
- **Build feasibility: GREEN.** recipe + 22 patches + patch 24 + shim + a prior B6 build all in hand; delta is one
  5-line patch + a Layer-4 rebuild + predeploy exceptions. No source gap, low effort, low risk.
- **Payoff: narrow.** cc-t3 + DIGEST 657 already showed JIT's benefit is essentially **toutiao only** — 18 of the 20
  white keys draw a first frame ≤4.05 s (content/render-bound, N11h double-copy family), not interpreter-slow. So JIT
  does not move the white-window cluster.
- **Therefore gate the build on Part 1.** If the long-wait window says toutiao is **pure-slow** → the JIT build is
  worth it (toutiao is the one key it helps, and this is the fix). If it says **native wall behind** → JIT will not get
  toutiao to content (the bionic-ABI walls of `2026-10-02-toutiao-oldroute-diff` row 2 remain), so defer.
- **For toutiao specifically, JIT > install-time AOT.** toutiao's slow phase is Mira-plugin + Tinker code, loaded as
  **dynamic dex at runtime**; `dex2oat` at install only AOTs the base APK dex, not the plugin/hotfix dex loaded later —
  so install-AOT would miss exactly the hot code. In-process JIT compiles whatever runs, including the dynamic dex.
  (This does not contradict FZ-005 being the AOT toolchain for the *boot image*; app dynamic-dex is a different surface.)

## Not done here (by design)
No build, no board, no gate edit. Assessment only, per dispatch. The go/no-go belongs to the outer after Part 1 runs.
