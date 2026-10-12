# Restore v5 frozen delta review

## Evidence and decision

**Exact offline delta accept, disabled** freeze `756c57e899ff89855f12bc174fdcd35c1e10fdd01ffb5d11b01501e193087ed8`. This is not origin-seal equivalence, writing authority, startup/UI acceptance, or a signed seal. The user-derived realization policy remains pending; 5cd is not written.

The intermediate v4 r2b freeze `3bcb54df7af6721f521e6c6babea14013692f1b9cd534f96ce3008941a63c57c` has 27 verified rows. Provider `52e02439`, manifest `3555eaecc`, and plan `593c002c` are byte-identical to the already-reviewed preparatory snapshot. No logic matrix was rerun.

V5 has 20 freeze rows plus freeze/ACK/landing (23 delivery paths), 486 unique manifest file records, and 487 target rows: 24 controls, 460 runtime, three stage. These counts describe different objects. All frozen row hashes and manifest file SHA/sizes, all target-to-local-source links, and all 13 boot-member bindings were independently checked.

## Changes and retained boundaries

- Exactly eight target SHAs change: entry, three helper aliases, members, startup, startup expected hash, and readiness worker. The full old/new target list is recorded in `evidence/restore-v5-756c/result.json`.
- Every target field other than its content SHA is identical to v4, including actual **5cd** before shape and per-file metadata. The binding changes only guardian provenance/update pin; storage, directory guards, runtime/stage source metadata, preserved stop, and control-source observations remain unchanged.
- The r3 source checkpoint and all 17 constituent file bytes match exact Git commit `69e15c4ae058d1fe17ba5f4355883e460ac9859b`. Helper and worker are exact r3 blobs. Watchdog and launch-common remain v4-identical. No source 61b authorization or startup template is imported.
- Provider changes are confined to `guardian_update` (allow the pinned r3 helper plus worker), `compile_package` (select those two sources), and self-test discovery. All other function ASTs match v4; executor bytes match v4. This preserves the previously accepted rollback/cleanup transaction behavior rather than rerunning its matrix.
- Actual packaged helper rejects 61b UID `20011206` against required 5cd UID `20011300`, emits one od diagnostic, and resets an inherited quiet flag. Boot members include the new worker exactly once; startup remains disabled/PENDING with a valid refreshed member/hash chain.

The original 61b exact-seal dynamic-field incompatibility is not silently weakened by this candidate. Three runtime UID/WID-derived scripts are not claimed unchanged from the original archive; v4's explicit realization binding is retained. Real c30 worker-budget validation remains outer's task and cannot be inferred from this restore package.

## Reproduction and raw output

`review_restore_v5_delta.py` is an independent read-only local checker. Its raw JSON stdout is recorded with exit 0; no v3 matrix, board, VM, remote command, installation, signal, or data mutation occurs. Frozen source/package metadata are copied to a private archive after matching their pins. Candidate sources remain unmodified.
