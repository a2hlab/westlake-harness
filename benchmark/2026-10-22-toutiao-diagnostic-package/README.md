# T47 — disabled diagnostic control package

The T46 candidate alone did not bind the actual 5cd startup/member pins. This local build uses all nine T46-P byte-exact historical controls and the accepted T46 candidate at commit8e4c993077. It emits **six candidate files and six exact rollback files**. The candidate is **disabled**, not deployment-ready, not a new approval, and not a white-screen fix.

`baseline/` is the public reproducible historical input snapshot. All nine files matched the collection size and SHA; bounded UTF-8 text review found no credentials or literal personal home paths. Original STARTUP_APPROVED_BY and ENABLED values are historical evidence only. The first ASCII-only review failed on a non-ASCII source comment before copying; that rc1 is retained privately and in the review index. No bytes were transcoded. Collection argv/stderr remain private.

`inputs/preimage-inputs.json` preserves the actual device paths, mode/UID/GID/dev/inode/mtime and SHA references. `inputs/source-lock.json` pins that index and four T46 source/provenance artifacts to exact committed bytes and Git blobs. Original inputs and all prior reports remain unchanged.

## Exact scope

- Candidate watchdog and owner helper are unchanged accepted T46 diagnostic sources.
- Entry changes only the two corresponding SHA literals.
- Members changes only watchdog/owner/entry hashes. The other **ten lines remain byte-identical**.
- Startup changes only the members hash and STARTUP_ENABLED from1 to0; expected.sha256 binds the new startup bytes. Historical approver text grants no new authority.
- All six rollback files exactly match the baseline. Original stat references are in `package-01/receipt.json`; this is not a device metadata application.
- Boot-entry, config-common and init cfg remain unchanged baseline inputs and are not candidate replacements. Root remains `/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012`.
- Of13 manifest members,4 were collected in T46-P. **Nine uncollected members require fresh predeployment hash checks**. `receipt.json` separately records modified/unmodified and collected/not_collected. Whole live package validation is not claimed.

## Reproduce from main checkout

Run from repository root, with a fresh output directory; no private HOME input is needed:

```sh
CARD=benchmark/2026-10-22-toutiao-diagnostic-package
python3 "$CARD/build.py" --inputs "$CARD/inputs/preimage-inputs.json" --bytes "$CARD/baseline" --out "$CARD/rebuild-01"
python3 "$CARD/check.py" --out "$CARD/.private/recheck-01"
CARGO_TARGET_DIR="$CARD/.private/cargo-target" cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test toutiao_diagnostic_package -- --nocapture
```

These are local assembly/check commands, not deployment commands. Output collisions refuse without changing history. Builder uses explicit checks (not removable assertions) and never executes startup inputs. It rejects optimized Python and PYTHONOPTIMIZE. The checker deliberately invokes -O only as a negative test and confirms no package is produced. To retain streams for another build, reuse `check.logged(argv, new_log_directory)`; it writes argv/start before subprocess execution and stdout/stderr directly to persistent files, followed by rc/end.

## Executed evidence

Public `package-01/` was built from `baseline/` by the real builder, rc0, then independently checked against the six-file/pin chain. Five bounded checks passed: real build/chain; existing-output refusal with unchanged tree; wrong SHA refusal without output; actual production parser refusal of executable syntax; optimization refusal without output. Rust target:1 passed,0 failed,0 skipped. No unrelated suites or runtime/guardian replay were run. No full agent-spec lifecycle PASS is claimed.

Raw builder/check/Rust argv, times, streams and rc are under `$CARD/.private/{build-01,check-driver-01,check-01,rust-01}/`; Rust also retains its own checker invocation directory. `raw-index.json` lists exact hashes and sizes, omitting disposable Cargo cache. First snapshot precheck failure is retained as `.private/snapshot-first-failure.json` (transcribed original tool error; not retroactively timestamped).

Device/VM/runtime build/deployment/process-control actions0. No permissions, identity predicates, lifecycle policy, init cfg or existing boot directory changed. No new signature, deployment runner or T38 work. `author_commit=null`; outer owns landing. `landing-paths.txt` is the fixed public listing, and `SHA256SUMS` covers every listed file except itself.
