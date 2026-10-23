# T97 authorized CLI attempt — stopped

REA CLI execution is not completed target analysis. The installed public `rea` 6.7.0 ran once with `search <absolute main-tree target> TOUCH21 --kind strings --provider ghidra --snapshot <persistent workspace path> --format json`. Target SHA-256 matched `8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1`, size 2,206,152 bytes.

The process exited **rc=1** after approximately 4.07 seconds. REA returned `execution_failure`, `retryable:false`, at Ghidra `ownership_preparation`. The compiler could not create its SwiftShims module-cache output (`Operation not permitted`); the same diagnostic also reports Swift SDK 6.3.2 versus compiler 6.3.3 incompatibility. These are preserved observations, not an inferred target defect.

Full JSON error output is in `01-search.stdout` (61,621 bytes); process stderr is empty because the compiler diagnostics are embedded in that JSON. `01-search.receipt.json` records exact argv, PID, UTC start/end and rc. `failure-excerpt.txt` preserves the nested compiler stderr verbatim. `preflight.json`, `version.stdout`, and `java.stdout`/`java.stderr` retain the local target/tool checks.

No target search hits or clock API/unit evidence were obtained. No snapshot was produced. Clock source and runtime alignment remain **unknown**. The attempt stopped without retry, decompilation, alternate entry point, configuration change, device access or MCP call. Internal `binary_session`/`open_binary` labels in the CLI diagnostic are not assistant MCP invocations. The original T96 receipt is unchanged.

Raw files named above are preserved under `$HOME/.local/share/westlake/runtime-clock-cli-20261023/inner-01/`, not included in the public repository. Their original hashes are in `results.json`. No permission or configuration change was made.
