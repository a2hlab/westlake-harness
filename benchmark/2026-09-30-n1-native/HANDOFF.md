# N1 native candidate: controlled acceptance pending

The first short-window discriminator changed only runtime U0 53f00423 to
d40ae63f. HelloWorld/ZigZag displayed their own interfaces. NewPipe retained
its own interface; uhabits survived to t20 with a blank white window. Fitness
crashed in RenderThread, so expansion to the complete native candidate stopped.
U0 clean recovery rendered Fitness in three consecutive t20 runs. This remains a control concern, not proof of deterministic causality from one candidate trial.
The complete package and six-package host owner callback have NOT been tested
on the device in this window. Do not promote to U1 from static tests alone.

## Immutable complete candidate

`/Users/zhaoyue/orca/workspaces/westlake-generation-n1-aa57845c`

See `release.json` for complete manifest and runtime hashes. Runtime 77639b80
includes the corrected newAudioSessionId object. The runtime-only d40 package
is a separate immutable artifact and lacks that one method.

After the control concern is adjudicated, on an explicitly allocated board:

1. Record current U0 ledger, boot, JAR receipt and fingerprint; acquire its lock.
2. Retire the recorded r17r overlay to the package's baked r8b JAR.
3. Run, in OrbStack, the repository deployer with SERIAL and LANE set to the
   allocated board/lane:

```sh
scripts/lab/deploy_generation.sh "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-generation-n1-aa57845c --dry-run --upgrade
scripts/lab/deploy_generation.sh "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-generation-n1-aa57845c --upgrade --lane "$LANE"
```

4. Restore the exact recorded JAR overlay. Check HW/ZZ before cluster apps.
   Use master bms_batch, --reinstall --hilog 20 --shots 5,20 --focus-check.
   First LocalSend/Immich, then JNA Firefox/Fennec, fd-plus SoundPool,
   VLC audio, Anki/BurgerKing ABI and NewPipe/uhabits frozen evidence.
5. Stop on a control regression. Retire JAR, undo with the same package and
   `--rollback`, then restore the receipt. Read SHA/boot back and unlock.
   `device-61b/rollback.sh runtime` undoes the discriminator specifically;
   its `full` mode is only for a full package layered over that discriminator.

Do not copy the 61b-specific JAR helper to another board unchanged.

## U1 handoff boundary

No U1 sweep ran here. After both J1 and N1 are accepted and identical manifests
are deployed on all three boards, use the external plan's immutable shards:
`westlake-harness-bms/benchmark/2026-09-30-round1-plan/shard/u1-v1/`.
The three key lists must be passed to master bms_batch on their declared serials;
use that directory's merge_facts.py to reject mixed fingerprints or missing
records. Retain all 66 keys and the N07/N09 unimplemented and N08 Java-boundary
rows in the denominator. `rollout_ready=false` remains intentional.
