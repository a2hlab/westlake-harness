# T4 handoff to cx-t0: one consolidated wiring correction

## Scope and evidence

Receiver: **cx-t0**, with outer(codex) reviewing. This supplements, never edits,
the52-file final R2 landing set (SHA197a9d4fa277e45e4d0fb65d280c731c53d15b2ca9e92b63249baadd4ff7d81e).
`evidence/t4-handoff-inputs.json` pins20 actually inspected integration files,
16/16 current member-layout SHAs and all52 original R2 file hashes. No candidate
tests were repeated, no launch/provider was executed, no board/VM/remote call
was made. This is an editing checkpoint, **not acceptance of an editing SHA**.
Paths below are relative to t0's integration directory unless absolute.

All six earlier items have changed in part; none should be reported as wholly
unchanged. They now need a frozen package and the explicit closures below.

## Use these exact route constants and fields

| Symbol/field | Existing actual route; not a current live assertion |
|---|---|
| `AUTH_RUNTIME` / `TT_RUNTIME` / `RB_RUNTIME` | `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d` |
| `AUTH_STAGE` / `TT_STAGE` | `/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d` |
| `AUTH_SOCKET` / `TT_SOCKET` | `/dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002` |
| `AUTH_STATE_ROOT` / `TT_STATE_ROOT` (F) | `/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview` in this draft; final attempt name must be explicitly rebound |
| historical stop | `/data/local/tmp/operator45/selfheal48/stop`; preserve empty-file SHAe3b0c442..., never clear |
| caller entry | F/entry.sh with F/authorization.env, via reviewed disabled service proposal; not direct invocation of either historical watchdog alias |
| runtime namespace alias | `/data/local/tmp/asx`; JIT, run.sh, asx-spawner and native paths are views inside the exact Route B parent namespace, not proof that default namespace is ready |

The UID20011206 is a **bound draft UID**, not guaranteed current ownership.
Entry now checks installed host UID and refuses a different value. Do not
reconcile by blindly accepting a new UID: regenerate run/JIT/request bindings
and review their differences if it changes.

## Six items: observed progress and exact remaining work

### T4-01 JIT: derivation exists, namespace file equivalence still needed

`payload/prepare_jit50-uid20011206.sh` is exactly the archived ad115b0b script
with only `app_uid=20010053` replaced by20011206 (aa1234d2). Request remains672
bytes: only bytes312,313,316,317 differ, two LE uint32 fields at312/316 both
become20011206 (f871e6a1). Runtime template changes only ASX_RUNTIME_OWNER_UID
(fa075c60), preserving JIT/preload/WebView/network flags. These were mechanically
compared here, not assumed from t0's description.

`spawn-prepared.sh:26-34` now preserves guarded parent -> timeout8 nsenter JIT
-> parent/window recheck -> actual host_spawn. Before the JIT command, compare
the physical `AUTH_RUNTIME/prepare_jit50.sh` with
`/proc/$TT_PARENT_PID/root/data/local/tmp/asx/prepare_jit50.sh` by SHA and device:
inode, like the existing run.sh guard. Bind the parent-visible effective JIT
SHA as AUTH_JIT_SHA. Record original JIT stderr/rc and code-cache readback
20011206:20011206:700 plus label; do not treat ls output alone as successful
label admission. This reviewer does not authorize running chown/chmod.

### T4-02 HERE/aliases: historical pair corrected, F classifier absent

Current `watchdog_aliases` correctly names root scripts/watchdog.sh **and** old
operator45/selfheal48/watchdog.sh, plus `attempt_watchdog` separately in F.
Helpers are listed beside all three; 16 member-layout entries currently match
their source bytes. The active new caller must go through F/entry.sh so the
unchanged976 watchdog receives TT_STATE_ROOT=F. Historical direct callers must
be explicitly retained inert/disabled in the separately reviewed transition;
do not assume copying watchdog bytes redirects an old boot job.

At F, use these placements exactly:
- start-parent.sh <- start-parent-prepared.sh
- spawn.sh <- spawn-prepared.sh
- real-start-parent.sh / real-spawn.sh / launch-common.sh / route-b-owner.sh
- watchdog.sh / entry.sh / authorization.expected.sha256 / authorization.env
- **screen-gate**: source808f58a1 is recorded under external_prerequisites, but
  not installed by member_layout. Add an exact placement or exact-existing
  readback prerequisite at F/screen-gate; missing/unexecutable must refuse
  before parent/child launch, not wait until UI_UNVERIFIED after launch.

### T4-03 environment: exports fixed, constants and inherited seams still open

`entry.sh:37-47` now exports execute/boot/UID/F/runtime/stage/socket and supports
existing/new parent modes; this closes the earlier missing-export issue.
However the captured real-start-parent and real-spawn still use the constants
above. Cheapest correction: **assert AUTH_RUNTIME/STAGE/SOCKET equal those
exact constants**, rather than allowing an authorization to select unrelated
paths while the actual helper runs the hardcoded route. Pin the production
tool PATH and set TT_PROC=/proc, not a inherited fixture seam. Explicitly bind
or clear inherited TT_CHILD_PID/TT_CHILD_BIRTH and set the approved TT_MAX_ATTEMPTS
and TT_MAX_POLLS instead of borrowing caller values. Parent mode and tuple must
be fresh. Needed binaries/tools: source_app_namespace60b89e11,
host_spawn019acf9e, spawner a7a358c6, sh/dirname/cat/cut/wc/tail/sed/stat/readlink/
sha256sum/cmp/timeout/nsenter/hidumper/grep/head/snapshot_display/classifier.
Check them in the actual caller domain; archived bytes and fixture substitutes
are not executable namespace or permission proof.

### T4-04 real launch: new and existing owner flows now wired

`start-parent-prepared.sh` now runs the real captured8e1d script under the
accepted watchdog's acquired lock; checks namespace binary SHA; waits for
socket; verifies parent birth/private root/namespace; writes/readbacks
parent-identity. `spawn-prepared.sh` reads this tuple for new-parent mode.
`launch-common.sh:26-36` checks current host-window row and parent environ
WL_PARENT_ID, closing the previous stale-template-only check in source.

Keep the exact sequence: future authorization + old-stop/preimage proof ->
entry ->976 acquires and verifies lock -> current foreground imehost0/strict
numeric WID -> real run.sh update -> source_app_namespace -> socket ready ->
parent UID/birth/exeSHA/run inode/ns/current WL_PARENT_ID -> parent-visible JIT
-> checked request UID/GID and host_spawn -> child ownership -> human UI.
Existing-parent mode skips creation but retains every parent/window/JIT gate.
Use the source overlay's existing WMS field convention (fourth token=window ID,
eighth=nonnegative Z-order), not the fixture row as evidence of real WMS output.
Neither that convention nor a parent PID alone proves user foreground consent.

One envelope to resolve before freeze: unchanged976 times start-parent.sh out
after15s; real helper can wait20*.25s, wrapper birth20*.1s and socket40*.25s
(up to17s of waits plus tools). Reduce the wrapper's combined budget below15s
with reserve, or explicitly demonstrate the bounded applicable path. Do not
modify accepted976, silently extend the old10800s driver, or kill a parent
already started if a wrapper times out. Driver budget and long-lived guardian
observation are separate; state RETRY_LIMIT/IO_FAILED is not UI or seal success.

### T4-05 integrity/format: payload hashing improved, real decoder still pending

Preview now verifies member-layout bytes. Entry hashes HERE helper/watchdog,
wrappers rehash authorization and expiry/boot, and missing-format flag refuses.
Do not drop these improvements. Frozen placement must also pin every wrapper,
classifier destination, finalized plan/attempt and service routing. Validate
the actual watched bytes match976/80a, not merely two independently supplied
authorization strings.

Current classifier_static reports libpng `png_image_*` imports and explicitly
`jpeg_verified=false`; unchanged976 captures JPEG. An `AUTH_CAPTURE_FORMAT_VERIFIED=yes`
fixture is **not** decoder evidence. Wait for a separately reviewed compatible
classifier/capture path with exact bytes, labels and local/board verification
scope. Do not rename JPEG to PNG or declare CAPTURE_SCREEN resolved from this.

### T4-06 stop/data/rollback: disabled proposal exists, preimages pending

Service proposal has no jobs and execution_enabled=false; unsigned binding is
NONE. New-plan draft explicitly preserves stop/data and requires exact backup
SHA/mode/uid/gid/label/absent before writes, avoiding blind overlay rerun.
Keep this conservative default. All16 member preimages remain unbound: supply
the real backup/readback manifest and exact future change/rollback mapping;
restore only reviewed control bytes, never automatically restart unsafe donor.
Any supervisor-stop permission must be separately authorized and tied to its
PID/birth/boot/UID/exe/argv, never a parent/U13/app name. Preserve historical
stop and logs; state-root independence requires explicit outer authorization,
not an implicit stop bypass. All current plan/boot/signature nulls are pending,
not missing strings to invent. Plan-2 stays61b20-key + existing5cd128.

## Wait for these specific artifacts, not polling

1. Immutable T4 commit/list and source SHAs, incorporating the wiring above.
2. Effective JIT/run/request derivation + parent-visible identity contract and
   live prerequisite/rollback readback requirements, with failure-path fixtures.
3. Exact compatible screen-gate placement/decoder proof; until then disabled.
4. New plan/service/placement and preimage restore manifest, explicit old-stop
   decision and future outer authorization (not supplied or signed by BMS).

The existing7-test output was read, not rerun. It explicitly substitutes native
helpers, identity, foreground row and classifier; it is useful source-order
testing, not board admission. Final independent review begins only on the
immutable package, not on these editing hashes. No continuous polling follows.
