# Installation-chain identity

U9's 119-file runtime fingerprint and 316 assertions omitted libinstalls. Identical APK `7070a3d4` installed on 61b with `51e1b525`, but failed with `9568260` on 5ea and 5cd with `2c9a5294`. The three rejected ZIP payloads match the approved #79 native-data exception table exactly. Outer review signed U9 at 115/166 lit, with zero runtime regressions after Seal's 61b follow-up. This version difference must remain visible until daytime service alignment.

## Tool changes, no device changes

`installation_chain.py` defines all six aliases for libbms, libapk_installer and libinstalls. Both `sweep_bind_deploy.FINGERPRINT_PATHS` and `bms_batch.FINGERPRINT_PATHS` use this shared list. New fingerprints include 123 files instead of 119. The U9 finish/read-baseline hooks add the per-board libinstalls expectations: 312 core assertions plus six service assertions, with two overlapping paths, yield **318 assertions / 316 unique paths**. The signed U9 package and original receipts are unchanged.

| Board | libinstalls, both aliases | Legacy runtime | Extended runtime |
|---|---|---|---|
| 5ea | 2c9a5294 | a8cb9a5a45a6 | 565fc6fdc116 |
| 5cd | 2c9a5294 | a8cb9a5a45a6 | 565fc6fdc116 |
| 61b | 51e1b525 | a8cb9a5a45a6 | a2919b793eb6 |

These extended fingerprints are calculated from archived per-file runtime readbacks plus the six already observed service aliases. They are not new board observations. `current-u9.json` records the inputs. **The installation chain is not unified.** Do not mark the differing values equal or relabel old records with the new schema. Future smoke specs must use the board's extended value after this tool change lands; generation runtime references must include the six service aliases when next assembled.

## Actual loading, not just disk files

A batch now records `installation-chain/installation-chain.json` before running keys and embeds the receipt in `baseline.json`. It finds exact service names from `ps`, reads their maps, and hashes relevant paths through `/proc/<pid>/root`. It compares mapped inode with the process-root file inode as well as SHA: a replaced disk path must not falsely validate an older loaded mapping. Deleted mappings, missing disk aliases or observed SHA/inode mismatches reject the batch. Absent on-demand services and unobserved libraries are **unknown**, rather than claimed verified. No service is started to fill an evidence gap. All service observations, including unknown status, stay in the receipt.

The standalone collector requires an existing lane board lock and boot guard. It is read-only. This delivery contains no new service loading observation; existing #79 evidence of the 61b service remains historical evidence. During the next approved batch/verification, capture both foundation/BMS and installs mappings before declaring the aligned services verified.

## Alignment proposal

Use the outer-approved [source and ABI plan](../2026-10-01-libinstalls-align/plan-draft.md): deploy the b79 source artifact `51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5`, not a live copy from 61b. Its 1096 exports match the old library; the exact ZIP exceptions are retained. Keep the frozen libbms `6aadb8b4` and libapk_installer `7048c7c5` unchanged.

Extend the existing service swap transaction to only libinstalls and its two aliases, with verified `2c9a5294` rollback copies. One board at a time, **daytime with the user present**; foundation restart may trigger a reboot/USB loss. Announce the restart first. If a reboot occurs, use the **current U9 executor/bundle** to restore the signed native + J10g + T7e composition, not the older v3a/v4 recipe mentioned in the draft. Never claim recovery before verifying the current U9 identities, both fingerprints and controls.

After replacement, verify disk aliases and actual foundation/installs loader identities; clean-install Seal, Toutiao and X as #79 installation controls, then HelloWorld and the approved U9 lit controls. Outer screenshot review is still required for lit verdicts. After both 5ea and 5cd accept 51e1, update `current-u9.json` to the single reviewed service version and recalculate the new reference fingerprints. No service replacement or restart is authorized by this tool-only delivery.

## Validation

Six tests cover exact service selection, mapping deduplication, stale/deleted mappings, SHA/inode mismatch, absent services as unknown, synchronized fingerprint paths and detection of a libinstalls-only change. Eight sweep helper tests and five U9 retention/identity tests also pass. The Seal follow-up facts are recorded verbatim under `approved-j10g/evidence/61b-seal/`.
