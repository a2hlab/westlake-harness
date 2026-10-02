# JIT on route-A: what it can win, where the OH JIT fix comes from, and a single-board minimal experiment (plan)

#90, offline, no board. Follows `2026-10-02-toutiao-oldroute-diff`, which found that route-A runs every app on the
interpreter (`APPSPAWNX_NO_JIT=1`). The question asked: how many of the candidate base's 20
"no observed termination" white-window keys are merely not finished at t20, and what is the smallest board
experiment that turns JIT on?

## What was wrong first

- **"The 20 white keys may just be slow" does not hold. 18 of 20 drew their first frame by t+4.05 s**
  (`stages.csv`, window 5, candidate base). They have bind start at ~1.3 s, Application return at 1.5-3.3 s and
  `activityResumed (first-frame)` at 1.85-4.05 s. Their main threads were then quiet for 5-7 s before the log
  cutoff.
  - Their white t20 is content or render, not startup speed.
  - Only **toutiao** is slow: still inside Application init at the cutoff (t+15.5 s), main thread logging 2 s
    before it.
  - One key never launched (`cv2-com-frequent-habits`: no icon found, no screenshot).
  - JIT is therefore a lever for toutiao and for start time in general, not for this white-window cluster.
- **"Port the OH JIT patch into libart" cannot be done as a single variable.** The board libart `59e1bb45` has no
  recoverable source (DIGEST 502: Westlake vtable code not in AOSP 14 r1; the r1 + 21 rebuild covers 97.9 % of
  its exports). A patched libart would be a different libart.
- **Removing `APPSPAWNX_NO_JIT` alone would not turn JIT on. Route-A ships no JIT compiler.**
  - libart `59e1bb45` (11.8 MB) dlopens `libart-compiler.so` ("JIT could not load libart-compiler.so"), and no
    package, board fingerprint or route directory has one.
  - The old route's libart `78e34445` (21.6 MB) had the optimizing compiler linked in (52 compiler symbols
    defined).
- **A JIT compiler built from the r1 tree would emit the wrong suspend checks.** `JitCompiler` copies
  `implicit_suspend_checks_` from the runtime *after* parsing `-Xcompiler-option` (r1 `jit_compiler.cc:77`), and r1's
  runtime sets it true on arm64 (`runtime.cc:1747`).
  - R155 keeps no suspend-trigger page in x21. That is why boot-image dex2oat needed patch 22
    (`implicit_suspend_checks_ = false`); T5b aborted on exactly this.
  - JIT code must follow the same rule, so the compiler needs its own one-line patch (24).
- **`APPSPAWNX_NO_JIT` has two origins, and neither is a correctness requirement.**
  - The env reader came from the 2026-05-01 G2.14n SIGILL hunt on 32-bit ARM. That hunt **eliminated** JIT: "Tested
    with `-Xusejit:false` → crash unchanged; `-Xint` → crash unchanged" (HanBingChen
    `adapter/memory/project_g214n_artmethod_entry_corruption.md`).
  - The production gates require it for a measurement contract: "qualifying cold starts must disable ART JIT
    (truly-cold)", from the ZigZag/Unity route-A generation certificate (`security_specialization/REPORT.md`: "Q5
    truly-cold device proof: not proven and not claimed").

## 1. Where each white key stood at t20 (`slow_or_dead.py` → `stages.csv`)

- t20 is the board mtime of `t20.jpeg` (record.json `remote_stat`), compared in board time (UTC+8, the hilog clock).
- The captured hilog ends 4.4-6.8 s before t20 in all 19 launched runs, so every key is judged at
  cutoff = min(t20, hilog end), about t+15-17 s.
- Markers were learned from a lit run (aegis, window 2): `[B43-BIND] ensureBindApplication start`,
  `handleBindApplication returned OK`, `[OH_WSA] ENTRY addToDisplayAsUser`, `activityResumed (first-frame)`.

| verdict | keys |
|---|---|
| drew (first frame ≤ 4.05 s) | 18: vaults-randomlydie, flowitgame, yam, itsdicey, yatoo, jiten-webview, dddmodel2, yahtzeedicer, webrtc-check, fd-AppManager (slowest, Application 3.31 s), fd-app, fd-mobile, fd-noice, fd-shatteredpixeldungeon, fd-tutanota, fd-uhabits, noice, termux |
| slow-in-app-init | 1: **toutiao** (bind 1.26 s, no Application return by t+15.5 s) |
| not-launched | 1: cv2-com-frequent-habits |

noice and fd-noice keep the main thread busy after the first frame (764 and 232 `scheduleVsync` requests): an
animation runs, the frames are white. fd-uhabits / fd-noice / noice are the U8 "about half the time lit" keys.
Their odds are the only ones in this group a faster runtime could plausibly move.

## 2. The OH JIT fix: source and what route-A needs instead

- **Source found (lookup order: local → a2hlab).** On a2hlab, `~/a2hlab/ws/aosp-art-15/runtime/jit/jit_memory_region.cc`
  is the patched file:
  - repo `aosp-art-15` @ `047ccf02924f` (2026-09-05 snapshot commit); file sha `e4b634051a68`; pristine
    `upstream/art-15` file `8f5ba3008edd`;
  - one `#if defined(__OHOS__)` block in `JitMemoryRegion::Initialize` (`source/oh-jit-art15.diff`).
  - Its anonymous-branch log is at **line 152**. That is the line the old route's child printed
    (`jit_memory_region.cc:152] [WESTLAKE-OH-JIT] memfd RX denied (13); using ART anonymous cache`, old-route
    child.stderr:23), so this is the source of `78e34445`'s JIT behaviour.
  - Upstream context: vm-copies/westlake-current f216957 `docs/parity/OH-ANDROID-PARITY-2026-09-05.md` (libart-v27,
    only `runtime/jit/jit_memory_region.o` changed). hw248 not needed.
- **Ported to AOSP 14 for the record:** `source/23-runtime__jit__jit_memory_region.cc.oh-jit.patch`.
  - The block is verbatim, with `gPageSize` → `kPageSize`; AOSP 14 has the same anchor and variables.
  - `git apply --check` passes on art-r1 3c05e56adf.
  - `cross_compile_arm64.sh:189` defines `__OHOS__`, so the block would compile in. It cannot be applied to
    `59e1bb45` (see above).
- **Equivalent without touching libart:** `source/jit_anon_shim.c`.
  - AOSP 14 already falls back to ART's anonymous single mapping when `art::memfd_create("jit-cache")` fails and
    RWX is allowed. See art-r1 `jit_memory_region.cc:85-95`, `:219`, `:240`; RWX is allowed for every
    non-system-server process, `jit_code_cache.cc:1929`.
  - libart imports that function from libartbase (`U _ZN3art12memfd_createEPKcj`). A preloaded shim that refuses
    only the name `jit-cache` reproduces the patch's anonymous branch.
  - The zygote names (`jit-zygote-cache`) pass through. Route-A children create a fresh non-zygote VM
    (`[ROUTE-A] fresh child VM requires no zygote post-fork hooks`, window5 toutiao hilog:30608), so the private
    cache is created in the child, on exactly this call.
- **JIT compiler:** `libart-compiler.so` built from the FZ-005 tree.
  - That tree is hw248 `/home/alvin/aosp-14.0.0_r1-art`, r1 + the 22-patch series, which T4 layout-matched to R155:
    versions 108/230, 244 `art_quick_*` Thread offsets identical.
  - Add patch `source/24-compiler__jit__jit_compiler.cc.explicit-suspend.patch`, and build with the existing
    `cross_compile_arm64.sh` Layer 4 recipe (`:782-892`).
  - The B6 compiler `3c8e76a2` (westlake-harness-bms-deploy `.work/b6-art14-recovery`) resolves all its `art::`
    imports against the board route libs. But it lacks patch 24, so it is **not** usable.

## 3. G2.14n: why JIT was turned off, and whether this JIT can trigger it

- **G2.14n (2026-05-01) was a SIGILL on 32-bit ARM.** `art_quick_invoke_stub` jumped through a corrupted
  `ArtMethod::entry_point_from_quick_compiled_code_` into a library's `.bss`, after the vsync chain started
  running Choreographer.
- JIT was disabled as a diagnostic, and the result was "crash unchanged" with `-Xusejit:false` and with `-Xint`.
  JIT was eliminated as the source; the switch was never removed.
- The platform has since changed: arm64, R155 libart, a different adapter.
- **What this experiment can still break:**
  - JIT code with a wrong check convention (covered by patch 24);
  - the RWX update path being refused by OH XPM in the route-A child domain. The old route's process accepted
    it, but its SELinux domain is not shown to be route-A's `normal_hap`. A refusal is not a crash: ART logs that
    the JIT code cache could not be created and runs without JIT.
  - Stop rule: any SIGILL/SIGSEGV whose pc lies in `[anon:dalvik-jit-code-cache]` or `jit-code-cache`.

## 4. The single-board experiment

**Overlay, one board, ≤ 30 min, on top of the unified state (U10.1+T8+U11i):**
1. `libart-compiler.so` (FZ-005 tree + patch 24) in the route-A directory next to libart:
   `/system/lib64/westlake/route-a/74d1d6d4…/`.
2. `libwestlake_jit_anon.so` (the shim) in `/system/android/lib64/`, appended to the appspawn-x `LD_PRELOAD`.
3. The appspawn-x init cfg with `APPSPAWNX_NO_JIT` removed. Init reads cfg at boot, so this needs one reboot.

libart, provider, BCP and boot image are unchanged.

**Before the window (static, offline):**
- native_predeploy N1/N2 on the two new .so: NEEDED closure inside the route directory plus the `libc++`
  prerequisite. Add exceptions only via `knowledge/gates/native-predeploy-exceptions.json`.
- `check_frozen.py`.
- `deploy_generation.py`'s single-ART check, which keys on `libart.so` / `libopenjdkjvm.so` only.
- Record the board's current `/system/etc/init` appspawn-x cfg SHA by read-only readback. It is not in the
  unified-state fingerprint.

**Run order:**
1. Smoke HW + ZZ.
2. `toutiao`.
3. 10 white keys: fd-uhabits, fd-noice, noice, fd-AppManager, fd-mobile, fd-tutanota, termux, yahtzeedicer,
   dddmodel2, jiten-webview.
4. Optional lit controls, if time allows: aegis, markor.

bms_batch t5/t20, plus one t60 screenshot for toutiao.

**Mechanism readback per process (must hold, else "JIT not engaged", inconclusive, roll back):**
- hilog has no `JIT DISABLED`, no `could not load libart-compiler.so`, no "Failed to create … code cache";
- `[JIT-ANON] shim loaded` and `[JIT-ANON] refused memfd jit-cache` are present;
- `maps-t5` shows `libart-compiler.so` mapped from the route directory and an executable `dalvik-jit-code-cache`
  mapping.

**Pass criteria (screenshots are ground truth):**
- toutiao `activityResumed (first-frame)` before t20 and its own UI at t20 or t60 (splash or the privacy
  dialog). Baseline: no Application return by t+15.5 s.
- First-frame time per key against `stages.csv`: not slower.
- HW / ZZ still lit.
- Any of the 10 white keys flipping to lit is a bonus; it is not required.

**Stop and roll back immediately on:**
- a SIGILL/SIGSEGV with pc in the JIT cache;
- HW or ZZ not lit;
- any key that drew in window 5 now failing before its first frame.

**Rollback:**
- restore the cfg (`APPSPAWNX_NO_JIT=1`, original `LD_PRELOAD`) and remove the two .so;
- reboot, then smoke HW + ZZ;
- `runtime-fingerprint.txt` must equal the unified state's, and the cfg SHA must equal the readback.

**Predictions (written before any window):**
- **toutiao:** Application returns and MainActivity draws a first frame by t20 (moderate). The feed does not come
  by t60, because the bionic-ABI walls of `2026-10-02-toutiao-oldroute-diff` row 2 are untouched.
- **The 18 drew-keys:** first frame 10-40 % earlier. The t20 verdict is unchanged for at least 8 of the 10
  measured; fd-uhabits / fd-noice / noice may flip either way.
- **HW / ZZ:** unchanged. ZZ is Unity il2cpp, little Java.
- **If XPM refuses anonymous exec:** "JIT not engaged", nothing breaks, and the next arm is the file-backed dual
  view. The same shim can return an `O_TMPFILE` fd from a 0700 app-owned cache directory instead of failing
  (upstream #50, p90 −61.6 %).

## 5. What it touches: gates and frozen items (the outer loop approves; nothing here weakens a frozen item)

| object | where | effect of the experiment | what is needed |
|---|---|---|---|
| production gate `APPSPAWNX_NO_JIT == "1"` | `bms/src/adapter/framework/appspawn-x/tests/test_production_config.py:47`, `generation/verify_generation.py:175` (run by `arm64-runtime-generation/container_build.sh:143` when an appspawn-x generation is built) | not executed by a board overlay; it would reject any future generation built with JIT on | exception-table style: give both checks an exceptions file (object, reason, evidence; e.g. `knowledge/gates/production-config-exceptions.json`). This is a one-time gate-code change, so the outer loop approves it; the contract text ("truly-cold" certificate) is a user-level policy and should be shown to the user |
| `main.cpp:123` `setenv("APPSPAWNX_NO_JIT","1")` | `bms/src/adapter/framework/appspawn-x/src/main.cpp` | not in the deployed host appspawn-x `65cc3535` or the provider (no `APPSPAWNX_FAST_DEV` string in either): legacy main | none for the experiment; remove with the gate change |
| appspawn-x init cfg | board `/system/etc/init` (repo copy `config/appspawn_x.cfg:61`) | edited for the window, then restored | read-only SHA readback before; restore after |
| FZ-002 `libwestlake_android_runtime_provider.so` 0509fe23 | reads `APPSPAWNX_NO_JIT` and adds `-Xusejit:false` | unchanged binary; only its input env changes. JIT is not part of FZ-002's frozen API (8 MiB ActivityThread pthread) | none |
| FZ-005 dex2oat toolchain / boot image | hw248 r1 tree + 22 patches | unchanged; its tree is reused to build `libart-compiler.so` (new artifact, not frozen) | record tree, patch 24 SHA, toolchain and build log (AGENTS: persist sources + logs) |
| libart `59e1bb45` | route-A directory | unchanged | none |
| deploy gates | `deploy_generation.py` single-ART (`libart.so`, `libopenjdkjvm.so`); native_predeploy N1/N2 | two new .so must pass N1/N2 | exceptions only via `knowledge/gates/native-predeploy-exceptions.json` |
| unified-state fingerprint | three boards | changes on the experiment board for the window only | rollback restores it; the other two boards are untouched |

## Files

- `slow_or_dead.py` → `stages.csv`: per white key, the stage times (s after child start), cutoff, main-thread
  quiet time, lines after the first frame, verdict, run path.
- `source/oh-jit-art15.diff`: the a2hlab patch, raw (with its git provenance lines).
- `source/23-runtime__jit__jit_memory_region.cc.oh-jit.patch`: AOSP 14 port, record only.
- `source/24-compiler__jit__jit_compiler.cc.explicit-suspend.patch`: compiler patch for the experiment.
- `source/jit_anon_shim.c`: the shim (not built).
