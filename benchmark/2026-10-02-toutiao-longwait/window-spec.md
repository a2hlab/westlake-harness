# Part 1 — toutiao long-wait short window (DEFAULT DISABLED)

**Status: DEFAULT DISABLED.** Run only after U12 stage-A finishes **and** the outer approves. ≤30 min, single board,
**prefer 61b**. This is a *capture-time* change only — no runtime/host/deploy/cfg change; it cannot regress the board
and reverts with the window.

## Goal
Settle the one thing the M4 traces could not: toutiao's capture ended at t+15.5 s (only `maps-t5`, no t20), still in
`handleBindApplication`. Does it eventually draw its own UI (pure slow → JIT/AOT is the fix), or is there a native wall
behind the handled `signal 11` seen in the stageB run? One longer CLEAN capture answers it.

## Base = the unified state at run time — ONE variable only
Base image = whatever is unified when this runs: **U12 if it has been promoted, else U10.1T8**. The ONLY change versus
that base is the **screenshot time points** (and keeping the run alive long enough to take them). No libart, no cfg, no
LD_PRELOAD, no JIT — this window does NOT turn JIT on; it only observes the base longer. (The JIT window is Part 2's
separate, later experiment.)

## Exact invocation — existing flags, run bms_batch directly for one key
From `evidence/executor-capabilities.txt`: `--shots 20,45,90` (valid: 3 increasing offsets ≤300), `--hilog 95` (full
untruncated dump after the t90 shot — `SECONDS` is the "until"), `--wait 95` (keep alive to t90) are all EXISTING. Run
the batch tool directly (a single-key window, not a full sweep, so `board_run.py`'s hardcoded `--shots 5,20` is bypassed
and needs no change):

```
# on the lab host, with the board LOCKed to cc-wiki, 61b whitelisted:
python3 benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py --execute \
  --serial <61b-connect-key> --lane cc-wiki \
  --manifest <base-manifest> --input-root <base-input-root> \
  --keys toutiao --reinstall --wait 95 --hilog 95 --shots 20,45,90 \
  --out benchmark/2026-10-02-toutiao-longwait/run/<iso>
```
Captures: `t20.jpeg` / `t45.jpeg` / `t90.jpeg`, full `hilog.txt` (reset at launch, dumped at t+95), faultlogs,
`record.json`, `facts.txt`.

### The one missing capture — t45/t90 maps (hand to the executor lane, do NOT self-patch)
`bms_batch` captures `/proc/<pid>/maps` **once, after the first screenshot only** (`timed_collection`,
`bms_batch.py:771` `if len(rec['screenshots']) == 1:`). So with `--shots 20,45,90` you get **`maps-t20` only**, not
t45/t90. Two options:
- **Preferred:** the executor lane makes the one-line change in `timed_collection` (capture maps on every `shot` event,
  not only the first) — spec in `evidence/executor-capabilities.txt`. Additive, one site. Then `--shots 20,45,90`
  yields maps-t20/t45/t90 for free.
- **Fallback if that change has not landed:** run the window anyway with `maps-t20` only (still answers the
  screenshot-based pass/fail below); the t45/t90 maps are a nice-to-have for the "which copy is mapped" cross-check,
  not required for the slow-vs-wall verdict.

## Pre-window (static, offline) — prove the base is unchanged (one variable)
- Record the board runtime fingerprint by read-only readback; it MUST equal the unified state's (this window changes
  nothing that is fingerprinted — if it differs, the base is wrong, stop).
- Only-read board check first (AGENTS board discipline); LOCK to cc-wiki; whitelist the 61b serial only.

## Pass / fail — the dispatch's three-way split (screenshots are ground truth)
- **PASS-pure-slow:** `t90.jpeg` shows toutiao's own UI (splash / privacy dialog / feed skeleton), OR hilog shows
  `activityResumed (first-frame)` / `handleLaunchActivity` reached by t90. → toutiao is *only* interpreter-slow;
  **JIT/AOT is the correct lever** (Part 2). A t60-class window would then be enough to A/B a JIT build.
- **FAIL-native-wall:** the process dies before t90, OR a `signal 11` is followed by a `cppcrash`/tombstone (the
  stageB handled-SIGSEGV turns out to be a real native wall, not benign probing). → **there is another wall behind the
  slowness**; capture and name it (faulting pc / library / the Java frame at the abort) — JIT would not move it; route
  to a native-fault lane (Claude).
- **STILL-IN-INIT (even slower):** at t90 the main thread is still in `handleBindApplication` /
  `installContentProviders` churn with no `callApplicationOnCreate`, no crash. → toutiao is slower than the window;
  the budget estimate (createSession ≫ 90 s) holds; the next arm is a JIT A/B (does JIT get it past onCreate at all)
  or a longer window.

## Readback (must hold, else inconclusive)
- `record.json` captured count = `facts.txt` (count from facts, not plan — AGENTS #63/#71).
- runtime fingerprint == unified state (no accidental base drift).
- Screenshots are the verdict; hilog phase markers corroborate.

## Cost
One key (toutiao), ~95 s runtime + install + three screenshots, single board. Well under 30 min including
lock / launch / revert. No rollback needed (nothing was changed); just unlock the board.
