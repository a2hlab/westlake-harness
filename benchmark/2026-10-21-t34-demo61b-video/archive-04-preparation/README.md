# W04 private archive preparation

This is a narrow successor to archive-03-preparation/archive.py, not an upload receipt. No snapshot, SSH, SCP, device command or upload was executed during preparation.

The unique destination alias is `HW248_ARTIFACT_ROOT/t34-demo61b-video-20261021/window-04.tar.gz`. Existing window.tar.gz and window-03.tar.gz are untouched. The existing exclusive reserve plus hard-link publication refuses overwrite. The reserve is0700 and archive0600; every archive member is0600. Original source bytes, including failed wrapper receipts and relocation records, are preserved.

Roots include all W-04, the separate read-only W04-after-close-read-01 (exact spelling, outside the closed window), root t34-window-driver-outer-01, the current t34-environment-read-20261021 (including app-package-01), and the explicit environment, candidate-view and driver author/independent peer roots. No previous W03 directory is silently relabeled as W04. Every file receives byte count/SHA, local archive readback verifies all members, source metadata is re-inventoried before network, and the reused original remote verifier checks archive SHA/size plus every member. Symlinks or files changing during packaging reject the snapshot.

Wait for outer confirmation that the actual W04 recovery has closed and unlocked. The root-authored confirmation must name only W-04, use approved_by=outer(codex), status=CLOSED_AND_UNLOCKED, and list real evidence paths/SHA including W-04/recover-reviewed/closed.json. That receipt must say RESTORED_UNLOCKED/held_after_rc1 and match the actual W04 admission holder/start. Old W03 approval is rejected before creating output or accessing the network.

```sh
python3 archive.py
# Only after actual closure and explicit outer authorization:
python3 archive.py --execute --closed-confirmation "$W04_CLOSED_CONFIRMATION" --out "$NEW_PRIVATE_ARCHIVE_OUTPUT"
```

The output directory must be new and outside every source root. Actual endpoint/credentials are read from the already successful private archive01 command receipts; no account paths are published. A failed upload preserves its original commands and partial artifacts; do not blindly rerun or delete the reservation. The next public receipt must be generated from actual receipt.json and source-member verification, never from this prepared plan.

Revision02 adds these two exact source roots only. Inventory requires both directories actually exist; packaging must wait for CC completion/freeze and renewed outer authorization. No archive execution was performed by this revision.
