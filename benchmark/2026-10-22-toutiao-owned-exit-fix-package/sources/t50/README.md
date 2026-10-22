# T50: conservative exit classification and bounded refusal records

T47 could turn a real disappearance between monitor reads into terminal OWNER_REFUSED;
its one-file-per-sequence audit could instead turn the next refusal into IO_FAILED.
The unchanged monitor-first-read branch also accepted any Z without checking birth.
This offline candidate classifies these three read-failure sites conservatively and
retains up to 16 additional exclusive refusal records. It is not a deployed fix or a
claim about the cause of the T48 white screen.

**Final evidence:** 35 cases × exact T47 baseline/candidate = 70 actual local shell
executions; 6 real-entry refusals under ordinary Python and `-O`; the single Rust
selector passes. `results.json` binds the final receipts and per-case outcomes.
`prepare.py` successfully reconstructed the exact candidate from baseline + diff.

- Watchdog: `d45a8d36794d3927c0c03f19d71fa632a0b9cec18944d9d9f92a3406b49f64f0`.
- Owner, unchanged: `fc63dae9a24c4a41d1e8db92612cc256734c650e94451513b97f05226f82fe58`.
- T47 watchdog input: `bcae2c697ae5ee6e31c836cd38d322d5120a87ffa74f1d35d2c88acca7be818e`.
- Input paths/blobs, current contract hash, and T49 fixture provenance: `sources.json`.

## Actual changes

`candidate/watchdog.sh:101-138` classifies within a subshell using explicit exit codes.
It uses RB_PROC, verifies the recorded parent birth from that same root, checks root
readability/traversability, and lists the root only after confirming child-directory
absence. Present child directories require a complete numeric stat read; Z and birth
come from the same read. Only witnessed gone or same-birth Z return 3. Unknown,
unreadable, malformed, reused, or still-live identity remains a refusal.

The two child_owned direct reads (`:141-158`) and monitor initial read use this classifier.
Gone/zombie and first_birth/last_birth/monitor_birth are persisted through the existing
event gate. Confirmed exits never call rb_deny or consume a diagnostic slot. Monitor
uses the original process_exit → RECOVERING path. Capture uses the actual capture_frame
and capture_context functions, records child_exited_during_capture, and waits for the
next monitor observation. Initial attach/spawn rc3 is START_FAILED before attempt/seq
commit and instance rewrite.

`candidate/watchdog.sh:32-46` preserves slot 0 and searches `.1` through `.16`.
Existing regular bytes are never overwritten. Symlink (including dangling), directory,
exhaustion, actual failed write, and actual failed readback are IO_FAILED with lock kept.
Pre/post control_file checks and noclobber remain. Slot 0 is byte-equal to T47 for the
same actual refusal (hash in results). Filenames refer to the **last committed seq**;
records retain actual phase/pid/birth, including initial validation with an old seq record.

## Replay boundary and outcomes

| Actual branch | Baseline | Candidate |
| --- | --- | --- |
| direct first/last read disappears | OWNER_REFUSED / rc2 | RECOVERING then budget-limited RETRY_LIMIT / rc4 |
| monitor first read gone | original recovery / rc4 | witnessed recovery / rc4 |
| monitor different-birth Z | original recovery / rc4 | OWNER_REFUSED / rc2 |
| same-birth Z at direct read | OWNER_REFUSED / rc2 | witnessed recovery / rc4 |
| attach/spawn validation gone | OWNER_REFUSED / rc2 | START_FAILED / rc3, attempt 0 |
| capture first/last direct read gone | refusal then recovery | exit event, no refusal, then recovery |
| old normal refusal record | IO_FAILED / rc5 | new numbered slot, original refusal rc2 |
| unknown/live/reuse/ppid mismatch | refusal | refusal |

`fixture.sh` derives from T49. Only external process-file/metadata reads and device
boundaries are synthetic; production main, classifier, child_owned, rb_owned, rb_deny,
state/event persistence, and capture functions execute. Parent acceptance and capture
initial directory creation are the documented T49/external-boundary seams. The parent
visibility witness itself executes the original rb_birth on local fixture bytes.
The rb_birth observational wrapper delegates to the original body, never selects its
value or rc. A removal occurs after a successful actual local stat read; numeric
mismatches are used only in the explicitly named reuse tests. No real target processes,
proc filesystem, devices, signals, permissions, or T38 paths are accessed.

Initial no-rewrite comparisons start at the validation boundary **after the original
supervisor-start persistence check**; those startup writes are retained. The failed
validation does not execute the later attempt increment, sequence write or instance
rewrite. MAX_ATTEMPTS=1 proves unchanged termination budgeting without real relaunch;
MAX_POLLS=2 for capture allows the next monitor confirmation. Normal and stop controls
are included. Synthetic image bytes and classifier results do not demonstrate UI/feed.

Residuals: rb_owned-internal, namespace-readlink, and ppid-read errors remain terminal;
rb_owned disappearance is explicitly replayed as such. Present-but-unreadable stat
while reaping still refuses. There is no retry loop or weaker identity decision. The list-after-absence reap-race
ordering is statically checked; it has no timed kernel-reap fixture.
Local `/bin/sh` noclobber tests do not establish device-shell O_EXCL/concurrency behavior.
There is no device acceptance, white-screen root cause, or full contract-lifecycle claim.

## Reproduce (offline, fresh output only)

From the repository root:

```sh
python3 benchmark/2026-10-22-toutiao-owned-exit-fix/check.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_owned_exit_fix -- --nocapture
python3 benchmark/2026-10-22-toutiao-owned-exit-fix/prepare.py --out benchmark/2026-10-22-toutiao-owned-exit-fix/.private/reconstruction-new
```

`check.py --out <fresh-directory>` is also supported. Both default Python and Rust
outputs are durable `.private` directories, not temporary evidence. Every actual shell,
negative checker, patch reconstruction, and Cargo invocation has argv/start/end/stdout/
stderr/rc. Public results contain hashes; raw stderr and personal paths remain private.
`raw-index.json` identifies the private manifest and final output; `landing-paths.txt`
is the exact public handoff. No commit or push performed.

The first development batch is retained: its stop injection occurred too late for
STOPPED before the poll limit, and its expectation incorrectly assumed T47 readback.
Those fixture/expectation errors were corrected; no historical rc or raw output was
rewritten. The final 70 executions use the fixed fixture, not the earlier 68-case receipt.
