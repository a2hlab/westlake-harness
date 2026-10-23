# REA client approval recovery

The old client rejected `open_binary` before REA execution. Editing the user configuration alone did not update that running client. The first fresh client opened the exact HAP successfully, but `inspect_artifact` still required approval.

With explicit user authorization, only `open_binary`, `inspect_artifact`, and `close_binary` received `approval_mode = "approve"` overrides under `mcp_servers.rea.tools`. A second fresh Codex 0.163.0 client with `--strict-config` completed all three operations: open once, inventory summary, close. The summary reports 10 file entries and zero integrity contradictions. Full raw client receipts and private configuration backups remain in the persistent private directory referenced by results.json; no configuration secrets are published. MCP receipt derivatives replace the local home prefix with `$HOME`.

The sample is the retained own-host HAP SHA b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0. This proves analysis tool availability, not current device identity or a Toutiao white-screen fix. No device operation occurred.

Rule: validate tool policy changes through a fresh client and an actual open/inspect/close lifecycle. TOML parsing and `codex mcp get` alone do not prove effective per-tool approvals.

Official configuration reference: https://learn.chatgpt.com/docs/config-file/config-reference
