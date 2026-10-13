# Actual61b full128 window01 archive

A completed window is not a completed128-app round. This archive preserves only `window-01/` from the actual086d round, including its original app records/screenshots/logs and all three identity phases. The last after-identity passed954 targets with empty diff and unchanged086d boot. The driver had advanced towindow02.

- Durable landing: `hw248:/home/alvin/westlake-final61b-full128-window-01-20261014T012742-d0b4961e/full128-window.tar.gz`
- SHA-256: `e64d718c58de706d5a537fae6039925e70c5d6f002cc7e6812312c7e58d8c3e2`
- Archive size: 21,993,621 bytes; 24,001 original files totaling 208,751,102 bytes.
- Manifest SHA-256: `df92e5801b4c8df5214e59182865b8c630c9b8c2fc1de75063e2ce696699339d`; inside `__archive_meta__/source-manifest.jsonl`.
- Recursive lsof found no open source writer. Two complete source metadata snapshots5s apart matched; last source write was about13min before that check. Source SHA/size/mode/inode/timestamps then matched before/after packaging, every tar member matched, and remote SHA/size/gzip integrity passed.
- Original driver `collect` reads old window records and creates only aggregate-level final symlinks/facts; it does not rewrite completed window files. Source pin is in `source-readiness.json`.

Later windows, aggregate evidence and final signoff are excluded. No UI verdict or full128 completion is granted by this archive. Zero HDC/device calls, source writes, commits or pushes. Finished 2026-10-14T01:27:47.665798+08:00.
