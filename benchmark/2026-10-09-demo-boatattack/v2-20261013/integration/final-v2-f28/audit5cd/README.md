# Exact post-return audit archive

The old preboot generator used the origin boot in its success receipt. This successor binds checks and both success receipts to the actual returned boot `362f2212-1a42-4c1a-8487-0dddb091c74b`. It accepts the original successful rollback plus the outer 20:16 fresh readonly inventory: exactly five files and two directories (inodes 156273/156291). No previous capture is rewritten.

`prepared-reviewed` is prepared, not executed. It uses the already successful POSIX process/mount checks, no awk. Its sole device mutation is one same-parent rename after checking the lock, boot, CFG, exact inventory, metadata, directory inode, file hashes, absence of consumers and owned mounts. Files retain their inode across rename. Unknown entries fail closed. No deletion or reboot occurs.

From this directory, offline preview:

```sh
bash prepared-reviewed/archive.sh
```

Outer only, inside an authorized held window, after verifying freeze pins:

```sh
export WORKSPACES=/path/to/workspaces
HOLDER='outer(codex)' bash prepared-reviewed/archive.sh --execute
```

HOLDER is the owner token; the wrapper also preserves and compares the complete held line. It does not acquire or release the board lock. Keep all execution stdout/stderr and transport/remote receipts. An interruption after rename requires inspection of the unique destination in mapping.json; do not rerun blindly.

The fresh audit input is `main outer/final-v2-5cd-owned-audit-readonly/{receipt.json,stdout.txt,stderr.txt}` (pinned in mapping.json). No repeat collection is needed before this archive: the remote rechecks the exact state immediately before rename. Afterwards use the existing readonly collector in a new output directory to obtain a complete current capture; the previous incomplete capture must remain unchanged. The provider must consume the new capture, never a manually flipped complete flag.

```sh
python3 ../capture5cd/capture_readonly.py --expected-boot 362f2212-1a42-4c1a-8487-0dddb091c74b --out "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final-v2-5cd-postarchive-readonly" --execute
```

Only the outer executes the collector. Complete merged-state recovery uses `restore-directory-complete`, preserving the original 487 transaction receipts and empty-directory metadata. `verify-existing` proves preservation only. Separate authorized windows may be at most 45 minutes; this archive adds zero reboots.

Offline validation: five tests, actual source generation, host/remote bash syntax and default-preview passed; zero device calls. Negative cases reject foreign inode, changed boot, remote failure and extra member before output creation. This is not a deployment or recovery-success receipt.
