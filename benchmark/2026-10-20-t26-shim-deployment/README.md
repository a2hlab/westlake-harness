# T26 + T27 single-candidate deployment data

The original disabled data is preserved byte-for-byte in history-pending, including its original checker and receipt. The root check_pending.py is retained as historical code; replay the preserved state through history-pending/check_pending.py. The actual production-02 output and 12 public production references are independently verified, including all 63 public manifest files. Fresh outer admission remains required.

The executor remains byte-identical to T25, SHA `693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb`. The other five artifact entries remain unchanged. Original six-state CAS, complete backups before swaps, metadata/labels/private inode checks, original apply-plan rollback, dynamic WID, fresh boot, 1800-second budget and 600-second recovery reserve remain unchanged. Existing t21 stage/backup naming is retained as part of the original executor.

The actual combined candidate is `fc58cec5c7a445a28ed0c0e3ec44d486f16f0921afe8ef4b6974bd96ca9574e9`, 96680 bytes. Independent ELF inspection finds geometry `0xe3c0`, lock `0x6ec8`, unlock `0x6edc`. All 116 producer input pins, 12 outputs and 25 raw command receipts were checked. This is an offline production check, not deployment authorization or playback evidence. See candidate-inspection.json.

Final data verification reuses T25 check_final.py with only the new three export offsets and the current exact production manifest (no T25-specific source-index path):

```sh
python3 benchmark/2026-10-20-t26-shim-deployment/check_final.py --source-root "$WORKSPACES/westlake-harness" --source-root "$WORKSPACES/westlake-harness-t4" --out "$HOME/.local/share/westlake/t26-deployment-data/final-01"
```

The final checker verifies the public production references and performs six original-executor previews/refusal sentinels. PRODUCTION_BUILD_VERIFIED denotes checked offline construction only; the producer explicitly retains OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED. Null fresh metadata still rejects execution before Board import. Fresh approval/holder/boot/host/metadata and live three-slot evidence remain null. The known player relocation offsets are static exact-player input; candidate exports do not establish live GOT targets. Historical readonly-inputs.json is not fresh admission.
