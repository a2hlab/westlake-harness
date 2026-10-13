# Approved 61b preinstall and preflight evidence archive

Local evidence alone does not establish durable retention. This archive preserves exactly the two closed source directories declared by the outer coordinator on 2026-10-14: `final61b-approved-preinstall-capture/` and `final61b-approved-execution/preflight/`, relative to `benchmark/2026-10-09-demo-boatattack/v2-20261013/outer`. The growing stage, postinstall results, external directories, and private app-data backups are excluded.

- Durable landing: `hw248:/home/alvin/westlake-final61b-preinstall-20261014T001243-277b0b8d/final61b-preinstall.tar.gz`
- Archive SHA-256: `96593d64cda0b321bb13b6bddaa0877afbdd6e266f55117b0796d8b96e6aa7ce`
- Archive size: 1,003,892 bytes; 911 original files totaling 15,746,469 bytes.
- Source manifest SHA-256: `040151783c2ce0d5ce330848edfbd56ae817054c5cb00ecb006bb327dab8656d`; included in the archive as `__archive_meta__/source-manifest.jsonl`.
- Before/after per-file SHA-256, size, mode, inode and nanosecond timestamps matched. Every archive member was independently read and checked against this manifest. Nonregular files and symlinks were refused.
- Local gzip integrity and independent remote gzip integrity, SHA-256 and size all passed. Original operation stdout/stderr and return codes are retained beside `results.json`.

Preserve the distinction between finished collection and a passing collected state: preinstall `capture.json` reports `complete=false`, `boat_registered=false`, and `boat_uid=null`. Those are original preinstall observations, not rewritten success fields. The separate `preflight/original940.json` reports real live-readonly PASS for 940 files, and its distinct process receipt returned rc0. Their hashes and selected original fields appear in `completed-source-gates.json`.

Archive completion is not a UI verdict, device-installation verdict, or V2 seal approval. No device call, source mutation, app-data write, commit, or push occurred. Started 2026-10-14T00:12:43.649909+08:00; finished 2026-10-14T00:12:44.953755+08:00.
