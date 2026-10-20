# T29 dual-artifact deployment data

The original pending template could not bind a new bridge or its shifted owner addresses. `history-pending/` preserves those original files byte-for-byte. The final data binds the actual joint production outputs: bridge `b0e5602a…` (2,023,136 bytes) and shim `9f3cecde…` (106,456 bytes). The transaction executor remains exact `693448c2…`; run, compat, media and player parameters are unchanged.

Fifteen public production references include the 22-command build receipt, original raw index, JNI tables, generated owner binding, source/build pins and independent production review. The production receipt still says the original objects are not byte-identical. The separate peer proves that each differs only in 38 bytes of the non-ALLOC `.comment` compiler revision; this is not described as exact object reproduction.

Actual ELF inspection confirms shim geometry/lock/unlock offsets `0xf488 / 0x72c8 / 0x72dc`; bridge get/acquire/release `0x12670c / 0x126748 / 0x126798`, Reference/Unreference slots `0x175520 / 0x175448`. These are static offsets, not measured runtime winners. Fresh admission, actual slot values and provider-instance receipt remain null.

## Recheck

```sh
python3 benchmark/2026-10-20-t29-deployment/check_final.py \
  --source-root "$WORKSPACES/westlake-harness" \
  --out "$HOME/.local/share/westlake/t29-deployment-final/replay-unique"
cargo test --manifest-path tools/spec-checks/Cargo.toml \
  --test toutiao_t29_deployment ttvideo_t29_deployment_final -- --exact
```

`check_final.py` verifies actual public references and all data cross-links, then calls the unchanged executor in three preview modes and three execute sentinels. Execute stops at the unsigned template's missing fresh metadata before Board import. The two final Python tests cover actual references and five deliberate drifts. The old pending test now reads the preserved historical directory; it was not rerun as part of this final increment.

Root must collect a **fresh T29** baseline and identity, sign an actual admission, retain original apply-plan backups, and enforce the existing 1800-second window with 600-second restoration reserve. T26 reused baseline is not a fresh T29 baseline. No deployment, playback or seal result is claimed here.

Evidence: `candidate-inspection.json`, `final-check-results.json`, `results.json`, and `final-private-raw-index.json`. Original pending evidence remains in `history-pending/`. Parent/private inode, metadata, labels, mixed-state rollback, fresh boot and same-instance routing checks retain their existing scope.
