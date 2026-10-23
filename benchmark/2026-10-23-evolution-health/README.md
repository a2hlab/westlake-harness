# Evolution pipeline health, 2026-10-23

The backlog was in retro processing, not evidence that the permanent watchers had died. Existing watchers **25030 / 25031** were retained. Their actual output files contain successful collection of EVO-0162 and EVO-0163, with zero `harvest: failed` markers. No duplicate watcher was launched, no process killed, and no lock cleared.

A real portable harvest completed with **rc 0 in 75.55 s**, adding **0** cards and retaining `next_id=164` / 163 seen identities. The review cursor advanced from **7,312,456 to 7,330,393 bytes**; the intervening tail had no qualifying new R2/override line. A real retro completed with **rc 0 in 0.34 s**, advancing last ID **161 → 163** and producing run **31**, containing two candidate drafts. These drafts are not new accepted FLAW records.

The original brief is `$HOME/.octos/outer/evo/2667e1da45a74829/retro/2026-10-23T02:19:55Z-31.md`. Raw command receipts are in `$HOME/.local/share/westlake/evolution-health-20261023/101840`; `results.json` pins their bytes and SHA-256. The sanitized brief is included without changing its judgments.

The two candidate improvements reuse existing records: **FLAW-011** requires actual UI/component evidence rather than healthy-feed summaries or lockscreen-derived desktop claims; **FLAW-012's existing related follow-up rule** keeps delivery/idle observation active until acceptance and acknowledgement. The latter is not a new late-signature recurrence. No formal FLAW, DIGEST, RUNBOOK, or device state was changed.

## Reproduction

```sh
export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"
export OLP_EVO_REVIEW_BOARD="$MAIN/.octos/boards/app-lighting.md"
/bin/bash "$HOME/.octos/outer/evo/runtime-20261013-portable/olp-evo-harvest.sh" "$MAIN"
/bin/bash "$HOME/.octos/outer/evo/runtime-20261013-portable/olp-evo-retro.sh" "$MAIN"
```

Inspect existing collectors before running; do not start duplicates or clear locks. Manual environment is explicit, but the existing watcher process environment could not be read through `ps`; its wrapper and successful raw logs provide supporting evidence, not a claim that environment inspection succeeded. The optional MCP board is absent and was skipped. Full-source scanning remains slow. No artificial event was injected, and no Linux outer-duty lock is claimed on macOS: this work uses the user's #91 Mac outer authorization outside Herdr.
