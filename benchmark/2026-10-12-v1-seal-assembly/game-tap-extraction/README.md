# Ten signed games: existing interaction evidence extraction

A desktop icon click is not an in-game action. The existing `clicked=true` fields and the t5/t20 images must not be presented as an in-game control map or an action before/after pair.

The final runbook selects 10 games, all signed `lit` in `window1`. This extraction independently rehashed the 10 original records and 20 original screenshots: **30/30 SHA-256 and byte-size matches** against `t3/window1-evidence.json`, zero mismatches. Every record has `launch_method=desktop`, `clicked=true`, and `first_tap=null`. There are **0 verified in-game control maps** in the scoped historical metadata search. Control id, text, coordinates, action, and game before/after images remain `unknown` for all 10 games.

The 20-key subset contains LibreSudoku, Privacy Friendly 2048, and Privacy Friendly Minesweeper. It does not narrow the user-confirmed 10-game interaction scope. `input-refs.json` pins the existing order, screenshot signoff, capture index and subset inputs; `games.json` contains exact per-file hashes; `checklist.tsv` is the operator handoff. The source image binaries are referenced, not copied.

The bounded search covered the same `2026-10-09-demo-baseline` topic in main, t3, bms, wiki, and tools-inventory workspaces. The local t4 topic is absent. The grouping/stability code is a validator, not an executed interaction result. First-tap proposals and synthetic tests are excluded. Searching has stopped; absence here means not found in this scoped search, not a claim about every historical artifact.

## Outer execution handoff

外环在 61b 独占窗口完成 20-key 后，按本表 10 个游戏逐个读取真实控件；记录 key/package、控件 id 或可见 text、实际布局/截图支持的坐标、点击前图、动作记录和点击后图。`unknown` 不得猜坐标；没有可确认控件就保留 unknown。交互失败标不稳定，不现场修、不扩大 app 集。只有实测图像及动作证据补齐后才能签认游戏交互。

This is a documentation-only extraction: no device, remote access, new image, or runtime change. Existing composed-runbook and restore freezes are untouched. `freeze.json` hashes this small text delivery; it excludes itself to avoid a circular hash.
