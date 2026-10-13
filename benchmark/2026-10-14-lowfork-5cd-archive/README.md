# Fixed5cd metadata A/B durable archive

Runtime success alone does not preserve the original comparison. This archive retains only the closed `metadata-lowfork-5cd-20261014T011836/` directory: exact enabled plan and authorization, original/candidate raw stdout/stderr,54 logical calls, timings, and holder receipts. Root confirmed session75745 rc0 and successful trap lock release; no source marker was added by the archiver.

- Durable landing: `hw248:/home/alvin/westlake-metadata-lowfork-5cd-20261014T012214-016918ca/metadata-lowfork-5cd.tar.gz`
- SHA-256: `4da142c3aa10d3ad4b09c86e8ddcc82a5656298276cb3294e1bb087630091770`
- Archive size: 40,124 bytes; 121 source files totaling 457,929 bytes.
- Manifest SHA-256: `5b2fd4f7cc3634aae1d51ed132d4247fba3e59677aa5f96dca2f0716452e9ba2`; included in `__archive_meta__/source-manifest.jsonl`.
- Every source file matched before/after by SHA-256, size, mode, inode and timestamps. Every tar member independently matched its manifest entry. Remote archive SHA-256, size and gzip integrity matched; local gzip integrity passed.

Original result remains `METADATA_AB_PASS_ONLY`, `accepted_for_full128=false`. Independent raw review is linked from [runtime review](../2026-10-14-lowfork-5cd-runtime-review/README.md). No current61b pin changed. No device call, source write, commit or push occurred during archiving. Completed 2026-10-14T01:22:15.278812+08:00.
