# T46 — persist owned guardian refusal diagnostics

The deployed watchdog combined a monitor birth mismatch and a later `child_owned` rejection into `child_identity_changed_no_signal`. Its owner helper emitted detailed JSON only to stderr. This candidate preserves those checks and their order, while retaining refusal JSON in the existing control directory. It does not implement recovery or establish a white-screen cause.

The final offline replay passed 11 cases, executing baseline and candidate main branches 22 times. The dedicated Rust target passed 1/1. The same deliberately corrupted baseline file was rejected in normal Python (source-pin mismatch, rc1) and optimized Python (optimization explicitly prohibited, rc1). No device, VM, REA, real process inspection, permission change, T38 test, commit, or push was performed.

## Source and minimal change

`sources.json` records the main commit, contract SHA, repository source paths and git blobs. Baseline bytes were compared with those git objects before copying:

- `watchdog.sh`: SHA `2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a`, blob `22fa04be19ed59a55983a84b38356d79d4ec2aa5`.
- `route-b-owner.sh`: SHA `6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c`, blob `f73a86bf1b6c940489ba61f46cc665641de87e02`.

`candidate.patch` is the complete change. The watchdog enables refusal persistence and splits the monitor reason into `child_birth_changed_no_signal` or `child_owner_check_failed_no_signal`. Birth mismatch still short-circuits `child_owned`. Both ordinary rejections retain rc2. Owner checks and quiet discovery retain their original behavior.

The owner rejection hook reuses the existing byte-safe JSON encoder. `guardian-refusal-$seq.jsonl` is created exclusively under `$F`, with the original `control_file` checks, noclobber creation and nonempty verification. An existing file is not reused; a symlink or directory is refused. Partial encoding/write failure retains partial evidence and enters the existing `io_fail` path (rc5, lock retained, best-effort `IO_FAILED`). It never turns a diagnostic failure into permission to continue. An existing per-sequence refusal intentionally blocks a later diagnostic write rather than overwriting history. No identity predicate, process operation, retry budget, launch decision, or host request handling was added or loosened.

## Executed checks and limits

`check.py` removes only the final automatic `main "$@"` invocation from each pinned source in its disposable replay library, installs synthetic seams, then calls the actual `main`. Production `child_owned`, `rb_owned`, JSON encoding, control-file guards, event/state writers and refusal branches execute. Parent ownership and frame capture are synthetic seams; every process input is a local fixture. Executable-link/hash/inode reads are local mocks. Launch/probe, signal and retry seams fail if invoked. No installed state or live process information is read.

Cases cover monitor birth mismatch; UID, executable path, namespace and PPID failures inside the actual owner checks; normal continuation; pre-existing file, symlink and directory; partial output failure; and quiet discovery. Detailed JSON actual/expected values are checked. Query/control traces and return codes match the baseline for the five identity refusals, normal continuation and quiet discovery. Diagnostic-storage faults intentionally use rc5 instead of the baseline identity refusal rc2, as required by the contract. This is bounded branch evidence, not an exhaustive guardian or device test.

Run from the repository root:

```sh
python3 benchmark/2026-10-22-toutiao-owned-guardian-diagnostics/check.py --out <new-persistent-directory>
cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test toutiao_owned_guardian_diagnostics -- --nocapture
```

`python -O`, `python -OO`, and `PYTHONOPTIMIZE` are rejected at checker entry, so assertions cannot silently disappear. A bad-source fixture is retained at `.private/bad-source-pin/`; both rejection invocations used that same modified file. The original baseline/candidate files remain unchanged.

## Evidence and handoff

`results.json` contains the candidate pins, case results, raw-stream hashes, timestamps and bounded conclusions. `.private/replay-03/` is the final persistent replay, including per-case argv/stdout/stderr/rc/start/end and actual fixture libraries. Prior runs remain intact; they were not retroactively given timestamps. The interruption was a user pause, not an execution failure.

The Rust target runs the same checker in a temporary directory and deletes its per-case files on completion. Its own argv/stdout/stderr/rc/start/end are retained under `.private/rust-03/`. The persistent replay is separate evidence, not a claim that Rust retained its temporary case files.

The metadata-only lifecycle invocation used `lint,boundary`: quality score 1.0, rc1 with three skipped scenarios because the test layer was omitted. Its original output and fresh explain output are retained. No lifecycle PASS is claimed; the dedicated Rust target above supplies the executed test evidence without running unrelated targets.

Raw stderr and generated private fixtures stay private. `.private/MANIFEST.sha256` binds their preserved bytes, excluding the disposable Cargo target cache. Public `SHA256SUMS` uses repository-relative paths; `landing-paths.txt` is the exact public listing. This packet remains uncommitted for outer review and landing.
