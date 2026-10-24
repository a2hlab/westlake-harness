# T133: local native recovery artifact preflight (read-only)

Both local artifacts exist and match the expected SHA-256 values. Only ordinary local file reads were made (`stat`, `shasum -a 256`). There was no device access, UI action, deployment, reboot or permission change; no old plan was run; and no stopped controller, executor or configuration was read.

| Role | Path | Bytes | SHA-256 | Expected |
|---|---|---|---|---|
| candidate | `$HOME/.local/share/westlake/native-host-recovery-build-20261024/snapshot-02/link-01/liboh_adapter_bridge.so` | 2,154,616 | `3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819` | match |
| rollback | `$HOME/.local/share/westlake/native-host-recovery-device-preflight-20261024/rollback-copy-01/liboh_adapter_bridge.b0e.so` | 2,023,136 | `b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4` | match |

The exact argv, start/end times, rc, stdout and stderr of all four commands are in [results.json](results.json). This proves local byte identity only. It says nothing about device state.
