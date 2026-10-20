# T28 RGBX deployment data

This data replaces only the T26 shim candidate with T28 RGBX production-01. The original executor is byte-identical, SHA256 `693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb`; the other five artifact entries are exactly unchanged. Six-state CAS, backups, metadata/inode checks, original apply-plan rollback, dynamic WID, fresh boot, 1800-second budget and 600-second recovery reserve remain inherited.

The independently inspected candidate is 97,464 bytes, SHA256 `89b9a8b9868bb35d3cd70108e9114714c7f525cbed7006974b4f095912ff0b33`. Geometry is `0xe3b0`, lock `0x6ec0`, unlock `0x6ed4`. All 156 producer input pins, 14 outputs and 28 original command receipts were checked; 11 compilation commands enable both observer and GNU macros. The 78 versioned exports match T26 and NEEDED remains libc.so, with no TEXTREL. See candidate-inspection.json and [source/build](../2026-10-20-t28-rgbx/README.md).

The checker reuses T26, changing only T28 target labels, donor-parameter filename, three export offsets and producer manifest path. It checks exact public references and executes six preview/refusal sentinels, never a device transaction:

```sh
python3 benchmark/2026-10-20-t28-shim-deployment/check_final.py --source-root "$WORKSPACES/westlake-harness" --source-root "$WORKSPACES/westlake-harness-t4" --out "$HOME/.local/share/westlake/t28-deployment-data/final-01"
```

Fresh approval, holder, boot, host PID/birth, metadata and live three-slot evidence are null. PRODUCTION_BUILD_VERIFIED means offline construction only. Fresh outer admission is required. Historical readonly inputs and static export offsets do not establish a current device binding, playback or seal decision. T26 history remains in its original directory; donor-t26-parameters.json is the exact final T26 data used for comparison.
