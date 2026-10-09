# Disabled round-three post-reboot execution plan

## Evidence first

**Reboot success is not demo readiness.** The draft requires fresh effective
seal comparison after a changed boot ID; it cannot reuse t3 identity or a prior
boot's bind overlays. If a special overlay disappears, readiness fails and no
manual bootstrap/rebind is hidden in the round. There is no executable device
dispatcher here: `prepare.py` only compiles JSON and `execution_enabled=false`.

The current draft binds the exact manifest and `shot-tiers.json` bytes and both
explicit overlay slots. It contains all 128 selected packages in manifest order,
121 captures at 10 seconds and seven at 20 seconds: **1350 seconds** of nominal
capture waits, excluding launch/read/infra overhead. Stable/edge grouping does
not alter capture duration. Pending special slots are preserved as blockers;
when approved active, regeneration adds Toutiao/BoatAttack at 20 seconds each.
Route B launches the existing imehost embedded route, not the Android package
through unified BMS; its launch recipe still requires cc-t3/outer binding.

## Execution handoff (cx-t0, after outer authorization)

1. Bind the final t3 signoff and compiled seal, final overlay decisions, actual
   smoke/identity hooks and fresh outer authorization. Verify every input SHA.
2. Perform read-only exact-serial checks, obtain the existing exclusive lock,
   repeat identity checks and capture the old boot ID. Only then reboot once.
3. Poll only 61b for at most 600 seconds. Require a new boot ID, actual seal
   selfcheck rc0, launcher/display readiness and no manual recovery steps.
   Timeout emits **aborted + timestamp + outer notification**; it is not PASS,
   no other board is substituted and lock disposition remains with outer.
4. Launch installed packages continuously, without install/uninstall, runtime
   change or guessed taps. Capture the actual `snapshot_display` image at each
   tier, retain raw hilog, record/facts and PID attribution. A missing/dead/empty/
   loading/error screen is not own content. Outer signs screenshots.
5. Game interactions and SAFE Route B Toutiao acceptance run after the initial capture pass,
   with observed controls, before/after screenshots and raw acceptance output.
   The 32 empty screens remain optional; no unverified coordinate is executed.
   Route B stock provision/acceptance scripts can kill the main appspawn-x;
   only the bound reviewed SAFE recipe is admissible. No hidden reinstall or
   runtime repair is permitted during post-reboot acceptance.
6. Final fresh same-boot selfcheck, retain evidence and unlock through the
   existing executor. If the 35-minute stop-new-tests cutoff is reached, stop
   opening new keys; before 45 minutes close safely. A later authorized window
   resumes only remaining keys on that same post-reboot boot, not another reboot.

The runner delay remains the production runner's launch elapsed time; physical
child timing determines the precomputed tier and fresh hilog remains evidence.
Do not change production scheduling origin without explicitly rebinding the
runner. This draft is not a `board_run` authorization or executable plan: null
seal/signoff/authorization fields must be filled by cx-t0/outer at admission.

```sh
python3 benchmark/2026-10-09-demo-baseline/t4/round3-plan/prepare.py \
  --out "$FRESH_DISABLED_ROUND3_PLAN"
python3 benchmark/2026-10-09-demo-baseline/t4/round3-plan/test_plan.py
```

No board, lock, VM, SSH, registry or promotion action occurs in this delivery.
