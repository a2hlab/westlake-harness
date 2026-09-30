# N2 handoff — device unverified

Package `/Users/zhaoyue/orca/workspaces/westlake-generation-n2-51a78bde` is based on
accepted N1 aa57845c. No board is assigned to this work; wait for the outer's slot.
Do not overlap U1. `rollout_ready=false` means screenshots remain under human review.
Do not change the flag just to claim success.

## Before / apply / rollback

1. Obtain the exact board lock using board_note.sh and confirm held. Record boot ID,
   active package ledger, SHA fingerprint, current JAR receipt and installer SHA.
   Require current native N1 and keep the same J2 JAR (0715c964) across A/B. If the
   outer has advanced U1, rebase declarations and rerun dry-run before any write.
2. Capture baseline controls/targets with master bms_batch and 16M preflight. Retain
   the current JAR receipt; expose package r8b using the same receipt-based JAR tool
   used by N1, checking hashes before/after. Never blindly unmount a stale receipt.
3. Run from this worktree (VM invokes hdc_mac.sh):

```sh
scripts/lab/deploy_generation.sh "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-generation-n2-51a78bde --upgrade --dry-run
scripts/lab/deploy_generation.sh "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-generation-n2-51a78bde --upgrade --lane cx-t0
```

4. Restore the same captured J2 overlay. Verify SHA, single ART, ANL route/android
   aliases and private ABI file hashes. Run HW/ZZ first, then targets and protections.
   Use master `benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py`, controls.json
   for HW/ZZ, `--reinstall --hilog 20 --shots 5,20 --focus-check`, serial-bearing run ID.
   Target keys: `localsend,fd-immich,fd-fluffychat,fd-kitchenowl,fd-libre,fd-saber,
   firefox,fd-fennec_fdroid,fd-shatteredpixeldungeon,opencamera,vlc,fd-uhabits,noice`.
   Protections: `aegis,fd-auxio,fd-droidify,fd-netguard,newpipe`; add fitness if time allows.
5. Stop immediately on a control regression. Always return to the entry unified
   baseline at the end of the <=45 minute window unless outer explicitly signs N2:
   expose package JAR from its receipt, then

```sh
scripts/lab/deploy_generation.sh "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-generation-n2-51a78bde --rollback --lane cx-t0
```

   Reapply the same JAR receipt, verify parent hashes/ART/maps/socket, HW smoke, unlock.
   Use deployer's begetctl service stop/start; never kill -9 appspawn-x.

## Evidence and predictions

Use `dispositions.json` checkpoints. Require `[N2-OWNER] ABI global ready` and
`[ANL-N2]` for the selected load and prove runtime's real mapping, not merely a file
on disk. Save first fatal before/after by PID/time. Camera registration alone is not
camera success; GL registration alone is not rendering success. Existing OH version
mismatches and Skia intermittent crashes remain explicit limitations.

Paste facts.txt unchanged, give every t20 screenshot path, and use compare_runs.py
on actual fingerprints. Mark all package paths changed (including private ABI paths)
even if an older fingerprint scanner omits private subdirectories. This is a native
batch intervention, not attribution to a single function. Human review is required.

Current device facts/screenshots: **unknown — no N2 run performed**.
