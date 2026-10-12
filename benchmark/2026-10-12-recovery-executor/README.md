# Concrete recovery executor: offline final, not device admission

The e576 integration's disabled default did not prove production preimages,
JPEG compatibility or a17-second startup path under a15-second watchdog budget.
Checkpoint70b6eeda5 exposed additional transaction failures; its raw failed tests
and inventory remain historical evidence. The reviewed executable revision is
**b093d8599aeffac5e4830bd2dc7f6c15806b8a28**, with program SHA430fbf4a,
plan f7dfdd5d, member table6a25a7d6 and durable policy0b4598c1. Full hashes are in
`results.json` and `evidence/transaction-revision/results.json`.
Accepted watchdog9763171a, helper80a263d9, integratione5763d36 and format-only
afd072 classifier remain unchanged. No board/VM/remote operation, user-data
rotation, privacy acceptance, spawner signal, push or seal signature occurred.

## Exact transaction and failure semantics

`executor.py` defaults to preview and creates **no transport**. Execution requires
a full plan and independently pinned outer(codex) JSON authorization containing
the complete plan SHA, serial, current boot, expiry and allowed actions. The
plan does not contain its authorization hash: no circular hash construction.
The actual CLI known-answer writes real files, calculates real SHA values and
uses an isolated HDC protocol recorder; it does not hand-assign `plan['_sha']`.

Before any control write: validate every local member/preimage/tool SHA and
non-null typed metadata, freshly check boot and every target, receive/verify
**all** backups, then recheck. Fresh declared-directory absence and metadata are
also enforced. Target scope is the new attempt tree, two exact watchdog/helper
aliases and the exact init CFG; existing run/JIT/request/native tools are
read-only prerequisites. Original historical stop and user directories are
preserved, never cleared or rotated. The numbered raw transport is reused from
wiki `demo_seal_61b.py`; its installer and old overlay/reconciler are never run.

Each placement records an intent before the attempt. A failed send records its
exact read-only postfailure SHA/metadata, if readable. Rollback accepts only the
signed preimage, candidate, or the exact observed partial state bound to that
intent. A different later state or an unreadable observation refuses restoration
rather than guessing. All backups are checked before the first rollback write;
current targets are checked again immediately before each restore. First mkdir
failure with zero sends and unchanged members closes as
`NO_MEMBER_CHANGES_NO_DONOR_RESTART`, without a stop write. Directory/audit
residue is retained; this receipt does not claim a recursive cleanup.

For `/system/etc/init/01_westlake_u13_toutiao.cfg`, direct HDC send to the ro
filesystem is avoided. An exact staged control is copied to a guarded temporary
CFG; owner/mode/label and cmp precede atomic mv. The narrow root rw remount and
EXIT trap restore original ro even on failure; originally rw stays rw. This
adapts wiki `demo_toutiao_slot.py:103-110`, not broad `hdc remount`. Real-shell
host tests execute that trap/copy/mv logic with an isolated mount recorder and
substituted privilege tools; they are not a physical mount/SELinux proof.

Rollback never reenables the unsafe original CFG. It retains the exact backup
and installs an inert jobs/services-empty quarantine. Ordinary controls are
restored by SHA and metadata; verified own additions are removed only when
unmounted. Rollback is idempotent. Candidate boot/state/log directories and
stop evidence are retained, never recursively erased.

A candidate supervisor stops **cooperatively**: read its lock, verify exact
PID/birth/boot, root UID, shell executable path and SHA of exact NUL-delimited
argv; repeat birth after the read, then create only the new candidate's stop
flags and wait boundedly for exit. No signal is sent. Wrong identity or continued
life refuses further restoration and preserves the app. Missing board `tr` is
irrelevant: neither `rb_script_signal` nor name-based kill is called; strings
is used only for the separately guarded environment fields, never exact argv.

## Durable init startup, not an expiring install attempt

Installation/rollback tickets bind current boot+expiry. In contrast,
`startup.env` is an immutable, separately approved configuration whose SHA is
pinned in `startup.expected.sha256`. It contains no today's boot/PID/WID or
short-lived expiry. Default is PENDING/disabled/NONE. `prepare.py` copies a new
package and verifies an explicitly supplied startup-config SHA; it neither
signs nor calls devices. Outer reviews the resulting complete plan, then pins
the separate installation authorization. Changed controls require a new package.

The cfg retains proven root/setuid/su, no restricted ambient caps, DUMP, and adds
CAPTURE_SCREEN in both permission and permission_acls. The historical permission
failure is in wiki `seal-routeb-autostart-chain-scan.md:92-94`; adding the cfg
fields is not proof of a newly granted live native token or successful capture.
The existing U13-ready condition starts the new entry after each boot, not the
old destructive overlay. Bootstrap reads the current kernel boot, verifies
member bytes and creates an independent per-boot directory. Existing attempts
are not reset. Any candidate stop, including one from an earlier candidate
boot, blocks later starts. The historical operator45 stop remains SHA-bound.

Entry checks a pinned real-decoder JPEG fixture **before** any parent/child
launch, then waits persistently for the human foreground host tap. It checks
stop and boot every wait cycle; unknown UI never triggers input. Virtual601s
first-tap and two-kernel-boot tests use the same immutable config without a
postboot Mac ticket. Their explicit endpoint/tool/path substitutions are not
hardware UI proof. Watchdog restore attempts remain3. Existing socket without
an approved owner is refused, never adopted or killed.

The new bounded parent helper accepts a freshly verified numeric WID from the
wrapper, removing the old second unbounded WMS polling loop while preserving
run-template WID update and the real namespace/spawner invocation. Foreground
reads are bounded2s, birth wait1s, socket wait2s; accepted R1's15s envelope is
unchanged. No nested timeout is added around a launched spawner. Parent/WID
checks use proven board-side strings, require exactly one complete WID and UID
field, and repeat identity. Entry clears inherited child/parent attach seams,
sets real /proc, exact runtime/stage/socket and explicit attempts/polls.

## Actual decoder evidence and limits

Local source `src/stb_image.h` (v2.27) comes from
`$HOME/orca/19.53_RunTime_AonB/gfxstream/third-party/stb/include/stb/stb_image.h`;
base pixel predicates came from enginecheck48 `screen_gate.c`. The actual
snapshot_display1af5524c and PNG-only screen-gate808f58a1 were read locally from
outer's captured binaries. `build.sh` records a real second build, byte-identical
afd072, rather than inventing logs for the initial unlogged build.

`src/screen_gate_feed.c` / `payload/screen-gate-feed` / `build-feed.sh` produce
**a0f5f55472e93338b490b89226aaf0436ee65b45191ce6f9f54be869781867fb**.
It preserves privacy/login precedence and adds conservative banner/search/
recommendation/home-icon/article checks for historical screenshot61. The old
white point(100,1800) landed on gray author text; x120 missed the red home icon.
No global threshold is relaxed. `evidence/feed-real-samples.json` pins7 real
historical host-decoded samples: feed/privacy and5 unknown negatives.

Outer independently checked ARM on spare5ea in
`benchmark/2026-10-12-recovery-classifier-probe/{results.json,feed-revision/results.json}`,
master8a4a07085. This closes tested format/ABI and historical predicate evidence,
**not fresh screenshot acquisition, new recovery UI, refresh/article or sealing**.
Sources and full external SHAs are catalogued in `sources.json`.

## Usage, verification and remaining external acceptance

```sh
python3 benchmark/2026-10-12-recovery-executor/executor.py
# Only after outer has supplied/pinned a new durable config and plan:
python3 benchmark/2026-10-12-recovery-executor/prepare.py \
  --out /tmp/recovery-reviewed-package \
  --startup-config <outer-reviewed-startup.env> --startup-config-sha256 <sha>
# Explicit placement; no automatic reboot/acceptance:
python3 /tmp/recovery-reviewed-package/executor.py --plan <complete-plan.json> \
  --execute --authorization <outer-ticket.json> --authorization-sha256 <sha> \
  --out <fresh-transaction-directory> --action apply
# Rollback uses the same plan/backups and a fresh current-boot rollback ticket:
python3 /tmp/recovery-reviewed-package/executor.py --plan <complete-plan.json> \
  --execute --authorization <outer-rollback-ticket.json> --authorization-sha256 <sha> \
  --out <same-transaction-directory> --action rollback
```

Rollback after a reboot binds `boot_id` to the current boot and
`origin_boot_id` to the plan's original boot. Scope remains61b20-key plus existing
5cd128 comparison, without Boat. No source test substitutes for visual signing.

Raw new tests are `evidence/transaction-revision/test-{0,1,2}.*`:13+6+6=25 methods,
all exit0. These cover real-file CLI hashes, wrong bindings, partial sends,
unknown/drifting state, backup prechecks, null metadata, mkdir no-op recovery,
CFG ro/rw/failure, exact cooperative identity, durable boot and late first tap.
Rust4 selectors and agent-spec4 scenarios+boundary pass; score1.0 with7 lint
notices retained in `evidence/lifecycle-final-output.txt`. No accepted R1 suite
was rerun. The unrelated arsc modification is excluded.

Outer reports that BMS logic, CFG and late-first-tap checks passed. Release
inventory verification, execution authorization and device acceptance remain external. Per outer's
responsibility split, fresh preboot snapshot/sepolicy/one reboot, postboot t7
adapter (master8a4a07085), legacy acceptance and20-key scheduling are **outer-owned**,
not missing executors to reinvent here. Legacy seal-provider UI signatures use
literal outer(claude); this new install authorization uses outer(codex). Neither
is fabricated or silently substituted. Default package remains disabled until
outer review and real acceptance.

`checkpoint-manifest.json` is the current release inventory. The old70b inventory
is retained only as historical `evidence/checkpoint-70b6-manifest.json`.
`evidence/release-byte-identity.json` compares every executor/prepare/payload byte
with b093; this release changes metadata and receipts only.
