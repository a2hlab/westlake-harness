# T25 production-02 deployment data

T23 audible playback was confirmed by the user, but its images did not pass video acceptance. This package prepares a geometry candidate without treating that earlier audio result as T25 validation.

The executor is copied byte-for-byte from the accepted T23 transaction: SHA256 `693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb`. Six donor files and the other five artifact states are unchanged. Five original file backups plus the absent-only compat marker, CAS, exact metadata, partial rollback, original apply-plan, and the 1800-second window with 600 seconds reserved for recovery remain the same. This is data preparation, not a new executor.

`shim-candidate.json` pins the actual production-02 candidate `2a867f78905bdc37020bec36c951f628c6393456a1770514c1d73f974fd3d5bc`, 82,112 bytes. The actual local build receipt check passed: 9 commands, 63 inputs, exact T23 baseline reproduction and one added geometry export. Public source/build/raw evidence references are individually hashed. `admission.template.json` still contains no approval, boot, holder, process identity or fresh metadata. Historical values inside the unchanged `readonly-inputs.json` remain historical. They cannot supply a new window identity. Explicit execution with the unsigned template rejects before Board import.

`three-slot-admission.json` requires geometry, lock and unlock from the same exact player instance: relocation offsets `0x472048`, `0x472490`, and `0x472760`. These were independently read from player SHA `0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471`. The exact new shim export offsets are respectively `0xd7e4`, `0x6c28`, and `0x6c3c`; the old T23 offsets must not be reused. After loading, actual slot values must select these corresponding exports of one exact T25 shim instance. This is a separate outer evidence requirement hashed into the admission template; the unchanged deployment executor does not inspect GOT slots. Pair logs or a geometry return code cannot replace it.

The original pending package is preserved byte-for-byte from commit `8e9c1a341` in `history-pending/`, including its historical manifest and check results. `candidate-inspection.json` records the earlier local inspection; its then-pending public-reference status is historical. The final manifest and checker refer to current data. Fresh window approval remains an outer action. No device command or candidate build was performed by this package author.

Recheck the final static data offline (add another `--source-root` only when reviewing exact files before main landing):

```sh
python3 benchmark/2026-10-20-t25-shim-deployment/check_final.py \
  --source-root "$WORKSPACES/westlake-harness" \
  --out "$HOME/.local/share/westlake/t25-deployment-data/final-check-new"
```
