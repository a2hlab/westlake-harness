# Demo desktop reconciliation on 61b

The signed demo list contained 13 excluded apps, three startup checks that had used ability fallbacks, and eight icons replaced by the same installer placeholder. All 13 explicitly excluded apps were removed. The 116 keep entries and protected Toutiao were retained. The three fallback cases were actually opened by their desktop icons and their startup screens were visually reviewed; this does not prove full functionality or long-term stability.

All eight confirmed wrong icons now display the original APK artwork: uNote, PostWriter, Tasks, LibreSudoku, Mood Cairns, PaperKnife+, Groce and Fossify Calendar. See the [eight-target visual review](desktop-final-icons/outer-icon-review.json), with screenshots for [uNote/PostWriter](desktop-final-icons/page--1-01.jpeg), [Groce/LibreSudoku/Mood Cairns](desktop-final-icons/page--1-03.jpeg), [PaperKnife+](desktop-final-icons/page--1-04.jpeg), [Calendar](desktop-final-icons/page--1-06.jpeg) and [Tasks](desktop-final-icons/page--1-08.jpeg).

## What was wrong

Updating only the sidecar PNG and BMS resource database did not change the screen. A first bounded SceneBoard refresh also retained the placeholder. Static analysis of the **actual device SceneBoard HAP** established the authoritative persistent cache: `Launcher.db.icon_info` is queried before the BMS fallback. The [source/bytecode evidence](cache-static-analysis/README.md) and exact keys explain the failure without repeated device experiments.

The repair rendered the original APK vector resources, changed eight sidecars and 129 BMS resource rows, then changed only `combine_pic` in 17 exact SceneBoard cache rows. Both database operations use full-before compare-and-swap checks and exact rollback SQL. A guarded SceneBoard-only refresh reloaded the new persistent entries; host PID 4583, Toutiao PID 6789 and both appspawn processes remained. HAP bytes and the runtime were not changed. The [repair tools](../2026-10-14-demo-desktop-icons/README.md), [actual execution](icon-cache-final/apply-results.json) and [refresh receipt](icon-cache-final/refresh/commands.json) are separate from visual acceptance.

## Scope and evidence

[Results](results.json) preserve the exact scope. The original V2 signoff is unchanged; this later installation set is a distinct reconciliation. Forty other installed packages were retained because they were outside the signed demo list and not independently classified for removal. Frequent Habits is an additional blank-icon suspect in that group, not one of the eight accepted repairs.

The [three actual desktop click reviews](manual-launch-3/outer-visual-review.json), [13 uninstall receipts](remove-13/results.json), and final selected screenshots are committed. Raw device databases, the original HAP and full disassembly are **not public Git files**; the [durable archive receipt](durable-evidence/receipt.json) records an independently verified remote SHA and archive location. The archive contains the original before images and SQL rollback evidence. Do not replace an entire database or delete launcher user data to repair an icon.
