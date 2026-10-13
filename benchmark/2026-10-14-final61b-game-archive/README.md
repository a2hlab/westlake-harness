# Actual 61b original game evidence archive

A completed capture is not a gameplay acceptance verdict. This archive preserves both frozen original directories, `final61b-game-086d/` and `final61b-game-resume-086d/`, including all original stdout/stderr, command receipts, screenshots and steps. The first timeout remains unchanged. Subsequent outer review is outside this archive.

- Durable landing: `hw248:/home/alvin/westlake-final61b-game-20261014T004414-a7522f8f/final61b-game.tar.gz`
- SHA-256: `75824321715d1da77a345debac7169fd8f386861974078c030ed91ef664f457f`
- Archive bytes: 3,691,197; 7,921 source files totaling 9,957,223 bytes.
- Source-manifest SHA-256: `0fb8ba020e4ec147b9de3fc38be113e8b6a2c18cad6d1a266c5401d1a1b9eafb`; full per-file manifest is inside `__archive_meta__/source-manifest.jsonl`.
- Every source file was hashed before and after packaging; path, size, SHA-256, mode, inode and nanosecond timestamps matched. Every tar member was independently checked against its manifest entry. Nonregular files and symlinks were refused.
- Local gzip integrity, remote gzip integrity and independently computed remote SHA-256/size all passed. Operation receipts and return codes are retained beside `results.json`.

The initial runner exited rc2 with `FAILED_EVIDENCE_RETAINED` and `step experiment deadline reached`; the resume runner exited rc0 with `CAPTURED_PENDING_HUMAN`. Both original records retain `accepted=false`, the same boot `086db6c7-a7e7-40ce-a336-9608adc05afc`, and surface node `76166950027268`. These original states and their exact record/process hashes are retained in `completed-source-gates.json`. Neither archive completion nor resume rc0 grants GAME_PASS or a seal.

Only these two declared source directories were read. Zero device calls, runner interference, source mutations, commits or pushes. Started 2026-10-14T00:44:12.783404+08:00; finished 2026-10-14T00:44:15.783855+08:00.
