# T106 — CC read-only collection (index only; comparison is Codex's)

**Plan and inputs.** The run followed `commands.disabled.json`, SHA-256 6a51db7e…, and `files.json`, SHA-256 9e1af571…; both are unchanged. The collector is `collect.py`. Its budget was 90 s per board and 240 s for the batch, with no retry. The batch actually used 16.8 s.

**Per-board steps.** Each board went through the same sequence:
1. `held` returned rc=1.
2. Fresh boot, uptime and ps.
3. For the child and for the host PID: stat, exe, cmdline (hex) and maps, then stat again.
4. For each allowlisted file mapped by those processes: stat, then sha256, then stat again, read through `/proc/<pid>/root<path>`.
5. 61b only: the plan's exact disk list.
6. A final identity read.

The boot ID and the PID start times were identical before and after on both boards.

## Results by board
| Board | Boot | Child (birth) | Host (birth) | Mapped files |
|---|---|---|---|---|
| 61b | 61aa5791 | 6291 (142694) | 4958 (10879) | 18 OK |
| 5cd | 62db0627 | 21639 (2117333) | 19801 (2115862) | 18 OK |

"OK" means the file was stable across the two stats and its maps dev/inode matched the stat dev/inode. Every mapped runtime path is `/data/local/tmp/asx/...` as seen inside each child's own process root.

## Unknown items
- **Host HAP.** Both host processes map `/data/storage/el1/bundle/entry.hap`. My first-pass suffix rule (`org.westlake.imehost/entry.hap`) missed it. My one supplementary read then failed because of my own error: zsh did not word-split the argument, the PID came out empty, and the command read the system-wide `/proc/stat` and a nonexistent path instead. No retry was made, so the **mapped HAP identity is UNKNOWN** on both boards. 61b has only the plan's physical disk row for `/data/app/el1/bundle/public/org.westlake.imehost/entry.hap`.
- **BCP jars.** None of the nine `fw/*.jar` files appears as a file mapping in either child. Their identity is UNKNOWN, and so is the active BCP order.
- **`libandroid.so` collision.** Two paths matched the `libandroid.so` role, because `webview-t-lib/libandroid.so` shares the basename. The index labels both rows.

## Files
- `index.json` holds every row and step rc.
- `raw/<board>/` holds the receipts. In `proc_*.stdout` the address-range map lines are stripped (`.no-maps-lines`); the full private originals are at `$HOME/.local/share/westlake/cross-board-startup-inputs-20261023/cc/`.

No device writes and no UI, power, network, permission or process changes were made. No stopped object was read.

Raw receipts are stored privately under `$HOME/.local/share/westlake/t106-outer-archive-20261023/`; the public outer-private-manifest.json indexes their SHA256 and sizes.
