# T49 — owned watchdog exit-between-reads replay

T48's persisted refusal did not mean a terminal `OWNER_REFUSED`: its actual capture failure was followed by `UI_UNVERIFIED`, `process_exit` and `RECOVERING`. This offline packet leaves that historical conclusion intact. It demonstrates a different, precisely scheduled monitor path using unchanged production functions, without diagnosing why any third-party process exited.

| Synthetic timing | Baseline | T47 candidate |
|---|---|---|
| Child already absent at first monitor birth read | process_exit → RECOVERING → RETRY_LIMIT, rc4 | Same, rc4 |
| First monitor read succeeds; next child_owned birth read fails | OWNER_REFUSED, rc2 | OWNER_REFUSED, rc2; strict birth failure JSON retained |
| Same timing, same-sequence diagnostic already exists | OWNER_REFUSED, rc2; old file preserved | IO_FAILED, rc5; original lock and old file preserved |
| Identity unchanged | UI_UNVERIFIED synthetic frame failure, observation limit, rc0 | Same, rc0; no diagnostic |

All eight actual shell executions passed, as did the dedicated Rust target (1/1). The first row deliberately retains T46's `TT_MAX_ATTEMPTS=1`: the original implementation reaches its exhausted-budget return after RECOVERING. It does not reproduce T48's three-attempt envelope or assert a subsequent retry. `TT_MAX_POLLS=1` bounds the normal control.

## Exact sources and seams

`sources.json` records committed paths, git blobs, SHA256, contract pin and the reused T46 fixture origin. The four shell files are unmodified copies: baseline watchdog `2b635ef1…` / owner `6bce7c3c…`; T47 candidate watchdog `bcae2c69…` / owner `fc63dae9…`. Full pins are hard-coded in the replay entry and recorded with every execution.

As in T46, the fixture defers only the final automatic main invocation, installs local external-read/device-boundary seams, then calls the actual main. Monitor, child_owned, rb_owned, rb_deny, event/state and diagnostic persistence bodies remain unchanged. The original rb_birth body is copied under a fixture alias, with only its declaration name changed; a tracing wrapper delegates to that body and returns its actual result. It neither selects a birth value nor manufactures a failure code.

The external `cat` seam performs the real read of a local synthetic stat file, then removes only the synthetic PID42 stat/status/directory after read5 (before monitor) or read6 (between monitor and child_owned). The next original rb_birth fails its actual readability check. Successful birth values stay 200; the failed read returns rc1 and no value. Trace validation checks exact ordered successful/failing birth reads and removal boundaries. Original child UID, executable, inode, namespace and parent predicates execute with synthetic metadata. T46 parent-ownership and capture seams remain; this does not replay the actual capture internals. Launch, signal and retry seams fail if invoked. No live target process or real proc filesystem is inspected or controlled.

## Reproduction and refusal evidence

From the repository root:

```sh
python3 benchmark/2026-10-22-toutiao-owned-exit-race/check.py --out <new-persistent-directory>
cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test toutiao_owned_exit_race -- --nocapture
```

For only the eight executions use `replay.py --out <new-directory>`; for read-only result validation use its `--verify-only --out <existing-replay-directory>`. The entry rejects all four source-pin mismatches before creating output. Existing output is refused without modifying its bytes. Checks use explicit `require`/exceptions throughout, not Python assertions.

The actual negative entry runs prove: a corrupted candidate owner is rejected under normal Python and `python -O` without output; a second invocation against the successful output is refused with its complete file snapshot unchanged; removing the actual failing-birth trace event from a separate copy makes the real result verifier reject it without mutation. No production implementation is changed for these checks.

## Persistent evidence and limits

`replay-evidence.json` publishes actual ordered traces, event/state observations, return codes and old/final diagnostic SHA for the eight primary executions. The old diagnostic SHA is identical before/after in both existing-file cases. `results.json` binds the checks and raw records. Raw stdout/stderr/argv/start/end/rc, source pins, fixture files and actual generated source libraries are retained in `.private/checks-01/`; the initial `.private/replay-01/` is preserved separately.

The Rust selector also retains its own uniquely named `.private/rust-checks-*` output, including the checker and every shell record; it does not delete temporary evidence. The enclosing Cargo command records are in `.private/rust-01/`. `.private/MANIFEST.sha256` covers preserved files excluding disposable Cargo/Python caches. Raw stderr stays private; the public listing includes only source, portable evidence and hash references.

This is source-behavior evidence, not a fix, a live root-cause finding or playback acceptance. No device/VM/REA/T38 operation, permission change, deployment, commit or push occurred. No full agent-spec lifecycle PASS is claimed. The branch difference and same-sequence diagnostic collision are recorded for outer review; production code and recovery policy remain unchanged.
