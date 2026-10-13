# Completed full128 tail-window archive

Windows 04–08 originally retained their raw evidence only on the local workstation. This archive preserves exactly those five completed windows, including original stdout/stderr, screenshots, process records, and before/after identity receipts. It does not include active finally/recovery output, any external directory, or any private Noice backup.

- Archived source: **97,820 regular files**, **617,066,909 bytes**; zero symlinks.
- Every window had `after_lock=0`, `before_unlock=0`, and an after-identity receipt with `passed=true`. All shard phases remained `completed_pending_review`; the archiver does not promote them to UI PASS. See `completed-window-gates.json`.
- A per-file SHA256/size/mode/time/inode inventory was collected before packaging and compared with a fresh complete inventory after packaging: exact match. Every archive member was independently streamed and compared to its source SHA256 and byte count.
- The full inventory is included inside the archive as `__archive_meta__/source-manifest.jsonl`; its SHA256 is `ba6e79627b6728c158c23876182ce423a04dd88db3a64aa31e337a65b8a30161`. The local inventory and large archive are under `.artifacts/`, outside the intended Git evidence set.
- Local `gzip -t` passed. Upload used a newly created unique directory and shell noclobber. Remote `gzip -t`, SHA256, and byte count all passed and matched the local artifact; original stdout/stderr are retained alongside this report.

Remote archive: `hw248:/home/alvin/westlake-boat-r6-full128-tail-20261013T220346-34a200de/windows04-08.tar.gz`

Archive SHA256: `5317f2dfce3ccbd28305ffa7d1aaed0a24f8dfd46b99f5906b64a6987bdba0b0`; compressed size: **68,672,654 bytes**.

This complements the previously verified windows 01–03 archive recorded in `../2026-10-09-demo-boatattack/v2-20261013/outer/r6-full128-execution/root-review/archive-windows01-03.json`. This report declares archive persistence complete, not full128 visual acceptance, final recovery success, or V2 sealing. No device calls, process changes, commits, or pushes occurred.
