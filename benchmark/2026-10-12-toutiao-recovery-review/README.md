# Toutiao current-boot recovery: independent review, not a deployment

## Latest R2 decision: offline accept of 9763, not board admission

The accepted four-file frozen snapshot is `io-9763171a/`, now identical to R1
final commitc014f86102f55b51033a0e5032c90ab4af089d09. Watchdog full SHA is
9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072;
helper80a263d9, fixture75b691a3, tests9bdafe0f are pinned in its manifest.
This review **actually executed** 14 independently injected cases against that
snapshot; all14 meet the control-safety criteria, with original case commands,
stdout/stderr and data before/after hashes retained in `.artifacts/io-9763171a/`.
`evidence/io-9763171a-raw-manifest.json` pins every original file, not just an
assertion that tests passed. We do not repeat the already-green full suite.

Six previously failing families are closed within that scope: owner write,
owner exact readback, sequence, instance, state and events.log failures now
exit5 and never report READY. Owner failures prevent any parent/child launch;
later failures preserve the already-started app and lock rather than killing
the app. `control_file`, exact-content/size readback, audit-before-state and
io_fail/keep_lock implement this boundary. Parent/spawn output failures exit3;
PID reuse refuses without relaunch; old/new stop remain; capture error becomes
UI_UNVERIFIED; manually-consented feed can become READY without automatic
touch; default execution remains off. This does not prove every filesystem,
shell, namespace, JIT or rendered-UI configuration on OpenHarmony.

Old ccb editing-checkpoint BLOCKER and commit2b872224/4d3a8e53's **own** six
BLOCKER results remain historical, with their own unmodified snapshots and
original outputs. They neither overwrite nor describe the accepted new SHA.
The sections below are chronology of earlier deliveries; later followup1406
closes the then-unknown live-helper bytes (only one comment differs from80a).
Current defaults in review.py report the new bounded offline accept, never UI
or seal acceptance. Completed 053-acceptance exit124 means no old waiting
driver/seal can be reused; no_mac_repair requires a new authorized attempt.

**Integration remains pending:** see `NEW-ATTEMPT.md` for the real window-ID /
source_app_namespace / host_spawn chain, omitted JIT preparation, HERE-relative
helper placement for both watchdog aliases, exact UID/reconcile/environment /
format gates, explicit old-stop handling and default-disabled rollback.
Fixture parent_tool/spawn_tool are not those real providers. t4 integration is
being independently reviewed without changing t0's candidates or any plan.

Final receipt-only checks:4 Python tests passed (0.048s); the current Rust
candidate selector passed1 test and ran the same4 receipt checks (0.040s).
Original outputs are `evidence/final-receipt-checks.txt` and
`evidence/final-receipt-rust.txt`. No accepted shell suite was repeated.
`T4-FIRST-REVIEW.md` records the first concrete27-file integration checkpoint,
16/16 source SHA matches and six closure items. It is not final T4 acceptance.
Regression scope is approved Plan-2:61b local20-key plus existing5cd128.
The earlier unit/Rust/lifecycle outputs below are explicitly historical;
their success must not be relabelled as this final shell candidate run.
Raw isolated receipts remain at the portable paths in their SHA manifest;
they are retained, not pruned or regenerated. Git index is not writable in
this sandbox: the explicit landing list is for outer to land, with no push.

## Earlier R2 evidence and review chronology (historical)

## Evidence first and what was wrong

This package is **91-R2**, cx-bms, offline only. It independently re-hashes
28 supplied local sources (`sources.json`) including the deployed **79**
watchdog, deployed **91** overlay and **83–93** index/originals. The current
boot is `ac87bbbe-5f9b-496f-8002-43279e072042`, serial
`61b0657200000000000000000324012c`. There are no board/VM/SSH calls, source-run
changes, privacy actions, signals, stop removals, runtime builds or signatures.

The previous assumptions to reject are: an ARMED receipt proves a live guardian;
a live keeper replaces the recovery supervisor; snapshot failure proves an app
failure; a historical privacy/feed demonstration proves today's refresh/article
success; and an old running driver authorizes replacing its bound control code.

`review.py` recomputes every SHA, all indexed existing originals, the instance
identity, plan/driver/placement identity and these facts. Missing or drifted
evidence refuses the review. Raw large logs stay in their existing source run,
not copied or overwritten here. Each fact below cites the corresponding source
ID in `sources.json`, which includes its portable path, full SHA and scope.

## Current failure and ownership chain

| Fact | Witness | Limit |
|---|---|---|
| Sequence 118, child 9548, birth 25409, parent 9529, started uptime 254, `mode=fresh` | instance / instance118 / sequence / index | Captured identity, not present-day process authority |
| UI stays unknown through uptime 438, elapsed 184 seconds | ui | The 180-second bootstrap limit can be reached; the exact cleanup/stop actor is not recorded |
| Snapshot says `write ... current.png as jpeg failed` despite requested png | snapshot | CAPTURE_SCREEN is an old-boot hypothesis, not proved on this boot |
| Guardian 5936 absent; lock owner absent; CLEANUP_BLOCKED; stop mtime 09:58 | guardian / owner_presence / state / stop | Stop predates 10:07 SIGSEGV; do not say the crash killed the guardian |
| Receipt ARMED records guardian5936/birth23291 and keeper3956/birth4528 | receipt | Keeper is screen-only; this report does not claim fresh keeper liveness |
| Parent log reaps child9548 signal11; hilog records SIGSEGV | parent / parent_tail / crash | Native crash root is out of scope and unknown |
| Expected private-tmp child stderr is absent | child_absent / index | Parent actually logs redirect to `/data/service/el1/public/appspawnx/adapter_child_9548.stderr`; that alternative file has not been collected |
| One ordinary-icon reentry did not create a recovered child or watchdog | reentry | Parent or imehost being alive is not successful recovery |

The U13 system parent is 4792, distinct from the **Route B** parent 9529 and
child9548. Their captured values must never be reused as a live kill list.
The pinned guard **source** checks birth twice, all UID fields, executable path
and SHA, and the private-root run.sh inode. It rejects arbitrary name matches.
However, its live deployed bytes were not separately received; source/plan
identity is not a fresh namespace/process-scope assertion. Its supervisor path
uses `tr`, which has been missing in other domains: do not silently fall back
to a name-based signal if identity inspection fails.

## Immediate independent blockers given to R1

Actual watchdog SHA is
`9ae770bd03e9846b9868b895ddc84f894c63811f6e30c1d1a61ce581172ab2ad`.
Actual overlay SHA is
`eb9deb24a5acd8f1c5a8a7d82fbeee9ae0d2248d6b7ca12eaf825ec78d5f7439`.
`results.json.control_risks` gives actual source line numbers.

1. Watchdog automatically touches privacy (and login). The new candidate must
   leave these actions to the user, preserving their consent/data.
2. `feed_count >= 2 && consented == 1` only recognizes scripted consent.
   Human-consented feed must not depend on an automatic touch flag.
3. Failed snapshot becomes `unknown`, then bootstrap_timeout and cleanup.
   Unknown/error must not kill a still identity-matched live child, nor fake UI
   READY. Process exit and UI availability are separate channels.
4. `fresh` moves `app-data`, `data`, `webview-t-data` and can delete a previous
   archive. Existing data must survive first launch, crash, repeated reentry and
   failed cleanup, not just the happy fixture.
5. The actual overlay rejects SAME_BOOT_ALREADY_ATTEMPTED and existing socket,
   but clears stop markers on a new attempt. Do not blindly rerun it, bypass
   its same-boot guard, clear stop or start a second guardian to make progress.
6. Candidate identity must include boot/PID/birth/UID/exe/private namespace and
   fresh lock ownership. Empty PID, PID reuse, root U13 parent, foreign owner
   and unavailable inspection must fail closed. Preserve observable failures
   and bounded backoff. SIG11 metadata must belong to this instance/boot.

These are control defects, not a claim that fixing them repairs the native
SIGSEGV or proves refresh/article. The historical b43 Bug7 is not reused as the
current permission root.

## Run, plan, timeout and invalidation boundaries

The current source plan is **04d64043…**, driver **a7add551…**, provider
**2a40aafd…**, placement **e856dab4…**; full values are in results and the source
index. The acceptance draft binds this plan and current boot; it is unsigned.

- Provider `_await_outer_signature` defaults to **5400 seconds** measured from
  its own `time.monotonic()` start, polls every5 seconds, and returns1 when not
  signed. An environment override is possible. The actual environment/start
  monotonic deadline and current driver liveness have not been captured.
- The driver's subprocess timeout is **10800 seconds** for ordinary commands;
  wait-prefixed probes cap at15 seconds; boot timeout is300 seconds. These are
  bounds, not proof the process is still waiting. Timeout becomes124; OSError
  becomes125. stdout/stderr are recorded before the step JSON is finalized,
  so absence of 053-acceptance.json does not itself mean the driver is alive.
- The referenced window document has **old boot68db… and expiry
  2026-10-11T20:00:00+08:00**, not this boot. Its note says it is not the binding
  authorization gate. We do not infer the whole run was unauthorized: the
  external authorization used to launch this attempt has not been independently
  pinned here. This document cannot authorize new work today.
- The provider recognizes an outer receipt with matching plan SHA; the driver
  separately checks the criteria/boot. A matching receipt is not safe to write
  while checks are false. No fake 4/5→5/5 or signature is produced here.
- Capture of unchanged facts only is additive evidence. Control bytes changing
  watchdog alias, owner helper, reconcile policy, overlay or placement requires
  new candidate hashes, semantic readback, placement/plan/authorization and new
  attempt. The reconciled-file content exclusion is not an unbound-code license.
  PID/boot/UID/namespace changes invalidate captured ownership, not necessarily
  historical screenshots; new identities need fresh evidence.
- Modifying the control plane after autonomous boot is a Mac intervention.
  It cannot retroactively satisfy this run's `no_mac_repair`/cold-boot criterion.
  A repaired run needs a separately authorized fresh autonomous proof; this
  package does not issue a reboot command or decide it is safe on61b.
- Once expired/exited, do not resurrect the same process, overwrite old step
  logs, extend a deadline or re-sign the old draft. Preserve the run; future
  resume/new-run policy belongs to the operator and outer under a new binding.

## Disabled minimal execution and rollback recipe

```sh
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/2026-10-12-toutiao-recovery-review/review.py
PYTHONDONTWRITEBYTECODE=1 python3 benchmark/2026-10-12-toutiao-recovery-review/preview.py
```

Both commands are local. The preview prints six phases: read-only identity;
archive original **control** bytes without moving data; replace only the
approved Route B aliases; pending explicit stop/arming policy; user-owned
foreground verification; identity-guarded rollback to archived control bytes.
There is no executor and `--action execute` always refuses before any command.
Providing a stale/wrong boot/plan/candidate approval refuses even preview.
`context.json` leaves new-plan/candidate SHA null: no placeholder authorizes use.

Concrete board install/start/signal argv are deliberately pending R1's actual
interface and the separate board-window review. Rollback must first verify the
candidate guardian's exact identity, never signal U13 or a reused PID, retain
stop/user data, restore exact backed-up aliases/metadata and read them back.
Restoring the unsafe old watchdog must not automatically restart it. No global
mount/installer/permissions/SELinux or shared U13 binary changes belong here.

## Candidate review status and tests

Candidate is **pending** until R1 supplies actual bytes/SHA and behavioral
receipts. `review.py --candidate PATH --sha256 FULL_SHA` is a conservative
static rejection screen, **not a complete shell parser or behavioral proof**.
It rejects pinned known privacy/data/name-kill/stop defects and SHA drift;
safe-looking text stays pending. No self-declared manifest can become accept.
Final independent acceptance needs tests against the actual candidate interface
and source/fixture/log hashes; no UI/seal signatures follow from offline tests.

13 Python known answers exercise real source identity/drift/missing evidence,
preview with fake hdc/kill/deploy/UI tools, unchanged stop/data sentinels, expired
and wrong approvals, execute refusal and defective/safe-looking candidates.
Three Rust selectors invoke EvidenceTests/PreviewTests/CandidateTests. Raw test
outputs are under `evidence/`; results label final t1 dependency pending rather
than disguising the first delivery as completed candidate acceptance.

Contract copies under `contracts/` are byte-identical to the read-only master
project/t1/t2. They are not changed to pass a test. No push; this worktree's
shared git index is read-only, so explicit landing paths are for outer landing.

## R1 checkpoint adversarial result — BLOCKER, not final release

R1 announced e4a039b3, but its editing file subsequently differed. This package
copies a read-only checkpoint at **ccb19087eebb3e60eb95014bdb703c93392466773c0e974b3cb63a0189baed0e**,
with helper **80a263d930a67c48fa92f5caa7b6266ee13ff75079ff5ba880e9576da72dbdc4**
and both supplied fixture files. Every copy matches its original-byte SHA in
`candidate-checkpoint/manifest.json`; none is represented as a final R1 release
or as byte-identical to e4a039b3. Old behavioral receipts cannot bind new bytes.

`adversarial_checkpoint.py` executes only this copied shell using the supplied
isolated fake proc, data sentinels and command recorder. It redirects all
fixture receipts to this worktree's `.artifacts/`, never into the t0 tree.
An injected directory at lock/owner makes the candidate's line87 owner printf
fail. It nevertheless invokes **parent_tool + spawn_tool**, records **READY**,
and returns **0**. The lock has no valid owner. This violates fail-closed
ownership and observable command failure, so this checkpoint is **BLOCKER**.
The helper's release path also reports synthetic self UID/read errors; those
are fixture limits and not the reason for rejecting the earlier unowned launch.

Repair requested to R1: refuse before any parent/child launch when owner write
or exact readback fails; preserve a foreign/changed owner, and test sequence /
instance / state write failures as well. Candidate/helper/fixture must be pinned
as one final release, then independently rerun. No candidate modification is
made by R2. No real stop, data, parent or child is controlled by this test.

Raw unredacted output stays persistently at
`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-12-toutiao-recovery-review/.artifacts/adversarial-checkpoint-original.txt`
(not public landing; it contains local fixture paths). Per-case commands,
stdout/stderr and before/after sentinel hashes are in the sibling
`.artifacts/adversarial-cases/`. The earlier `evidence/adversarial-cases/` first
attempt remains untouched and is also not landed. Public results contain the
portable outcome and raw-file SHA, not fabricated or redacted raw evidence.

After adding the independent real-checkpoint negative case: Python14/14,
Rust3/3 and lifecycle3/3 rc0; raw outputs are `evidence/tests-with-checkpoint.txt`
and `evidence/lifecycle-with-checkpoint.json`. PASS means the known defective
checkpoint is correctly classified BLOCKER, not that its owner write is fixed.
Default `review.py` now verifies checkpoint/result/raw-receipt SHAs and reports
that BLOCKER; an explicitly supplied different SHA remains separately pending
until its own full behavior review. First-delivery outputs are not overwritten.

Fresh validation: Python13/13, Rust3/3, lifecycle rc0/quality1.0/scenarios3/3
with two reported lint issues. `evidence/lifecycle.json` is the full raw
production output. These computational checks prove evidence identity and the
pending/blocker/preview safety rules, **not final R1 candidate acceptance**.
`unit-tests.txt` is the first passing checkpoint; `tests-and-rust.txt` is the
final run including the literal-U13-PID negative subcase. A dry-run git add was
refused with index.lock Operation not permitted; no commit or push occurred.
