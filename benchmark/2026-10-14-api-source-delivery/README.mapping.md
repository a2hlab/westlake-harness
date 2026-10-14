# Source/build mapping release v1

Earlier rows linked reports or external worktrees. This release maps all315 immutable API/index records, with304 source references verified against master42c87ab42b. Every non-null direct build entry is an exact tracked MAIN file. It preserves all original API grades. Missing source, stub behavior, partial build closure and historical output differences remain explicit.

T0 owns README.md, results.json, generate.py and views. This package changes none of them. Use SYNC-T0-FINAL.md for exact input hashes and the original T0 build/check command. The two stable metadata slices have landed at2db1b58511. final-checks/consumer.json records a subsequent call to the original MAIN consumer without producer metadata fallback.

Later Java has a new83-source/160-class javac rc0 receipt; no historical runtime/DEX equivalence. J1/J7b whole-overlay producers returned0 but strict wrappers returned2 for different bytes. TagSoup newDEX matches historicalDEX while JAR bytes differ. Later native source blobs and original scripts are delivered, without a new native build claim. A legacy DevEco compiler dependency remains unavailable locally. Known source gaps remain, and no all315-complete claim is made.

Reproduce in a fresh output directory:

```sh
python3 benchmark/2026-10-14-api-source-delivery/map_sources.py --main "$WORKSPACES/westlake-harness" --master-revision 42c87ab42b896c68762b88f943ee40b6bd3bfa45 --out "$FRESH_MAPPING"
T5_MAPPING_DIR="$FRESH_MAPPING" python3 benchmark/2026-10-14-api-source-delivery/test_mapping.py
```

The source tree and all referenced stable metadata must retain their pinned bytes. Source resolution reports are frozen snapshots, not the mutable final-delivery-review report. No build or device command is executed. Future source additions belong in a separate release.
