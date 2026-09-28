# app-breadth sweep — design + safety + how to run (#48 horizontal, 5ea34a45)
date: 2026-09-27

## What it measures
"How many of the ~110 pinned apps (app-inputs.lock.json) reach a first usable UI on the current Westlake
runtime." Automated, not manual. LIT = rendered to first usable frame; BLOCKED = crash or stuck (with a
blocker category so the histogram shows WHERE the runtime fails across apps).

## Mechanism (confirmed by RE of the board-runner infra)
- App staging is via `manifest/tools/probe_source_app.py --app <key> --serial <board>` — it is
  SERIAL-PINNED (`transport=[hdc,'-t',serial]`, and verifies the serial is attached), so sweep_app.sh
  pins 5ea34a45 and REFUSES any other serial. 110 apps are pinned in app-inputs.lock.json (keys:
  wikipedia/newpipe/anki/antennapod/aegis/markor/opencamera/termux/ooniprobe/mindustry/ppsspp + fd-* +
  co-* commercial + toutiao/mcdonalds/burgerking + vlc/firefox/subwaysurfers/localsend).
- probe_source_app.py needs the full assembled runtime-candidate input set (--workspace/--westlake-source/
  --framework-report/--host-build/--webview-input/--source-webview-build/--app-input), i.e. the board
  runner's staged 5ea34a45 base runtime (same set launch-webview10.sh uses). sweep_config.*.template
  captures these; the board runner fills them.

## Safety (paramount — 3 boards attached)
- sweep_app.sh ABORTS unless SERIAL == 5ea34a4500000000000000001123012c, and re-checks the board is in
  `hdc list targets` before running. Every board op goes through `h(){ hdc -t 5ea34a45… }`. A stray or
  mis-configured run can never touch 61b06572 (Toutiao delivery) or 5cd1e3dd (device farm).
- Idempotent: force-stops the host + clears prior child stderr before each app; force-stops after.

## Execution boundary (why the board runner executes)
The sweep is a sustained physical-board campaign (60+ stage/spawn/screencap/cleanup cycles) that
requires the board runner's assembled 5ea34a45 runtime-candidate environment. Per the standing division
of labor (board = claude-2/codex-2 domain; claude-3 = build/analyze), claude-3 delivers this automation;
the board runner runs it on 5ea34a45 (sourcing the filled config), and claude-3 aggregates the
results.tsv into the LIT/BLOCKED/lit-rate/category report. If the outer loop wants claude-3 to run it,
point claude-3 at the canonical 5ea34a45 launch config (the filled sweep_config) and I'll drive it
(hard-pinned).

## Run
1. `cp sweep_config.5ea34a45.sh.template sweep_config.5ea34a45.sh` and fill the paths from the assembled
   5ea34a45 runtime.
2. `source sweep_config.5ea34a45.sh && ./sweep_batch.sh keys.fdroid.txt`  (then keys.commercial.txt).
3. Read the printed tally + $OUT_ROOT/results.tsv → hand to claude-3 for the aggregated report.
