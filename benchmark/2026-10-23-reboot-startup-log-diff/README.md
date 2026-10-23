# T113 — no evidenced new API repair candidate

A failed startup does not make its existing warnings causal. The two newly collected prefixes contain ordinary failures also present in T95's successful prefix. No new, demonstrated blocking public API/class/service initialization failure was found; no code candidate is proposed.

Both receipts bind boot `ecb84d86-f22f-4622-9501-143a26f39cf1`. `raw/05/p30.stdout:5` binds PID **7011**, PPID 5201, to `com.ss.android.article.news`; `p60.stdout:5` independently binds **9860**. The collection commands select their respective `adapter_child_<PID>.stderr`, with boot/date/stat before and stat after. Both commands returned rc=0 and empty transport stderr; inode, size and mtime remained unchanged across collection. No PID merging or exit attribution is made.

| Child | Remote file size | Captured payload | Payload lines | mtime (UTC; not launch time) |
|---|---:|---:|---:|---|
| 7011 | 368,251 B | 131,072 B | 1,589 | 2026-10-23 14:42:29 |
| 9860 | 314,796 B | 131,072 B | 1,511 | 2026-10-23 14:43:02 |

Failure line references below are **original `raw/06/log<PID>.stdout` lines**, including its five-line collection header; success references are `$HOME/.local/share/westlake/startup-stage-coverage-20261023/extended-01/head.stdout` (4 MiB, SHA `2ee3a988406296170b4ce6511b097a8d3836a21d456f21ca6a18b2bf53219cc6`). Exact input and command-receipt hashes are in `results.json`.

| Ordinary observation | 7011 | 9860 | Successful 6291 |
|---|---|---|---|
| AMS RuntimeException explicitly falls back to Proxy stub | 193; installed 199 | 193; installed 199 | 188; installed 194 |
| InputManagerGlobal.sService NoSuchFieldException | 209; next stage 211 | 209; next stage 211 | 204; next stage 206 |
| PluginPackageManager unknown authority | 449, 480, 536… | 503 | 748, 905 |
| libsysoptimizer missing `_ZNSt6__ndk18ios_baseD2Ev` | 1043, 1295 | 428, 448 | 507, 687 |
| libwasm missing `_ZNKSt6__ndk18ios_base6getlocEv` | not seen in this prefix | 1207 | 2080 |
| `AFTER scheduleTransaction OK` | 1193 | 759 | 1420 |

Typeface-symbol warnings, unsupported class-loader warnings, optional `.dm` metadata misses and resource-close warnings are also shared. Exact match patterns and all matching line numbers are recorded, not merely counts of “No such file”. No `NoClassDefFoundError`, `NoSuchMethodError`, `UnsatisfiedLinkError` or `ExceptionInInitializerError` was observed in either failure prefix. The visible AMS/field exceptions are followed by explicit installation/stage-progress records; those records do not certify every API behavior.

Coverage remains limited: both 128 KiB payloads end mid-record (7011: partial `[OHServ`; 9860: partial ordinary network record, private address omitted). Their uncollected suffixes remain unknown. `scheduleTransaction OK` is dispatch progress, not Activity completion or first frame. Different ordering/counts are not elapsed time or a demonstrated blocker. No source expansion is justified by these findings.

Reproduce offline: `python3 benchmark/2026-10-23-reboot-startup-log-diff/compare.py`. The additional normalized error screen found no unmatched allowed error lines; this is a bounded text check, not proof of equivalence. No device, REA, clock reanalysis, memory/fault/protection-mechanism analysis, or stopped-object inspection was performed. Original private logs are not copied into this report.
