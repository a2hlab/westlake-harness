# Evolution collector health, 2026-10-13

The previous check inferred collector health from two live watcher processes. That was insufficient: both watchers discard stdout and stderr to `/dev/null`, while the locally available Bash 3.2 cannot parse the harvester's Unicode escape. GNU `stat` is also required. This investigation made **zero device calls**, changed no global scripts, stopped no watchers, and did not write the real evolution ledger or collector state.

Evidence:

- `/bin/bash` is 3.2.57; no modern Bash was found in PATH, Homebrew Cellar, `/usr/local`, `/opt/local`, or the user's local bin tree. `/opt/homebrew/bin/bash` does not exist. No installation was attempted.
- BSD `stat -c` exits 1; the installed GNU coreutils `stat -c` exits 0 (`bsd-stat.*`, `gnu-stat.*`).
- The original header parser ignores `EVO-0139` on Bash 3.2 and proposes **EVO-0001** with empty state. Replacing one expression with `${local_id%%[!0-9]*}` proposes **EVO-0140** (`original-fixture.*`, `portable-fixture.*`). The same numeric-prefix rule also tolerates ASCII/fullwidth delimiters without relying on Unicode escapes.
- A second isolated replay copied all **139 real cards and the current state**. Its first actual harvest appended exactly EVO-0140, preserved the original ledger byte-for-byte as a prefix, and advanced next_id to 141. The second harvest appended **0 cards** and left the ledger size and next_id unchanged (`replay139-*`, `results.json`). These writes were confined to a deleted temporary directory.
- The portable collector's **real-board dry-run** completed with rc=0 and **0 pending cards**. Real state SHA remained `15d2da269379ea8bc7c40646a19288a46cad2cc40620f88c3bb40a043a2349ba`; ledger SHA remained `52752afde485df973f0af33749f0806628e1385e79d0881979f0c0755335eed8`. Therefore it did not duplicate the existing 139 cards or rewind the live cursor. The test disabled the unrelated MCP audit input via `/dev/null`.
- Real retro dry-run completed rc=0 and reports **48 old cards / 48 candidates** since its previous checkpoint. These are a review backlog, not new October 13 cards and not 48 approved FLAW records.
- PIDs 55426 and 55427 were live and both output descriptors pointed to `/dev/null`. macOS `ps eww` exposed **no environment fields**, so their inherited PATH and OLP variables are **unknown**. An initial message incorrectly interpreted that absence as unset variables; it was explicitly corrected before this report. The script's default review board is `OUTER_LOOP_REVIEW.md`, so new launch commands must explicitly bind `app-lighting.md`.

## Reviewable repair

`prepare-runtime.sh` creates a **new isolated runtime directory**, checks the original harvester SHA, copies five required scripts, and applies only the numeric-prefix fix. It generates `watch.sh` with explicit GNU coreutils PATH and the correct review board. It neither starts/stops a watcher nor runs a harvest. A repo-local harvester that would shadow this copy causes the launcher to refuse.

Outer may execute the following preparation from the repository root:

```bash
EVO_RUNTIME="$HOME/.octos/outer/evo-macos-20261013"
bash benchmark/2026-10-13-evolution-health/prepare-runtime.sh \
  "$HOME/workspace/octoscode/scripts" "$EVO_RUNTIME"
export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"
export OLP_EVO_REVIEW_BOARD="$PWD/.octos/boards/app-lighting.md"
bash "$EVO_RUNTIME/olp-evo-harvest.sh" "$PWD" --dry-run
```

Then independently recheck that 55426/55427 are the exact old evolution watchers, terminate those two watchers only, and launch both replacements with persistent logs:

```bash
nohup /bin/bash "$EVO_RUNTIME/watch.sh" "$PWD" '改判' \
  > "$EVO_RUNTIME/watch-override.log" 2>&1 </dev/null &
printf '%s\n' "$!" > "$EVO_RUNTIME/watch-override.pid"
nohup /bin/bash "$EVO_RUNTIME/watch.sh" "$PWD" 'R2 记档' \
  > "$EVO_RUNTIME/watch-r2.log" 2>&1 </dev/null &
printf '%s\n' "$!" > "$EVO_RUNTIME/watch-r2.pid"
# Catch up the switch interval; identities deduplicate under the existing lock.
bash "$EVO_RUNTIME/olp-evo-harvest.sh" "$PWD" \
  > "$EVO_RUNTIME/catchup.log" 2>&1
bash "$EVO_RUNTIME/olp-evo-retro.sh" "$PWD" --dry-run \
  > "$EVO_RUNTIME/retro-preview.txt" 2>&1
```

Do not reset state, next_id, or seen identities. Keep the existing state root. Check the next genuinely signed R2/override produces a new, unique card and a successful watcher log before claiming live recovery. These two tokens are evolution triggers; they do not replace the separate positive ACK and negative goal-transition observers.

## Scope and status

**Live recovery has not been performed by this task.** Only the isolated repair, replay, and read-only real-state preview are complete. Root owns watcher replacement, the first real catch-up, at most three reviewed FLAW records, and DIGEST/RUNBOOK changes. No commit or push was made.

Sources: the installed OctoLoop skill, `.octos/OPS-RUNBOOK.md` macOS collector note, and local Octoscode `scripts/olp-{watch-board,evo-harvest,evo-retro,evo-lib,board-append}`. Exact harvester source SHA and portable SHA are in `results.json`. `probe.py` reproduces the initial probes; the supplementary 139-card replay is recorded in the small raw logs and structured result.

## Outer integration receipt

Root subsequently installed the isolated runtime, replaced only the two identified evolution watchers, and observed two genuine signed records become EVO-0140 and EVO-0141. See `live-switch.json` and `live-r2.stderr.txt`; this is separate from the read-only investigation above. FLAW-009 and FLAW-010 are the two selected records for this review. No global collector code or board runtime was modified.
