# T128-A: existing child window-record access preflight

**No definite inaccessibility condition was found in the observed path/mode/identity evidence. Child-credential read remains unverified.** This was a narrow read-only observation, not t3 execution or a stopped deployment retry. Root proxy readability does not prove that the child opened, read or consumed the record.

The existing61b target was listed and sampled between **2026-10-24T16:45:30.110807+00:00 and 2026-10-24T16:47:36.449413+00:00** (UTC; actual precise command bounds are in results). Boot remained `61aa5791-fd69-4bbb-a7b5-333b5d913c81`; host `10486/birth7039472`, parent `5129/birth11126`, and child `22035/birth6535369` matched before/after. The child was identified as `com.ss.android.article.news`, not selected from historical PID alone.

- Child Uid and Gid real/effective/saved/filesystem values are all **20011206**; supplementary Groups are **1097,3003,3004,3099**; CapEff is0.
- Child mount namespace is `mnt:[4026533005]`, root observer namespace `mnt:[4026531841]`. Root observer is uid0/gid0 with context `u:r:su:s0`; child context is `u:r:normal_hap:s0`; the separately read enforce value is **0**. No policy/credential/namespace change or policy analysis occurred.
- All11 pathname components have matching stat tuples in root direct and `/proc/22035/root` views. Based only on the observed mode bits and filesystem credentials, each ancestor supplies search and the final regular file supplies read. This is a mode-bit calculation, not a successful child access test.

| Absolute component | dev/inode (both views) | owner | mode | Mode-bit observation |
|---|---|---|---|---|
| `/` | 66336/2 | 0:0 | 0755 | other search present |
| `/data` | 66352/3 | 1000:1000 | 0771 | other search present |
| `/data/app` | 66352/42 | 1000:1000 | 0771 | other search present |
| `/data/app/el2` | 66352/48 | 0:0 | 0711 | other search present |
| `/data/app/el2/100` | 66352/1082 | 0:0 | 0711 | other search present |
| `/data/app/el2/100/base` | 66352/1083 | 0:0 | 0711 | other search present |
| `/data/app/el2/100/base/org.westlake.imehost` | 66352/431392 | 20011206:20011206 | 0700 | owner search present |
| `/data/app/el2/100/base/org.westlake.imehost/haps` | 66352/431426 | 20011206:20011206 | 0700 | owner search present |
| `/data/app/el2/100/base/org.westlake.imehost/haps/entry` | 66352/438975 | 20011206:20011206 | 0755 | owner search present |
| `/data/app/el2/100/base/org.westlake.imehost/haps/entry/files` | 66352/438976 | 20011206:20011206 | 0770 | owner search present |
| `/data/app/el2/100/base/org.westlake.imehost/haps/entry/files/window-state.json` | 66352/438987 | 20011206:20011206 | 0660 | owner read present |

The final file is **518 bytes**, dev66352/inode438987, owner20011206:20011206, mode0660; both views retain that tuple in the closing sample. A single `head -c8192` root-proxy read returned518 bytes, valid JSON, SHA256 **4031fa9fa5fd5bd3e135e168228f9ccefb3381596811ad5837ec02380b67650b**. Public metadata is limited to event `stage-event`; the body stays private. Matching before/after stat does not establish byte immutability across the window.

OC/GLM offline input is the existing file `.private/07-record-bytes/stdout` under this directory. [results.json](results.json) provides its exact alias/size/SHA and per-component source line numbers. Do not copy the body into public reports. This lane did not invoke the reader with child credentials or run the offline reader.

Nine actual HDC commands were recorded: one list and eight serial-scoped read-only shell invocations, each with a15-second subprocess timeout. All returned local rc0 without timeout. The combined02 context tail lacks reliable separators/status markers and remains unchanged; dedicated04/05/06 observations supply the context/enforce facts. Local HDC rc0 is not an independently framed remote rc and is not alone treated as proof of read success.

All36 original argv/start/end/rc/stdout/stderr files remain under `.private/`, hashed in [raw-index.json](raw-index.json). Only sanitized metadata/hash references are public. No launch, reboot, UI, signal, deployment, permission change, namespace switch, HDC restart or further scan occurred. No environ/controller/executor/config or application user data was read. Exact public delivery is [landing-paths.txt](landing-paths.txt).

## Offline replay of the captured bytes (local copy only)

A single local compilation linked the accepted production `host_window_record_reader.cpp` (`29eb5ba7…`), header (`2427a498…`) and vendored JSON (`9bea4c80…`) unchanged with [driver.cpp](driver.cpp). Compilation and execution both returned rc0. The actual518-byte captured input was not copied over, edited or chmodded. Source/input SHA and dev/inode/uid/gid/mode/size/mtime/ctime comparisons remained unchanged; no atime assertion is made.

Production output: **status=Candidate, id=62, source_event=StageEvent, stage=4**. The minimal driver mirrors the accepted `Foreground` pure expression (window-ready or stage1/2); its result is **false** for this HIDDEN4 record. It does not execute recovery or IPC. Parser Candidate does not imply foreground admission.

`ReadWindowRecord(path,getuid(),getgid())` used the Mac copy's actual **501:20**, not the OH child's20011206. This confirms only production-parser treatment of the captured bytes/local file. It does not prove OH child access, current foreground state, candidate loading, repair or feed. No new device command was issued.

[offline-replay.json](offline-replay.json) pins source/input/compiler/binary and records the exact result. Original compile/execute argv were persisted before execution, with start/end/rc/stdout/stderr under `.private/offline-replay-01/`; [raw-index.json](raw-index.json) now includes these additional local records alongside the unchanged36 HDC originals.
