# Video-window closure preparation (not executed)

Checkpoint01 is immutable. Current same-plan 64-target / 351-label invariants are equal, but baseline child8654/b18108 exited before a feed image. Parent6101/b16617 remained. One normal icon reentry is being checked by the outer. These facts do not constitute complete restoration or explain any exit.

The two local-only scripts are prepared for terminal inputs; neither has been run against an unfinished window. Both require an actual close receipt with `closed_at` or `unlocked_at`, matching the existing closure format. No close time, image verdict or live identity is synthesized.

1. After the final outer receipt and actual restored record/image exist, use:

```sh
python3 finalize.py --close "$BASE20/r13-video-close.json" \
  --restore-run "$ACTUAL_RESTORED_RECORD_DIRECTORY" --out "$NEW_FINAL_SUPPLEMENT"
```

This compares only existing same-plan invariants, pins the actual record/image, retains the raw close receipt, and runs MAIN's local facts helper on the real parent directory. It deliberately leaves independent image and final cleanup/identity review pending. The reviewer must read the actual image and terminal raw receipts before final acceptance. Both candidate exits and the baseline first-child failure remain in the complete raw inventory.

2. Once closure is accepted, prepare full raw evidence in a new persistent output:

```sh
python3 prepare_archive.py --close "$BASE20/r13-video-close.json" \
  --out "$NEW_PERSISTENT_ARCHIVE_OUTPUT"
```

Selection covers BASE19 `video-r13-video-*`, BASE20 `r13-video-*`, `video-tab-readonly`, historical outer/module/reboot scripts, R13 observer sources and specifications. Historical script inclusion is provenance, not a claim every script was invoked. Every regular member is hashed before packing, re-read from the tar and compared by SHA/size; all source hashes are checked again afterward. Original stdout/stderr/rc and failed attempts are retained privately. The generated private three-command argv file targets `HW248_ARTIFACT_ROOT/toutiao-r13-video-20261020/window.tar.gz`. Upload is opt-in; sandbox denial stops at the first error and must remain in the receipt. No upload or archive is performed at this preparation checkpoint.

Aliases BASE19/BASE20 resolve under `$HOME/.local/share/westlake/`; SOURCE_REPO may select MAIN. No production, frozen observer, checkpoint01, device or MAIN writes are authorized by these scripts. This is evidence preparation, not a new deployment or observation tool.
