# T116 — current startup-control fingerprint, 61b and 5cd (read-only, hash-only)

**Procedure.** Each board was checked in this order:
1. `held` returned rc 1.
2. Fresh boot ID (the same before and after), uptime and ps.
3. The init cfg `/system/etc/init/01_westlake_u13_toutiao.cfg`: stat, SHA-256 and content.
4. The service argv was used to find the ROOT, taken from the `.../boot-entry.sh` argument.
5. In ROOT and in the current-boot subdirectory, the config metadata (`startup.env`, `startup.expected.sha256`, `members.tsv`): stat, SHA-256 and content.
6. Every implementation member listed in `members.tsv`, plus `entry.sh`, `config-common.sh`, `boot-entry.sh` and `watchdog.sh`, in both places: **stat and sha256sum only, no content read**.

The batch took 5.4 s. Python argv lists were used throughout; there were no device writes.

**First attempt.** The first run stopped on the host before any ROOT read: the parser took argv[0] (`/system/bin/sh`) instead of argv[1]. It was fixed and rerun as `raw2/`. The first run's receipts are kept.

## Results
| Board | Boot | init cfg SHA-256 | ROOT |
|---|---|---|---|
| 61b | 61aa5791 | 7b9f2c0e… | `icon-manual-20261021-r3` |
| 5cd | ecb84d86 | 19d0201b… | `restore-v1-5cd-20261012` |

All per-file SHA-256, size, mtime and mode values are in `index.json`.

**Not in the boot subdirectory.** On both boards the three config files and `boot-entry.sh` exist only in ROOT; the boot subdirectory has no copy of them.

**Retry and manual-reentry parameters.** These are **unknown**. They are not present in `startup.env`, and the implementation files were hash-only. The `startup.env` `*_SHA`, serial, enabled and tap-wait-policy fields are published; `APPROVED_BY` is redacted.

Equal file SHA does not prove the same runtime mode; the comparison against T115 is Codex's.

The private originals are at `$HOME/.local/share/westlake/current-control-fingerprint-20261023/` (`raw/`, `raw2/`).
