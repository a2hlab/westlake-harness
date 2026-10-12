# T4 integration checkpoint: disabled, not admitted

## Evidence and decision

R2 accepts only frozen watchdog9763171a and helper80a263d9 from commit
c014f86102f55b51033a0e5032c90ab4af089d09 in its isolated control-safety scope.
The actual T4 draft is a different package under
`$WORKSPACES/westlake-harness-t0/benchmark/2026-10-12-toutiao-recovery-integration/`.
`evidence/t4-first-inputs.json` pins 27 observed files and independently checks
16/16 bound source SHAs. This is an editing checkpoint, not a frozen release.
All references below are relative to that T4 directory. Nothing was deployed
or run through a board/VM/remote transport.

Default `preview.py` contains no device executor, refuses execution or supplied
authorization, and reports pending dependencies. `payload/entry.sh` is disarmed
by `authorization.expected.sha256=NONE`; the unsigned attempt has null boot,
UID, plan and outer signature. This is the correct current safety state.
**Final T4 acceptance remains pending.** No fixture result proves a real UI,
automatic recovery or seal. Plan-2 remains 61b local20-key plus existing5cd128
cross-comparison, not a new61b128 run.

The audited pure-Python preview was run locally: default rc0/pending/zero
device calls; `--execute` rc2/REJECT/zero device calls. Its complete original
output is `evidence/t4-preview-only.txt`. No shell launch wrapper was executed.

## Concrete integration checklist for t0

| ID | Observed current draft | Required closure before a frozen acceptance |
|---|---|---|
| T4-01 JIT | `spawn-prepared.sh:14-20` checks JIT SHA and restores the original8-second nsenter preparation before host_spawn, rechecking parent afterwards. This closes the earlier omitted-JIT design gap. `sources/prepare_jit50.sh:5,14-17` still has donor UID20010053 and mutates only code-cache ownership/mode. | Bind the effective UID-reconciled JIT bytes and cache label/readback; require exact physical and parent-namespace JIT file identity, not just physical SHA plus a hardcoded `/data/local/tmp/asx` command. Record JIT stderr/rc. Do not execute it during this review. |
| T4-02 HERE and aliases | `bindings.json` names root scripts/watchdog and a new-attempt watchdog, each with a HERE helper path. Accepted watchdog sources HERE/route-b-owner.sh but uses F/start-parent.sh, F/spawn.sh and F/screen-gate. `spawn-prepared.sh` in turn sources its own HERE/launch-common.sh and HERE/real-spawn.sh. | Exact placement must bind all these destination files, mode/owner and SHA, not merely the two watchdog names. Do not leave root alias using old F by default. Bind the actual caller to entry.sh and explicit TT_STATE_ROOT. The old operator F/watchdog reference needs an explicit retained/inert disposition; do not rewrite it implicitly. |
| T4-03 environment | `entry.sh:33-35` exports execute/boot/UID/state/parent tuple, but not TT_RUNTIME, TT_STAGE or TT_SOCKET; accepted watchdog therefore takes its baked defaults. `spawn-prepared.sh` reads AUTH_RUNTIME/STAGE/SOCKET while `real-spawn.sh` has captured absolute stage/socket constants. | Either assert every authorized path equals the captured constants or export and verify one coherent route. Explicitly pin PROC, tool PATH, current UID/GID, attempt/poll envelope and parent role/birth. Do not accept an authorization for one route and execute another. |
| T4-04 real launch and attach | Entry requires an existing exact parent tuple. The real parent script is byte-identical to the capture; it polls a host WID, can continue without one, rewrites run.sh and uses UID20011206. Runtime template still has owner20010053 and WID1443. No actual parent preparation/foreground gate is wired by this checkpoint. | Keep attach-only entry if intended, but provide the separately reviewed parent preparation order: current host foreground -> strict numeric WID -> effective UID/run readback -> private source_app_namespace -> exact parent/socket -> JIT -> host_spawn. Test missing WID/helper/JIT/socket using real scripts with external effects mocked, not parent_tool/spawn_tool. |
| T4-05 integrity and classifier | Preview validates16 source records, not the new payload wrapper bytes, effective placement or attempt JSON. Entry checks an authorized candidate SHA string, not the on-disk watchdog/helper hash. Candidate captures JPEG; the screen-gate source is bound but its decoder contract is pending. | Pin the finalized wrappers/placement/plan, verify live destination bytes before execution, require actual JPEG decoding/labels on an existing local frame or isolated format fixture, and reject non-UTF/tool failures. `AUTH_CAPTURE_FORMAT_VERIFIED=yes` alone is not the evidence. |
| T4-06 stop/data/rollback | Entry explicitly requires retained old-stop SHA and separate authorization before the new state root. This is preferable to a blind old-overlay rerun. Preview rollback is a generic string, not an exact backup/restore manifest. | Preserve original stop, raw run, logs and data. Record an explicit outer new-attempt decision, not a hidden F change. Supply exact destination backup SHA+metadata and candidate-only supervisor identity; no app/U13/parent signals, no automatic restart of unsafe old watchdog. New attempt/signature/no_mac_repair are fresh, never inherited. |

Required real caller tools include sh, dirname, cat, cut, wc, tail, sed, stat,
readlink, sha256sum, cmp, timeout, nsenter, snapshot_display, screen-gate,
hidumper and the foreground-host provider. The helper's `tr` is relevant to
any proposed rollback supervisor signal; it is not called by the accepted
watchdog's no-signal monitoring path. Missing tr cannot justify a name-only kill.
No real-domain tool or permission success is inferred from Mac fake-proc tests.

The bindings correctly distinguish archived source_app_namespace/host_spawn/
request.bin bytes from live reconciled bytes. Effective request UID/GID, socket
identity and actual runtime dependencies remain pending; copied archive files
do not close them. Frozen package tests, concrete restore receipt and new
authorization are not yet present in this observed checkpoint. Re-review the
next immutable T4 SHA rather than silently extending this checkpoint's result.
