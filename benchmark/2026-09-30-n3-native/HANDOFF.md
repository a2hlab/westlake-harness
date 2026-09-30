# N3 handoff — device unverified

Package `/Users/zhaoyue/orca/workspaces/westlake-generation-n3-8a7880fa` upgrades
U2 native N2 `51a78bde`. Current device facts/screenshots: **unknown**. No board
window was allocated to cx-t0 for this offline task; wait for the outer's schedule.

1. Take the full serial's board_note.sh lock and confirm held. Save boot ID, active
   ledger, JAR receipt, installer identities and runtime fingerprint. Require U2
   `937e2a6d0d88` (native N2 + J2 `0715c964` + background installer), or have the
   outer explicitly select a later common baseline. Do not overwrite another lane.
2. Use the receipt-based JAR tool to expose package r8b; verify exact SHA rather
   than blindly unmounting. Retain the same captured JAR for A/B. Run preflight:

```sh
python3 scripts/lab/check_frozen.py --source-root . --package /Users/zhaoyue/orca/workspaces/westlake-generation-n3-8a7880fa
scripts/lab/deploy_generation.sh "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-generation-n3-8a7880fa --upgrade --dry-run
scripts/lab/deploy_generation.sh "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-generation-n3-8a7880fa --upgrade --lane cx-t0
```

3. Restore the same JAR overlay. Verify SHA, single ART, ANL aliases, host, private
   facades and ABI declarations. HW/ZZ controls first, then LocalSend/Immich,
   remaining Flutter, Unciv/SPD, Firefox/Fennec, Mindustry/PPSSPP, VLC and native-domain
   targets. Protect Anki, Auxio, NetGuard, Droid-ify, Fitness and AntennaPod.
   Use master bms_batch, controls.json for HW/ZZ, `--reinstall --hilog 20
   --shots 5,20 --focus-check`. Respect the assigned window (maximum 45 minute batch);
   use outer-assigned shards rather than trying all targets on one board.
4. Inspect `[N3-OWNER]` HiLog and child maps. Require one resident runtime and ART,
   no second provider caused by library reopening. Prove JNI lookup progressed;
   no success inference from files existing. Compare each first fatal with
   `dispositions.json`. Preserve Xpm/header errors if they remain. Audio symbol
   resolution is not playback; engine initialization is not Flutter UI.
5. Control regression means stop and rollback. Unless outer signs a new baseline,
   always restore U2 after the window: expose r8b from the receipt, then

```sh
scripts/lab/deploy_generation.sh "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-generation-n3-8a7880fa --rollback --lane cx-t0
```

   Reapply original J2, verify **937e2a6d0d88**, installer SHA, maps/single ART and HW
   smoke. Unlock immediately. Use begetctl stop/start, never kill -9 appspawn-x.

Paste facts.txt unchanged, every t20 screenshot path, and compare_runs.py output.
This is a native batch intervention: all 11 changed paths count, including private
paths omitted by old fingerprint scanners. No single-function causal claim from
this batch. Resource/context fixes must be separated from GLS supply in attribution.
