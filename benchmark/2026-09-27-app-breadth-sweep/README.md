# 2026-09-27 app-breadth sweep automation (#48 horizontal) — board 5ea34a45 ONLY
Count how many apps the current Westlake runtime lights up (to first usable UI). Automation to stage+
launch each app, wait ~30s, screenshot + capture child stderr, classify LIT vs BLOCKED(category), clean
up, and tally. Board **5ea34a45 only** — hard-guarded; never 61b06572 (Toutiao) / 5cd1e3dd (device farm).

| Path | What |
|------|------|
| scripts/sweep_app.sh | stage+launch ONE app-key via probe_source_app.py (serial-pinned to 5ea34a45), wait, snapshot, capture child stderr, classify LIT/BLOCKED(category), cleanup. ABORTS unless SERIAL=5ea34a45…1123012c |
| scripts/sweep_batch.sh | loop sweep_app.sh over a keys file; accumulate results.tsv + LIT/BLOCKED counts + lit-rate + blocker-category histogram |
| scripts/sweep_config.5ea34a45.sh.template | the 5ea34a45 base-runtime candidate paths the sweep needs (HDC/SERIAL/PROBE/WORKSPACE/WESTLAKE_SOURCE/FRAMEWORK_REPORT/HOST_BUILD/WEBVIEW_INPUT/SOURCE_WEBVIEW_BUILD/APP_INPUT_ROOT/OUT_ROOT) — fill from the assembled 5ea34a45 runtime |
| scripts/keys.fdroid.txt | 66 open/F-Droid app keys (fd-* ≈ fdroid100 + wikipedia/newpipe/anki/… ) — sweep these FIRST (high hit rate) |
| scripts/keys.commercial.txt | 37 co-* commercial keys (heavy, anti-tamper — low hit; sweep last) |

Classify: LIT = process alive after WAIT + render markers in child stderr (ANativeWindow/onResume/
render/prewrapped/drawFrame) [+ screenshot saved for manual confirm]; BLOCKED = fatal crash (category:
mallocng-smash / telephony-NPE / flutter-impeller / native-symbol / crash) OR alive-no-render(stuck/
black) OR exited-no-crash-marker.

EXECUTION BOUNDARY: staging uses the board runner's probe_source_app.py with the assembled 5ea34a45
runtime-candidate inputs (framework/host/webview/shim builds). The board runner (claude-2/codex-2) owns
that assembled runtime + the board; run sweep_batch.sh after sourcing sweep_config.5ea34a45.sh (filled
with the 5ea34a45 candidate paths). claude-3 aggregates/classifies the results.tsv. Prioritize
keys.fdroid.txt, then keys.commercial.txt. Skip already-lit (wikipedia/toutiao/mcdonalds) + parked
deep-walls (localsend/X) or let them re-confirm.
