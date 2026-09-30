# sweep_bind_deploy — reusable bind-overlay sweep harness (U6-derived, for U7+)

Turns the U6 three-board sweep that cc-t3 ran by hand into one reusable, testable tool so U7 (and any
later bind-composed candidate) runs it directly.

## What it does (one board)
`lock -> preflight -> backup baseline shas -> stage -> mount --bind each artifact -> restart
appspawn-x (begetctl, never kill -9) -> verify EVERY expected-run.json file through the appspawn-x
child view /proc/<root-pid>/root<path> -> bms_batch shard (--reinstall --hilog 20 --shots 5,20
--focus-check) -> rollback (umount all + verify RUNTIME/BOOT fingerprints back to the U-baseline) ->
unlock.` libart is never touched; the overlay is exact-byte reversible.

Not a persister — persisting to /system is deploy_generation's job with a real generation package
(U7). This is the on-board sweep harness only.

## Why the child-view verify
The U6 rule: an image/jar swap only counts if the app actually sees it. Binds propagate into the
appspawn-x child mount namespace, so every one of the 119 runtime + 36 boot files is hashed at
`/proc/<appspawn-root>/root<path>` and compared to expected-run.json before any app runs. `RUNTIME`
excludes the BCP jars + boot image on purpose (a jar-only fingerprint; boot changes show in `BOOT`).

## Modes
- `--self-test` — 8 off-board unit tests of the pure logic (bind parsing incl. images-dir expansion,
  expected-run merge, the order-independent fingerprint, dest set). No board, no hdc.
- `--dry-run` — validate args + print the full plan (bind count, verify count, rollback fingerprints,
  sweep keys, flow). Touches no board.
- `--no-run` / `--no-rollback` — deploy-only smoke / leave the overlay for the caller.

## U7 usage (the U6 recipe, parameterised)
```
sweep_bind_deploy.sh --serial <sn> --lane cc-t3 \
  --bind <U7 runtime jar>:/system/android/framework/oh-adapter-runtime.jar \
  --bind <U7 stubs jar>:/system/android/framework/adapter-mainline-stubs.jar \
  --images-dir <U7 27 boot images> \
  --expected <U7 expected-run.json> \
  --bms-batch <master bms_batch.py> --manifest <master apps.json> \
  --keys keys-<board>.txt --input-root <inputs root> \
  --note-cmd <board_note.sh> --board-md <app-lighting.md> \
  --rollback-runtime-fp <U-baseline runtime fp> --rollback-boot-fp <U-baseline boot fp> \
  --out <run dir>
```
On the Mac, `source westlake-inputs/env-mac.sh` first (sha256sum shim); `--hdc` defaults to the
DevEco hdc. To run everything in the VM, pass `--hdc`/`--bms-hdc-cmd` the hdc_mac.sh forwarder.

Reproduce: `scripts/lab/sweep_bind_deploy.replay.sh` (self-test + synthetic dry-run, no board).

## Provenance
Derived byte-for-byte from the U6 sweep (benchmark/2026-10-01-u6-sweep): the same three-layer bind
(J7b 381110a6 + T7c 27 images + stubs 366acc27), the same 155-file child-view verify (5cd/61b/5ea all
155/155), the same rollback that reverified RUNTIME 73ecf422dba2 / BOOT 0876029078e2 on all three.
The real-args dry-run reproduces that exact plan (29 binds, 155 verify).
