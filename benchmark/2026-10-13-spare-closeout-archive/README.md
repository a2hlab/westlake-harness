# Spare-board contrast and sealed-board read-only closeout archive

A completed local run is not durable evidence until its original files are preserved and checked remotely. This archive preserves exactly `content-state-baseline947-r2/` and `final61b-readonly-preflight/` from the completed V2 outer evidence directory. No source file was modified and no external directory or app private-data backup was scanned or included.

- Durable archive: `hw248:/home/alvin/westlake-spare-closeout-20261013T222642-280dceba/spare-closeout.tar.gz`
- Archive SHA-256: `a77201ca09519f6ac7927893796f8a795db0d96a1de3ec635eeb7474f098627f`
- Archive size: 3,863,420 bytes; 3,913 source files totaling 53,044,715 bytes.
- Every source regular file was hashed before packaging and after; path, SHA-256, size, mode, inode, and nanosecond timestamps matched. Symlinks/nonregular files were refused.
- Every tar member was independently read and checked against the per-file manifest. The manifest is included as `__archive_meta__/source-manifest.jsonl`; SHA-256 `6c2514033e6757867cbcda09b56741670d66f823fb86a357d1c1be0e914f9372`.
- Local gzip integrity, remote gzip integrity, and independent remote archive SHA-256/size all passed. Exact stdout/stderr and exit status are retained beside `results.json`.

`completed-source-gates.json` records the source completion checks: two launch-only app records with lock released, and the distinct `verified940.json` live-readonly PASS report for 940 files. The earlier wrapper reused and overwrote `original940.json`; all original raw/stdout/stderr remain in this archive, and the corrected report and separate process receipt retain the explicit correction reason. No reconstructed report replaces that history.

The source two-app completion still says visual review pending; the archiver does not adjudicate screenshots or advance any seal verdict. Zero device calls, app-data writes, commits, or pushes. Completed 2026-10-13T22:26:44.513700+08:00.
