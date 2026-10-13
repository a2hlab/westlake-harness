# Approved 61b execution durable evidence archive

Local run completion alone does not preserve the original transaction and execution evidence. This archive retains the entire closed `final61b-approved-execution/` directory, including its earlier preflight, postinstall capture, stage transactions/backups, original stdout/stderr, and screenshots. The growing `final61b-game-086d/` and all outside directories were neither scanned nor included.

- Durable landing: `hw248:/home/alvin/westlake-final61b-execution-20261014T002714-2d70ae5e/final61b-execution.tar.gz`
- Archive SHA-256: `4df2e6c405413eb9054a02a9765585074bfd7592f209f4a459704fee2932e511`
- Archive size: 28,708,892 bytes; 12,351 original source files totaling 147,437,084 bytes.
- Manifest SHA-256: `725e9912d11248535a1796ad8c85a02cb176865e871f4777f3c46fb487f53cf5`. The full per-file manifest is preserved inside the archive as `__archive_meta__/source-manifest.jsonl`.
- Before/after path, SHA-256, size, mode, inode and nanosecond timestamps matched. Every tar member was read and checked against its manifest entry. Symlinks and nonregular files were refused.
- Local gzip integrity, independent remote gzip integrity, remote SHA-256 and remote size all passed. Small operation receipts and exit statuses are retained beside `results.json`; original source logs are kept in the durable archive, not published here.

`stage/completion.json` explicitly records `CANDIDATE_DEPLOYMENT_AND_CONTROLS_COMPLETE_NOT_SEALED`: boot `086db6c7-a7e7-40ce-a336-9608adc05afc`, postboot954/final954 and controls passed, and lock released. Its original facts line is `TOTAL keys=2 screenshots_captured=4/4 alive_t5=2 alive_t20=2`. The original completion and its hash are recorded in `completed-source-gates.json`.

The outer reviewer reports that the final host image shows a login/promotion page; the Toutiao feed remains unverified. Gameplay, full128 and sealing are not completed or granted by this archive. The archiver performed no UI review and changed no source verdict.

Zero device calls, source mutations, app-data writes, commits or pushes. Started 2026-10-14T00:27:09.848998+08:00; completed 2026-10-14T00:27:21.703757+08:00.
