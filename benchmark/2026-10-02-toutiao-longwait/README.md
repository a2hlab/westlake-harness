# Toutiao long-wait window + JIT feasibility — two offline deliverables that gate each other

Offline, no board, board #90. Follows `benchmark/2026-10-02-toutiao-m4` (toutiao is SLOW not WAITING: JIT off,
interpreter `handleBindApplication` churn; capture ended t+15.5 s with only `maps-t5`). Two asks, both offline:

1. **Prepare a default-disabled toutiao long-wait short window** (`window-spec.md`) that observes the base longer to
   settle slow-vs-wall — using the executor's existing flags, flagging the one capability gap.
2. **Assess the feasibility of cc-t3's JIT experiment plan** (`jit-feasibility.md`) — source, buildability, gates,
   effort; assessment only, no build.

## How the two connect (the point)
The long-wait window is the **go/no-go gate** for the JIT build:
- Part 1 PASS-pure-slow (toutiao draws its own UI by t90) → JIT/AOT is the right lever → **build** (Part 2 is GREEN).
- Part 1 FAIL-native-wall (dies / cppcrash after signal 11) → a wall JIT cannot move → **defer** the JIT build.

So Part 2's recommendation is explicitly conditioned on Part 1's outcome. Neither ships a board change this round.

## Part 1 — long-wait window (default disabled): the key finding is an executor audit
`evidence/executor-capabilities.txt` (read-only audit of `bms_batch.py` / `board_run.py`):
- **Screenshots t20/t45/t90 — EXISTING.** `--shots 20,45,90` is valid (`shot_offsets`: 1..32 increasing offsets ≤300,
  `bms_batch.py:1088`); files auto-named `t20/t45/t90.jpeg`.
- **Full untruncated hilog — EXISTING.** `--hilog 95` dumps the whole launch-reset buffer after the t90 shot
  (`bms_batch.py:1130`); `SECONDS` *is* the "until" — there is no separate `--hilog-until`. `--wait 95` keeps the run
  alive to t90.
- **maps at t45/t90 — NOT EXISTING (the one gap).** `bms_batch` captures `/proc/<pid>/maps` **once, after the first
  screenshot only** (`bms_batch.py:771` `if len(rec['screenshots']) == 1:`) — that is why M4's `--shots 5,20` yielded
  only `maps-t5`. To get t45/t90 maps the **executor lane** makes one additive change (capture maps on every `shot`
  event, not only the first); I specify it but do **not** touch the executor (contract boundary). The window still runs
  without it (maps-t20 only), losing just the later maps, not the pass/fail verdict.

Base = the unified state at run time (U12 if promoted, else U10.1T8). The **only** variable vs that base is the
screenshot time points — no runtime/cfg/LD_PRELOAD change; this window does NOT turn JIT on. Exact bms_batch invocation,
pre-window fingerprint check, and the three-way pass/fail (pure-slow / native-wall / still-in-init) are in
`window-spec.md`.

## Part 2 — JIT feasibility: GREEN to build, but narrow payoff
`jit-feasibility.md`. All of cc-t3's statically-checkable claims hold; added value = verifying the build path is in-repo
and conditioning the build on Part 1:
- **Source: no gap.** the OH JIT fix (a2hlab aosp-art-15@047ccf0), the AOSP-14 port, patch 24 (read & confirmed: the
  5-line arm64 `implicit_suspend_checks_=false`, the JIT mirror of dex2oat patch 22), the memfd shim, AND the build
  recipe (`cross_compile_arm64.sh:782-892` "Layer 4: libart-compiler.so") are all on disk here. FZ-005's 22 patches are
  in-repo (`knowledge/toolchains/art-r155/patches/01..22`).
- **Buildable, proven once:** the B6 compiler `3c8e76a2` is a `libart-compiler.so` already built from the 14 tree whose
  `art::` imports resolve on-board; it lacks only patch 24. Delta = patch 24 + a Layer-4 rebuild + 2× byte-identical.
  Effort: small; the frozen clang is x86_64 Linux (build on a2hlab/hw248).
- **Gates:** two new `.so` need native_predeploy N1/N2 exceptions; single-ART and check_frozen are untouched (libart /
  FZ-002 / FZ-005 / boot image all unchanged); two PRODUCTION gates asserting `APPSPAWNX_NO_JIT==1` need an exceptions
  file; the "truly-cold" measurement certificate is a USER-level policy to surface, not just gate.
- **Payoff narrow:** JIT helps essentially toutiao only (18/20 white keys draw ≤4.05 s = content/render-bound, not
  interpreter-slow — cc-t3 + DIGEST 657). And for toutiao, **JIT beats install-time AOT**: its slow code is Mira/Tinker
  **dynamic dex** loaded at runtime, which `dex2oat`-at-install cannot reach but in-process JIT can.

## This round's rules
- To change what a window captures, check the executor's existing flags first (`--shots` / `--hilog SECONDS` / `--wait`);
  a capability it lacks (per-shot maps) is a one-site change handed to the executor lane, not self-patched — stay inside
  the contract boundary.
- A feasibility assessment verifies the other lane's claims against on-disk artifacts (patch content, recipe lines,
  prior-build evidence) rather than restating them, and ties the go/no-go to the experiment that actually decides it.

## Files
- `window-spec.md` — Part 1: the default-disabled long-wait window (exact invocation, one-variable base, 3-way pass/fail).
- `jit-feasibility.md` — Part 2: the one-page JIT feasibility assessment (source / build / gates / effort / recommendation).
- `evidence/executor-capabilities.txt` — read-only audit of bms_batch/board_run with line cites + the one minimal change.
