# T114 — ordinary host callbacks were recorded

The T112 no-new-child outcome does not establish that the desktop click failed to reach the host lifecycle. **Positive host foreground and stage-event records exist near the click.** No implementation defect or candidate is established.

T112's single click command spans **22:48:54.228655–22:48:54.571848 +08:00**, rc=0, from `after-reboot-icon-recovery-20261023/raw/03/click.start` and `.end`. T114 collection independently confirms boot `ecb84d86-f22f-4622-9501-143a26f39cf1`, host PID **5074**, birth **9930** before/after (`raw/ident_pre.stdout:339`, `ident_post.stdout:339`, `birth_pre.stdout:1`, `birth_post.stdout:1`).

The ordinary PID-filtered hilog returned rc=0, empty transport stderr and no detected CODE/argument error. Its 987 lines retain epoch range **1792766516.501–1792767088.827**, spanning the click. Independently parsed `WL_IME_HOST` records include:

| `raw/hilog.stdout` line | Local time (+08:00) | PID/TID | Recorded event |
|---|---|---|---|
| 901 | 22:48:56.912 | 5074/5074 | `foreground` |
| 904 | 22:48:56.916 | 5074/5074 | `stage-event`, numeric event 1, window 29 |
| 917 | 22:48:56.920 | 5074/5074 | `stage-event`, numeric event 2, window 29 |

The embedded `Date.now()` values agree with these hilog timestamps. Numeric stage values are preserved without assigning unverified names. Host-command/device clock offset was not measured, so no exact click latency is claimed. Retained first/last timestamps do not prove lossless logging; the positive callback records themselves establish occurrence. T112's unchanged RETRY_LIMIT/no-new-child observations remain separate accepted facts; this task does not explain the downstream behavior.

The T89-bound EntryAbility source SHA is `9dc302d9aa72eb1be8635d7bc4bc4306da76f0e45d2414d67bd96d024e2a24c6`. It emits hilog **before** file writing (line 9), registers stage events (21–23), and records `foreground` (31). `record()` writes `window-state.json` with `TRUNC` (11–13): it is a last-event file, not history. Absence of an `onNewWant` override is not by itself a defect.

**File read failed despite transport rc=0:** `raw/window_state.stdout:1`, `:3`, `:6` explicitly report `No such file or directory` for the prescribed path. File mtime/content/event remain **unknown**. The path's absence does not prove a callback was absent or identify a file-writing defect; no alternative device path was tried.

Raw root: `$HOME/.local/share/westlake/host-lifecycle-after-retry-limit-20261023/`. `raw-pins.json` pins original receipts; `callback-events.json` contains only allowed callback fields. Reproduce with `source_audit.py` followed by `analyze.py` in this directory. Final alignment is in `results.json`; `source-results.json` is the preceding source-facts record. No device/REA/deployment, stopped-source, fault or protection-mechanism analysis occurred.
