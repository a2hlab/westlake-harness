# T25 deployment data preparation

T23 audible playback was confirmed by the user, but its images did not pass video acceptance. This package prepares a geometry candidate without treating that earlier audio result as T25 validation.

The executor is copied byte-for-byte from the accepted T23 transaction: SHA256 `693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb`. Six donor files and the other five artifact states are unchanged. Five original file backups plus the absent-only compat marker, CAS, exact metadata, partial rollback, original apply-plan, and the 1800-second window with 600 seconds reserved for recovery remain the same. This is data preparation, not a new executor.

`shim-candidate.json` deliberately has no candidate hash or production receipt yet. `admission.template.json` contains no approval, boot, holder, process identity or fresh metadata. Historical values inside the unchanged `readonly-inputs.json` remain historical. They cannot supply a new window identity. Preview is harmless; explicit execution of this pending package rejects before Board import.

`three-slot-admission.json` requires geometry, lock and unlock from the same exact player instance: relocation offsets `0x472048`, `0x472490`, and `0x472760`. These were independently read from player SHA `0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471`. All new candidate export offsets are pending. After loading, actual slot values must select the corresponding exports of one exact T25 shim instance. This is a separate outer evidence requirement; the unchanged deployment executor does not inspect GOT slots. Pair logs or a geometry return code cannot replace it.

Before making final data: verify the immutable production receipt, source snapshots, raw build return codes, baseline reproduction, exact candidate SHA/size, ABI and independent review; read all three candidate symbols from that ELF; update only candidate data and dependent hashes. Fresh window approval remains an outer action. No device command or candidate build was performed by this package author.

Recheck the pending package offline:

```sh
python3 benchmark/2026-10-20-t25-shim-deployment/check_pending.py \
  --repo "$WORKSPACES/westlake-harness" \
  --out "$HOME/.local/share/westlake/t25-deployment-data/pending-check-new"
```
