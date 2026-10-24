# T122 ordinary log suffix identity

The inner `hdc list targets` attempt timed out after 10.007 seconds with rc 124 and empty stdout/stderr. It does not establish device absence or a safety refusal. The outer lane subsequently reported successful listing through the same HDC entry. No retry was made here, no device shell command ran, and no suffix was collected. Both historical-file bindings remain **unknown**. Outer supplementary evidence is pending.

The local lock check returned 1 with empty output and no holder file. Historical T109 records supplied the two 131072-byte prefixes and file identity fields; reading those saved records is not fresh device evidence. A local parser initially expected nine STAT tokens rather than eight; its failed source and a tool-error summary are retained. No device command preceded that parser failure.

`check_identity.py` is offline only. It requires integer device/inode/size/mtime/ctime fields, identical before/after identities, exact full size up to 512 KiB, and an exact 131072-byte prefix. Atime is excluded because reading may update it. Current boot must never be presented as historical file birth boot. Schema/test success is neither diagnosis nor repair.

Validation: one Rust selector passed and invoked six actual Python cases: valid binding, changed prefix, absent identity fields, post-read inode change, truncated capture, oversize capture. This is offline validation only; the human-review collection scenarios remain incomplete.

```sh
python3 benchmark/2026-10-24-ordinary-log-suffix/check_identity.py benchmark/2026-10-24-ordinary-log-suffix/.private/collection-01
cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test ordinary_log_suffix ordinary_log_suffix_identity -- --exact
```

Private receipts are under `$CARD/.private/collection-01/`; test argv/start/stdout/stderr/rc are in `$CARD/.private/tests-01/`. `$CARD` means this card in the inner worktree. `raw-index.json` lists actual file hashes without log text or personal paths. Raw content is excluded from landing. Original T109 evidence remains at `$HOME/.local/share/westlake/spare-board-reboot-repeat-20261023/raw/06/` and was not modified.

`results.json` preserves the initial unknown result; later evidence must be a separate addendum. `author_commit=null`: known shared-Git write restrictions were not retried. Outer landing is required. No push, UI, restart, runtime modification, or stopped-object access was performed for this task.
