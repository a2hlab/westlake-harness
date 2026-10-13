# Actual61b full128 window02 archive

A completed window is not a completed128-app round. This archive preserves only `window-02/` from the actual086d round, including original app records/screenshots/logs and identity phases. Its after-identity passed954 targets with empty diff and unchanged086d boot; original `board-run-result.json` reports `before_unlock=0` and `smoke=0`. Driver advance towindow03 was observed.

- Durable landing: `hw248:/home/alvin/westlake-final61b-full128-window-02-20261014T013746-2f3670d8/full128-window.tar.gz`
- SHA-256: `d1d69b40b6e8478ea508c4bc1202e3c87f6df890f983799cf7ada7d8082de372`
- Archive size: 16,751,721 bytes; 21,409 original files totaling 143,241,798 bytes.
- Manifest SHA-256: `699a2fd358797adbeecd852e964ac7fd3e2ff8de8a647503218e7962d21c1ca2`; inside `__archive_meta__/source-manifest.jsonl`.
- Recursive lsof found no open source writer; two complete metadata snapshots5s apart matched. Source SHA/size/mode/inode/timestamps matched before/after packaging, every tar member matched, and remote SHA/size/gzip integrity passed.
- The original board result hash and source/driver observations are retained in `source-readiness.json`; original receipts remain unchanged in the archive.

Later windows, final aggregate and signoff are excluded. No UI or full128 completion verdict is granted. Zero HDC/device calls, source writes, commits or pushes. Completed 2026-10-14T01:37:50.858963+08:00.
