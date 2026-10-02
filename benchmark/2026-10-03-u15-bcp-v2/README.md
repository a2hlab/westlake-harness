# U15 double-BCP rebake preparation (execution disabled)

## Correction and evidence

The previous `2026-10-03-u15-plan` selected framework alone. Outer ACK(90)
07:23:43 added NSD stubs, so its one-swap contract is historical, not silently
relaxed. This separately versioned plan selects **framework9e55 + stubs94a9**
in one complete FZ-005 bake. Nine local JAR snapshots are hash-verified; **no
new image, remote command, compiler invocation, VM access or board operation**
has occurred. Gate registry and gate code are untouched during window4.

- `plan.json`: ordered nine inputs, full candidate/U14 hashes and source paths.
- `input-inventory.json`: persistent local snapshots under this worktree's
  `.artifacts/inputs/jars9/`; binary JARs are deliberately not landing files.
- `inputs/jars9.sha256`: exact candidate map; seven hashes unchanged.
- `expected-images.{json,csv}`: full 27 targets, all candidate hashes unknown.
- `source-snapshots.json`: original and portable snapshot hashes, donor source
  receipts and live-build logs. The six NSD release files were checked against
  their own SHA256SUMS; donor two-build identity is their reported result, not
  a build performed by this lane.
- `native-slots.json`: references the previously handed-off native partial;
  newly arrived Flutter9b824 is explicitly uncomposed here. Its target is
  only `westlake_flutter/libandroid.so`, never the native-domain alias.

Effective U14 content bases remain common9b42 and 61bf589, with installers2c9a
and 51e1 respectively in both system locations. These are content identities,
not promotion claims. `transaction-base.template.json` stays unbound. Runtime
JAR0349 is unchanged and **outside BCP**; native runtime94c3 is a different file.
On eventual assembly update both the native framework/stubs underlay and the
effective framework overlay, plus the complete paired image group atomically.

## Full image group and validation

The modified stubs and framework segments forecast six changed members;
fourteen other ART/OAT members may change, and seven unchanged DEX VDEX
members are forecast identical. **6/14/7 is a forecast, not a measured count.**
All 27 images must be built on both runs. Do not bake only the six segments.

Fresh Mac class comparisons are recorded verbatim in `evidence/`, with
original raw SHA/argv/exit codes in `static-input-checks.json`. The NSD comparison
uses only its eight exact added classes as a proposed allow list, not an outer
signature. Framework DEX UTF8 decoding failure remains unknown; donor shape
or verifier results are not substituted for fresh production PASS.

`paired-receipt.template.json` contains both input maps and 27 null outputs per
run, null actual argv/toolchain/hostlib/log identities and null return codes.
After execution bind actual argv, compiler/driver hashes, compiler log and
session log hashes, hostlibs inventory hash and compiler/tee/session/script
statuses for **each** run; compare all outputs. Driver rc6 only records mismatch
against the historical U14 image reference; it is not production admission.
Fresh G1/G2, RB, T4b, image reproducibility and paired receipt are still required.

**Do not transfer U14/T7d boot.art nondeterminism approvals.** Both changed
inputs form a new input/output pair. If images differ, retain byte ranges and
obtain actual frozen-oatdump object-chain evidence for a new outer decision.

## Executable handoff, only after separate outer authorization

The approved target is SSH alias `hw248`, actual host **ecs-9f6c**, Linux
x86_64. Explicit `HW248_HOME` must match the FZ-005 home identity hash; it is
not inferred from the SSH account's HOME. Frozen compiler ae865 and driver14b1
are checked in the wrapper; the repository driver has a different hash and is
not a substitute. The plan includes the historical frozen hostlibs inventory;
each future run must freshly match it and run2 must match run1.

Stage this packet to `$HW248_HOME/u15-bitmap-nsd-9e55-94a9-v1/plan/` and the
hash-verified local nine JARs to the sibling `jars9/`, using the operator's
approved transfer mechanism. This **new root** avoids old framework-only runs.
Verify `inputs/jars9.sha256` on the remote snapshot before granting execution.
Do not transfer `.artifacts` wholesale or reuse prior `run1`, `run2` or logs.

Only after outer explicitly authorizes this exact plan/input set, on hw248:

```sh
export HW248_HOME="$APPROVED_FZ005_HOME"
export U15_PLAN_EXECUTE=outer-approved-hw248-only
ROOT="$HW248_HOME/u15-bitmap-nsd-9e55-94a9-v1"
bash "$ROOT/plan/planned-bake.sh" 1
bash "$ROOT/plan/planned-bake.sh" 2
```

Without that explicit execution switch the script exits **78 before any
machine probe**. Both builds reuse the same `work/` path; completed output groups
go to distinct `run1/` and `run2/`. Live compiler tee and whole-session tee,
argv JSON, tool hashes, OS identity, hostlibs inventory, output checksums and
all return codes remain under that persistent root. Run2 rejects incomplete
run1 status. Existing output/logs and symlinked roots are rejected.

Return the two complete image groups and original logs/status/argv/checksums
to `$WORKSPACES/westlake-inputs/generations/u15-bt-bake-9e55-94a9-v1/`.
Do not truncate or concatenate failed logs. Keep failed attempts as evidence
and use an independently reviewed fresh staging root for any retry.

## Local checks and landing

Run `python3 test_plan.py`, targeted Rust selectors `u15_bcp_v2_inputs` and
`u15_bcp_v2_recipe`, and both fresh spec lifecycles. Cold tests need only the
landing files, not `.artifacts` or another worktree. `documentation.json`
contains incremental Layout/DIGEST snippets for the outer; root documents and
active gates are not landing files. `landing-paths.txt` plus preflight is the
handoff; this plan grants no build, production or deployment authorization.
