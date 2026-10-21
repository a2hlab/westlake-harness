# G34 standard native diagnostic readiness

A tool on disk is not proof of a usable Genshin crash capture. This local-only audit recovered exact LLDB tool identities and existing probe evidence, but no new game PC or stack. No debugger, device command, VM command or REA session was started.

| Path | Verified evidence | Capture condition / limit |
|---|---|---|
| Existing standard crash report | Prior faultlog-path-audit distinguishes faultlogger/temp/freeze and warninglog categories | Preserve the exact PID/time-bound native report if present; sceneboard WINDOW_STATE_ERROR is not the game crash. Absence from two directories does not prove absence globally. No live process required. |
| OH dumpcatcher | Local public `dfx_dump_catcher.h` exposes PID/TID native-stack API and timeout result distinction; exact lines and SHA in source-evidence.json | Need installed CLI identity/help and actual permission policy. Source error enum explicitly includes exited process, permission, ptrace and blocked-signal failures. No invented CLI or claim of passive sampling. |
| hidumper | Existing RUNBOOK uses `hidumper -s WindowManagerService -a '-a'` | This is WMS inspection, not a verified native crash stack command. Native-stack syntax/binary/version not established in this inventory. |
| debuggerd | No binary/help identified in the bounded local inputs | UNKNOWN, not globally absent; Android usage must not be presumed valid on OH. |
| DevEco LLDB15 + SDK server | Current hashes checked; R11 recorded no stop reply and zero target events | Do not recommend repeating the failed server based only on its presence. |
| Same host + NDK r23b server | R12 own root probe: two hardware hits, detach and continued count; outer cleanup closed | Proven only on 5cd Linux5.15.180 / Permissive / root-owned probe. Not game or 5ea crash interception validation. |

## Minimal next choice (not executed)

Prefer preserving an existing native crash report with matching PID/time and module identities. If it does not exist, first establish the stock OH dumpcatcher executable/help and permission requirements under a separately authorized diagnostic task. Its ordinary live sample may supply useful stacks, but is not automatically the fault-time PC. Do not relabel a kernel fallback as a native user stack.

LLDB is an evidenced fallback tool family, not a proven game capture route. Historical server syntax is `lldb-server gdbserver 127.0.0.1:5039 --attach <verified-live-PID>` (R13 source indexed below); the actual R12 engine selected `remote-ohos`, required hardware breakpoints and used `process detach --keep-stopped false`. These are historical usage references, **not an execution card or approval**. Attach pauses/traces the process and can change timing and signal handling. A future fault observation would need an independently reviewed bounded lifecycle and supported stop semantics; no game signal interception policy is changed here.

`input-index.json` pins historical source/receipts; `tool-inventory.json` records freshly hashed local bytes; `source-evidence.json` records public header path:line/SHA. SDK client version15.0.4 is from the prior real receipt, not a new invocation. NDK23b identity is tied to the recorded installation path and exact server bytes, not a newly queried server version. No tool installation on current 5ea is established. Large/private receipts remain at their HOME aliases.
