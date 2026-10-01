# N11g blueprint: explicit sealed owner for host-service opens

**Design only. No source patch, build, package or board deployment is authorized or produced.** Base for a future observation is signed **U9**, not U10/U10.1. N11f was refuted and 61b was restored and unlocked.

## What is proved, and what is the proposed cause

N11f child **f1b43386** ran on 61b. The host emitted `done stage=8 branch=0 index=0`; ART and JVM each had one load instance. Probe PID **7080** nevertheless had two bridge instances at **7f16440000 / 7f1fb80000**, and two runtime instances at **7f00c40000 / 7f16900000**. Each pair maps the **same inode** (bridge 467241, runtime 463980), so counting distinct path strings/inodes would miss this failure. The smoke counter uses `path@load-address`. This refuted the single-owner premise before the 18-key observation; all 18 outcomes remain missing. Raw/collated evidence: `../2026-10-01-n11f-owner-callback/window-r1/`.

Outer attributes the remaining copy to the host open-service path's plain default `dlopen`. The following static evidence supports choosing that path for the next single-variable experiment:

- `westlake_android_child_plugin.c:702` assigns `child_services.open_sealed_exact = WLSCPL_OpenPreparedNamespace`; the callback implementation is in **the child plugin .so**, not the appspawn-x executable. Its co-build recipe exactly reproduced N11e **3f1e703c** and produced repeat-identical N11f **f1b43386**. Sources and inputs are archived under `$WORKSPACES/westlake-inputs/generations/n11f-u9-owner-callback-v1/`.
- `sealed_child_provider_loader.c:272–304` returns a resident handle only for two exact path strings; its generic fallback remains `return dlopen(absolute_path, flags)`. In the actual N11f ELF, `WLSCPL_OpenPreparedNamespace` ends the fallback with **0x35e8: b dlopen@plt** (`n11f-callback-disassembly.txt`). Thus that fallback has no explicit sealed namespace argument; caller-address namespace selection remains in play.
- `RealOpenLocalNow` explicitly uses `dlopen_ns(&closure_namespace, ...)` and opens the two owners after route-A ART is resident. Use this verified local mechanism instead of relying on the default namespace or a new inheritance edge.

An important timing limit: the existing `done` log is emitted immediately after `WLSCPL_LoadSealedProvider`, **before** the service table assignment and provider entry (`source-evidence.txt`, plugin:645–711). Its branch 0 proves that loader stage succeeded; it does not independently trace every later open callback. The next marker must observe the actual callback request and selected route. The precise request that minted the second instance is not dynamically traced by N11f. This is a design hypothesis to test, not a new claim that all later calls were already measured.

## Selected change and exact scope

**Prefer one child-only routing change:** replace the wrapper's plain fallback with an explicit open in the already-prepared `closure_namespace`. Keep the current canonical absolute-path, `/system/android/lib64/` prefix and flags checks. Reuse the two published `g_owner_handles` for exact owner requests. A missing protected owner must record the current error and reject that child; **no fallback to default**. Other currently allowed paths are opened with the **same path/flags** through `dlopen_ns(&closure_namespace, absolute_path, flags)`. Do not change the requested library or relax its path guard.

Design sketch (not an applied diff):

1. Validate the existing request and prepared namespace.
2. Exact bridge/runtime request: return its already-published sealed owner; absent owner -> typed failure, never plain dlopen.
3. Other admitted Android-library request: open the exact file explicitly in the prepared sealed namespace; failure -> capture current dlerror and return failure, never plain dlopen.
4. Emit a callback-route marker containing path, `resident|sealed|reject`, result handle and owner index, including failures. No weak HiLog dependency.

Primary changed function: `src/sealed_child_provider_loader.c::WLSCPL_OpenPreparedNamespace`. Only supporting audit/log state in that file, and a post-provider-entry host-context audit in `src/westlake_android_child_plugin.c` if needed to guarantee output. Preserve N11e's captured-current-error channel and N11f's unconditional loader-stage result. No host appspawn-x source change, runtime/provider/ART/JVM/bridge/Java/image change, `dlns_inherit` change, arbitrary new shared-library list or global process handle registry.

Logging should reuse the already-resolved `HiLogPrint` from the resident runtime owner (the `[N11f-OWNER]` route was observed). Emit e.g. `[N11g-SEALED-OPEN] path=… route=… owner=… handle=…`; the smoke must require a **real callback** marker. If that channel is absent, the gate must report a silent probe, not infer that the path did not run. The existing done marker alone is insufficient.

Before implementing, check the existing callback callers' `dlclose` ownership contract against the recorded source: the resident handle is an anchored, process-lifetime owner and must not be invalidated by callers. N11f already uses a borrowed resident return; N11g must not silently introduce a new ownership convention. If an owned reference is required, acquire it via a same-namespace resident lookup and compare with the anchor, with a separately reviewed gate binding. This is a review item, not permission to build a second implementation now.

Do **not** deduplicate by SONAME alone. Deployed U9 `libandroid.so` (**9ccf64f8**) has SONAME `liboh_android_runtime.so`, while its private facades (**ee2fb82c**) have SONAME `libandroid.so` (`u9-libandroid-identity.txt`). Those are different products and paths. Do not redirect libandroid to runtime merely because SONAME matches; keep exact path behavior and verify the owner of dependencies.

The alternative of adding another namespace inheritance edge is rejected for this first experiment: OH 6.1 repeat `dlns_inherit` to one parent replaces the prior list (U10 OrganicMaps regression), and an existing local duplicate is not merged by adding an edge. An explicit prepared-namespace open is smaller and measurable.

## Gates, prospective oracle and retreat

After approval to implement: co-build only the child; reproduce the N11f build baseline, repeat the candidate, audit against **deployed U9 dc73a28d** and N11f (exports/NEEDED/SONAME/calls/read-only data), artifact identity, N1/N2 and frozen checks. Existing N11f exception scope explicitly excludes unified promotion; **new manifest bindings need outer review**, even if semantic findings match. Preserve all original U9/FZ artifacts.

Fresh proposed 61b window: <=30 minutes, no new key after minute 20; after-lock must verify U9 **a2919b793eb6 / 4db882a81732**, 318 assertions and candidate SHA. Continuous hilog starts before replacing the one child file. Smoke requires a live callback-route marker, no default-open route for either owner, HelloWorld live t20, and **ART/JVM/bridge/runtime each one load instance**. Count distinct mapping bases, not inodes, using the existing activation_smoke implementation. Candidate fingerprints alone cannot show a child replacement; explicit child hash is mandatory.

If single-copy smoke passes, run the approved prediction table's four session-miss candidates, Wikipedia and canaries, then other-cause observations within the deadline. Use clean reinstall, snapshots at 5/20s, raw facts and outer UI verdicts; unknown keys stay unknown. `predict_vs_actual` with no signed samples must remain missing, not a fabricated hit.

Refute: any owner has two bases; callback falls back to default; protected-owner rejection/late publication; silent marker; hard control/canary failure; or outer-read target screenshot refutes the predicted wall clearance. On any refute, do no further targets: stop capture and immediately run the original finish path. Always restore **U9 child dc73a28d**, verify 318 / diff empty / absent empty / residual mounts zero, restore smoke and verify again before unlocking. Recovery failure retains the lock for authorized recovery. No installer restart, board reboot, new boot service or exception disabling is part of N11g.
