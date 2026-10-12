# R1: data-preserving Toutiao recovery candidate (offline)

## Returned release and I/O repair

The first release, commit `2b8722245f22f50516039772b71e10a55d9ce727`,
watchdog SHA `4d3a8e530bb50d93bf0170040bc29ea8b9787ef854190342bb2524f3a1859232`,
was **rejected**, despite passing its original 12 test methods. Those tests did
not inject critical control-file I/O failure. Independent R2 and outer review
proved that `lock/owner` as a directory caused a failed printf followed by
parent/child launch, `READY`, and exit 0. Sequence, instance, state, and event
writes had the same unchecked-status defect. The old receipt is not approval of
the repair; its sources, raw tests and prior commit remain preserved.

`evidence/io-revision/red-tests.txt` runs new tests **before the repair** against
4d3 and records 10 failing subcases. The old exact bytes are additionally in
`sources/watchdog-rejected-4d3a8e53.sh`. The new SHA and all four source/fixture
hashes are in `evidence/io-revision/frozen-checkpoint/manifest.json`; copies
there are immutable review inputs, separate from editing paths.

The repair checks each control write and its readback. Lock ownership must be
written and match exact PID/birth/boot content **and byte length** before any
launch. Nonregular/symlink control paths refuse. Sequence, instance, state and
events are checked before launching; later failures stop the supervisor with
exit 5, leave the app/parent untouched, and retain the lock for review. A foreign
existing lock emits a refusal only to stderr, without writing its shared state.
Present unreadable/malformed sequence is never silently converted to 0.

State transitions first persist a `transition_target` audit intent; only then
does a successful exact state write publish that state. Event append status and
last-line readback are checked. READY additionally requires a successful feed
archive/cmp and state readback. On failure, stderr carries boot/sequence and both
PID/birth pairs; a best-effort `IO_FAILED` invalidates old READY only after this
supervisor has verified its lock. If that device is also unwritable, nonzero exit
and stderr are authoritative, and **any existing state file is stale**, not a
success receipt. No failing operation is hidden by a later successful state.

The new tests inject owner write rejection and wrong readback, plus four critical
files as directories before launch and immediately after spawn. Early failures
invoke neither parent nor child; post-spawn failures leave that one launched app
untouched, retain the failure lock and never publish READY. Directory injection
is an actual shell/path failure, not a claim to reproduce a device EIO or ENOSPC.
These 10 subcases plus the original behavior tests pass in the new run. A first
full rerun also exposed two fixture assertions that counted the newly recorded
**read-only cat** as an effect; those assertions now allow only cat and still
reject every write/launch. That failed rerun is preserved in
`evidence/io-revision/checkpoint-tests.txt`, not overwritten.

The deployed controller confuses capture failure with bootstrap failure, rotates
existing data, touches privacy/login UI, and requires its own automatic-consent
flag before accepting a feed. This deliverable replaces that controller in an
independent candidate directory. It does **not** repair the native SIGSEGV,
establish the cause of the screenshot failure, change the current deployment, or
complete seal acceptance.

## Evidence and provenance

| Input | Exact evidence / provenance | Scope |
|---|---|---|
| Actual deployed watchdog | `sources/watchdog-deployed.sh`, SHA `9ae770bd03e9846b9868b895ddc84f894c63811f6e30c1d1a61ce581172ab2ad`; copied from wiki acceptance evidence **79**, not a placement source substitute | Baseline controller |
| Actual deployed overlay | `sources/overlay-deployed.sh`, SHA `eb9deb24a5acd8f1c5a8a7d82fbeee9ae0d2248d6b7ca12eaf825ec78d5f7439`; copied from acceptance evidence **91** | Unchanged integration boundary |
| Route B identity guard | `payload/route-b-owner.sh` = `sources/route-b-owner.sh`, SHA `80a263d930a67c48fa92f5caa7b6266ee13ff75079ff5ba880e9576da72dbdc4` | Exact existing helper, including unused signal functions |
| Guard lineage | `cfab66ae8c` base; UID-dynamic source landed at `d837acf904fcbd38edde93d1172555f1c8a742fc`, from wiki `aa6e561b75`; main-tree `benchmark/2026-10-10-u13-autostart/boot-slot-uid-dynamic/route-b-owner.sh` | Existing tested implementation, not a new device-verification claim |
| Historical guard tests | Main-tree `benchmark/2026-10-10-toutiao-boot-slot/{README.md,test_slot.py}` and `benchmark/2026-10-10-u13-autostart/boot-slot-uid-dynamic/tests/test_boot_slot_uid.py` | Local donor search; this round executes the separate candidate tests |

`sources.json` pins all donor hashes. The read-only originals are under
`$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-10-demo-seal-61b/seal-run-20261012T094950/acceptance-evidence/`.
No file there was changed. Current evidence **83–93** identifies historical
child 9548 / parent 9529 / birth 25409 / sequence 118 / started 254; UI remained
unknown through uptime 438, and the snapshot writer reported failure. Parent log
**90** reports reaping 9548 with signal 11. It also names the actual stderr
redirect `/data/service/el1/public/appspawnx/adapter_child_9548.stderr`; the
different path marked absent in **89** does not prove that redirect absent.
The exact stop actor, screenshot permission cause, and crash site remain unknown.
These are historical captured facts, **not** this-round liveness or UI evidence.

Outer's read-only main-tree `benchmark/2026-10-12-toutiao-recovery-readonly/followup-1406/`
adds the real owner/start-parent/spawn scripts and SHA index. Live helper
`eaba972bbfb5de827341df3bd40e85b99d5ba9cd355f0c1aeddaa34186147abd` differs
from the copied 80a helper only in comment/blank content; executable lines compare
equal. The real start-parent rewrites the current host window ID in `run.sh` and
starts the namespace parent; real spawn calls `host_spawn` with the existing
request. This task only reads their captured bytes. Synthetic launcher tests do
not prove those transitive operations or permissions; current stop and native
failure remain untouched.

## Candidate behavior

| Baseline defect | Candidate behavior | Executed check |
|---|---|---|
| `prepare_profile` fresh mode moves data and removes the previous profile | Requires existing `app-data`, `data`, `webview-t-data`; never rotates, deletes, chowns, or relabels these trees | Three sentinel hashes unchanged through initial launch, three bounded child-exit retries, and explicit same-boot attachment |
| Privacy/login branches call `uinput` | Privacy waits for the user; login/unknown stays unverified; no UI input command | Recorded commands contain no touch or consent action |
| Feed requires `consented=1` | Two consecutive classified fresh feed captures yield controller `READY`, without a consent flag | Privacy → feed → feed passes without input |
| 180-second unknown/capture failure triggers cleanup | Capture/classifier failures record `UI_UNVERIFIED`, return codes and `alive_no_cleanup`; no live-child cleanup or deadline-based kill | Snapshot failure with a stale feed file, unknown frame, and classifier failure all avoid READY/relaunch/signals |
| Controller repeatedly cleans parent and child | Reuses the verified parent; only an actually absent/zombie child permits a new launch, with 3 attempts and 5/10-second backoff | Three child launches, one parent launch, then `RETRY_LIMIT` |

`READY` here is a controller observation of two classifier feed results. It is
not a substitute for `snapshot_display` ground-truth review or an acceptance
signature. Screenshot bytes in tests are synthetic; no screenshot was taken on
a board during this task.

## Identity and side-effect boundary

The candidate starts disarmed (`TT_RECOVERY_EXECUTE` defaults to 0). Execution
requires an exact expected boot, non-root owner UID, preserved data directories,
and an existing operator state directory outside the runtime data tree (physical
paths are checked, including symlink aliases). Existing `stop` always refuses
startup. An existing lock is never reclaimed, even when stale or ownerless.
Only the candidate's exact PID/birth/boot lock owner is removed on exit.

Child guards preserve PID/birth, all four UID values, exact asx-spawner executable
path and SHA, and the private `run.sh` inode from the proven helper. Additional
checks require a non-init mount namespace and the expected PPID. Parent attachment
uses the same executable SHA/private root/birth/namespace boundary, accepting the
existing root Route B parent for **read-only** identity; it never sends a signal.
The candidate calls neither `rb_signal` nor `rb_script_signal`, never name-kills
anything, and never controls U13 appspawn-x. PID reuse or identity drift refuses
instead of cleaning or spawning a replacement.

The fixture runs the **real** shell candidate. Fake external commands record
launch, ownership queries, file operations, capture/classification and backoff;
forbidden controls fail if called, including shell-builtin `kill` interception.
File-operation fakes only allow the isolated case directory, outside its runtime
data tree. Shell-written state is archived alongside commands and before/after
data hashes. Synthetic `/proc` fixtures model exit, PID reuse, namespace/UID/SHA
mismatches, existing parent/child, stop, and foreign locks. The test does not claim
to sandbox or validate every native/transitive operation inside the production
start-parent/spawn programs: those are replaced with recording commands.

## Reproduction and verdict

From the repository root, without boards, VM or remote access:

```sh
bash -n benchmark/2026-10-12-toutiao-recovery-candidate/payload/watchdog.sh
python3 benchmark/2026-10-12-toutiao-recovery-candidate/tests/test_watchdog.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_recovery_candidate -- --nocapture
agent-spec lifecycle specs/demo-recovery-followup/t1-watchdog.spec.md --code tools/spec-checks --format json
```

Raw runs, per-case command recordings/state/data hashes, final artifact hashes and
the lifecycle results are in `evidence/` and `results.json`. The three Rust
selectors independently execute consent, data/reentry, and identity/refusal
cases. The two contract copies are byte-identical to the main tree, copied only
for local lifecycle as explicitly authorized.

## Integration gaps requiring separate review

1. The deployed overlay still clears stop markers, reconciles UID/data ownership,
   and refuses a second same-boot attempt. It is deliberately unchanged; this is
   not a drop-in reboot/reentry recipe. Current stop must remain untouched.
2. Placement, driver, source SHA bindings, deadlines and authorization remain
   those of the old run. A candidate attempt needs new reviewed bindings; it
   cannot append a Mac-assisted repair into old autonomous acceptance.
3. The existing start-parent/spawn entrypoints and pinned spawner are prerequisites.
   Initial parent creation keeps their behavior; the candidate removes old JIT,
   focus/power/config changes rather than reproducing them implicitly. Production
   launch readiness therefore remains unverified.
4. The JPEG invocation follows the working manual capture form. Its compatibility
   with the deployed classifier, board utilities, and actual screenshot failure
   is unverified. Any failure remains UI-unverified without killing the app.
5. If the verified parent exits, its identity changes, or an unrecorded owned
   child already exists, the candidate stops fail-closed. It does not adopt a
   process by name or repair a parent by signaling it.
6. Independent BMS adversarial review, device integration, human image review,
   and seal signatures are pending. This deliverable authorizes none of them.

Only the standalone candidate, isolated tests, evidence and exclusive Rust
selector are delivered. No board/VM/remote operation, data rotation, automatic
privacy consent, runtime build, frozen-registry change, signature or push occurred.
