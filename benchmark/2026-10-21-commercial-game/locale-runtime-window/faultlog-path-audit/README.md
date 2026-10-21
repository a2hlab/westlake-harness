# G34 faultlog path audit — partial source binding

The earlier two-directory listing is **not sufficient to locate the two observed sceneboard syswarning records**. This is not evidence that a Genshin crash record exists, nor evidence that it does not exist.

The exact unfiltered log (`a5335168…`,32,974,064 bytes) supplies more than the generic “Save Faultlog” message:

- L73201 / L180451 explicitly remove temporary `syswarning-WINDOW_STATE_ERROR-…tmp` files under **`/data/log/faultlog/freeze/`**, a directory not covered by the supplied temp/faultlogger listings.
- L73203 / L180453 say `SaveFaultLogToFile: create log` and give two actual `syswarning-com.ohos.sceneboard-…log` basenames. L73205–73207 / L180455–180457 identify PID2391 and WINDOW_STATE_ERROR. These are not PID29761's native crash record. The messages do **not** show a final absolute destination or establish current file retention.

## Precisely bounded source evidence

The local public OH header snapshot at `$WORKSPACES/westlake-inputs/oh61-oh-root/oh_mirror/base/hiviewdfx/hiview/plugins/faultlogger/service/bdfr_base/` contains:

| Exact source location | Established fact |
|---|---|
| `constants.h:28–32` | Separate constants for faultlog base, temp, **`/data/log/warninglog/`**, faultlogger and hilog directories. |
| `fault_file/faultlog_manager.h:37–46` | Save/remove APIs, type-dependent `GetFaultLogFilePath`, and separate `InitWarningLogStore` / `warningLogStore_`. |
| `public_include/faultlog_info_inner.h:52–53` | SYS_WARNING=6 and APPFREEZE_WARNING=7 exist as distinct types. |
| `utils/faultlog_util.h:47` | Event-name-to-type mapping is an API; its implementation is absent from the located snapshot. |

Original headers (including copyright/license) are copied byte-for-byte into `sources/`; SHA256, exact source paths and numbered excerpts are in `source-index.json`. **No implementation body was found** in the bounded local filename searches for faultlogger_base/faultlog_manager/faultlog_util CPP. Therefore `/data/log/warninglog/` is a **source-supported candidate destination**, not a proven final destination for these two runtime events. No deployed Hiview/Faultlogger ELF-to-source reproduction was established.

The actual two `ls -la` receipts returned0, show no Oct21 entries, and are indexed without copying unrelated filenames or log contents. Their scope is exactly temp and faultlogger. Even if both contain only older entries, this does not exhaust the observed freeze input path or the source's separate warning store.

The smallest missing source is `FaultLogManager::GetFaultLogFilePath` / `SaveFaultLogToFile` / `InitWarningLogStore`, plus `FaultloggerBase::AddFaultLog` and event-type mapping. These would establish routing and message placement; deployment identity would still be required to turn source inference into exact installed behavior. No filename is fabricated. No device, VM, REA, service restart, configuration change or unrelated user-log read was performed.
