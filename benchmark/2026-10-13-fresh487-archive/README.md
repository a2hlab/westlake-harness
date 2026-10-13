# Completed full487 restoration archive

The completed restoration contained original execution evidence and 487 backups only on the local workstation. This archive makes that exact completed run durable without rewriting its evidence or including the subsequently active Boat candidate stage.

The source window is closed safely with `apply_rc=0`, `restored487=true`, and zero reboots. Its final recipe receipt independently reports `complete=true` and `executor_rc=0`.

Scope: the entire completed `benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/routeb-fresh-restore-main` directory, including the disabled plan, recipe, authorization, admission, independent review, launch/preview records, every transaction raw stdout/stderr file, all 487 backups, placement/atomic receipts, and the final recipe/window receipts. The running `routeb-fresh-boat-stage` directory is excluded. No source evidence was changed.

Validation completed locally:

- 15,665 files, 778,444,612 uncompressed bytes, 487 backup files, no symbolic links.
- Every archived regular file matched a pre-archive SHA256/size manifest; a second full source manifest matched the first after packaging.
- `gzip -t` passed. The local archive is under `.artifacts/`, outside the intended Git evidence set.
- Compressed bytes: 458,382,385. SHA256: `fccbc5ff2f30658849a9921586e23a64e250cf45a0d43d67f57dd201980cf093`.

**Remote persistence is complete and verified.** The remote SHA256 and byte count exactly match the local archive, and remote `gzip -t` passed (all three commands rc=0). `results.json` records `status=complete`; `archive.json` records `verified_remote=true`. The new remote directory is created exclusively with `mkdir`; upload uses shell noclobber, and does not overwrite an existing archive. Transfer/verification raw stdout and stderr are preserved beside this report.

No device calls, active stage changes, commits, or pushes were performed. The remote archive path and verification receipt are recorded in `archive.json`.
