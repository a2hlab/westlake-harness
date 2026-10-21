# G34 outer-confirmed stock tool presence

The original inner `hdc list targets` timeout remains valid and unchanged. A separate existing outer HDC entry succeeded at 2026-10-22 00:33:17 +08:00 and listed three serials. This does not establish recovery of the inner entry, explain its timeout, or lift/retry any ADB restriction. This addendum performs local evidence analysis only.

The outer targeted only 5ea for shell reads. Both 02 and 03 boot bookends equal G34 boot `a1d869b4-69a2-40a4-937e-4860f5b54239`. Exact argv, host rc, remote marker rc and raw hashes are indexed in command-ledger.json/raw-index.json.

| Tool | Actual result | Limit |
|---|---|---|
| `/bin/dumpcatcher` | 61448 bytes; SHA b38f3bc15f22ba9f39d467614e3ac6639b4adadebbcdc02144011430e832a431 | `-h` returned remote rc0 but printed `unrecognized option: h` followed by usage. Not standard help success. No PID or stack capture supplied. |
| `/bin/hidumper` | 49168 bytes; SHA 5785e0e893aa40c08f944a53249f9ab978728cf5801ee803e0847364be36a45c | `-h` printed usage. `-e --list com.miHoYo.Yuanshen -n 10` returned `no records found.` and rc0; only this query returned no records. |
| `debuggerd`, `process_dump` | `command -v` remote rc1, no path | Not resolved in that shell PATH; no filesystem-wide absence claim. |

The six current stock library SHA/size values independently match the six saved local ELF copies. Current stat dev/inode also agree with prior child maps metadata (Linux dev_t decoded). See stock-six-comparison.json. These are post-crash reads: equal boot/inodes and current saved bytes do **not** supply missing crash-time byte hashes, select a runtime provider winner, establish handler execution, or reproduce the stock source/build.

Tool version strings were not obtained. Presence and usage do not prove capture permissions or successful fault capture. No faulting PC/backtrace was obtained; no game launch, PID sampling, debugger attach or tool upload was performed by this analysis. Public stdout copies retain the exact help/query text and remote markers; original receipts remain private at HOME aliases.

## 00:37:48 global history index addendum

Outer executed `/bin/hidumper -e --list -n 100` on 5ea at 2026-10-22 00:37:48 +08:00. Host and remote marker rc are both 0; body is `no records found.` This removes the package filter but remains a bounded query of the current abnormal-exit service index. It does **not** establish that all crash-report files are absent. No report content or process sampling was requested. This additional receipt has no new boot bookends; earlier boot checks are not silently extended. Exact raw bytes are indexed and the response is preserved in global-history.stdout.txt.
