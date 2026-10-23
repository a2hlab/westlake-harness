# T106B — host HAP mapped identity, corrected read

**Corrected window.** This was a separate window: 20:37:06–20:37:07, 0.7 s of a 60 s budget. It did not overwrite the first batch, and nothing in `../` was rewritten.
- `hap_corrected.py` passes every argument as a Python argv list; no shell word-splitting is used.
- Each serial had to be on the full-value whitelist.
- The host PID had to be unique and numeric in a fresh `ps`.
- The HAP was read as `/proc/<pid>/root/data/storage/el1/bundle/entry.hap`, with the process stat read before and after.

## Results
| Board | Boot | Host PID (birth before = after) | maps dev/inode = stat dev/inode | stat stable | size | SHA-256 |
|---|---|---|---|---|---|---|
| 61b | 61aa5791 | 4958 (10879) | 66352/545751 | yes | 54215 | b18978b8… |
| 5cd | 62db0627 | 19801 (2115862) | 66352/211807 | yes | 54215 | b18978b8… |

Both boards: `result OK`. The full SHA-256, mtime, owner and mode are in `hap_corrected.json`. The first-batch `hap_supp` failure, an executor argument error, is preserved unchanged in `../raw/*/hap_supp.*`.

No device writes were made.

Raw receipts are stored privately under `$HOME/.local/share/westlake/t106-outer-archive-20261023/`; the public outer-private-manifest.json indexes their SHA256 and sizes.
