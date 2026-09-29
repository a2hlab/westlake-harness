# 61b installer-only A/B handoff

Prepared entirely on Mac, from the accepted `../2026-09-30-installer-background-launcher/HANDOFF.md` and unchanged library bytes. Only serial/lane/transaction directories differ in the copied script. `dry-run.json` confirms device_io=false. Do not execute until cc-t3 has written UNLOCK and cx-t0 owns the full-key lock.

The 17 keys are in `keys.txt`; the 14 predicted permission-wall cases are linked to the original r17p trace evidence. Pin Java to r17p `a0ed5c4fedd952762256a24ab7801deb3ad6e696a0204853ce5000316336d173`. Capture the current JAR receipt at lock acquisition, not from an earlier query. `board_state.py capture` verifies native bytes match the r17p baseline before any write; `pin-jar` changes only Java if required and verifies the parent's host/JAR. Native graphics must stay at the original resident SHA, not 32df.

## On Mac, after lock acquisition and JAR capture/pinning

Announce `将重启 61b` on the board first. The board is behind the USB hub; a foundation restart can black-screen or reboot it. Record the original boot and runtime package before apply. If USB disappears, do not issue commands against another serial.

```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-61b/swap_services.py dry-run
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-61b/swap_services.py apply
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-61b/swap_services.py restart
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-61b/swap_services.py verify
```

Exact rollback (four backed-up paths, pair restored together):

```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-61b/swap_services.py rollback
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-61b/swap_services.py restart
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4-61b/swap_services.py verify
```

Backup receipt: `/Users/zhaoyue/orca/workspaces/westlake-generation-state/61b0657200000000000000000324012c/installer-background-launcher-ab90/state.json`; remote originals `/data/local/tmp/installer-background-launcher-ab90/backup/`. Rollback does not undo per-package ATM token changes; clean reinstall is needed for permission A/B.

If the authorized recovery requires reboot, restore the exact package captured in `original.json` with the existing generation deployer, **without --upgrade on a new boot**, then re-pin the same r17p. No rebuild or different native package. The expected current offline ledger is v3c668e4f7c; the live lock-time capture has precedence. Record reboot as an experimental covariate.

## Acceptance

Use master bms_batch with `--reinstall --hilog 20 --shots 5,20 --focus-check`, input root with the original app inventories and the unchanged HelloWorld control. All 17 entries are required. Check actual WMS `canStartAbilityFromBackground:1`, package request and permission trace; a StartAbility return of zero is insufficient. Archive exact facts and each t20 path. Compare 117 runtime paths before/after: only the installer pair differs from old r17p; preserve native and graphics. UI conclusions belong to screenshot review. AntennaPod/FitoTrack are controls for cross-board discrepancies, not guaranteed fixes.
