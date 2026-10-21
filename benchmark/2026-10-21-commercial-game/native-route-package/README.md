# G27: unsigned native-route transaction inputs

G20's assembler only changes two policy targets. Selecting replacement libraries
by basename also catches the old 74e6 route in the real 319-target baseline.
The first G27 attempt refused that cardinality; its output is preserved.
The successful fresh assembly explicitly selects system plus current 74d1 aliases.
No deployment tool, source artifact, registry or signature was changed.

The actual package is `$G27/.private/assembly-02/{baseline,candidate}`.
`$G27` means this directory in the isolated worktree. Both sides contain 319
expected targets. The original main `u7_executor.prepare` produced **35 writes,
30 with unchanged SHA**, and exactly these five logical changes:

| Targets | Baseline | Candidate |
|---|---|---|
| /system/bin/appspawn-x | 2a87118e | ee5649f2 |
| ANL system + current74d1 route aliases | eebd62f2 | 640b3c87 |
| policy system + current74d1 route aliases | b8be63d2 | 878c7019 |

Full target names and SHA values are in `five-targets.json`. All historical74e6
members remain unchanged. G18 policy878c is retained as the G24 atfork control;
G26 is layered on that control. Host646840B and ANL60208B are independently hashed
against their original completed receipts. The outer loop subsequently confirmed
both exact baselines, candidate build rc0, unchanged exports/DT_NEEDED, actual
production ANL37 + host50 checks for each version and the permitted-only control.
That confirmation is recorded separately from the initial pending assembly.
The final G26 public landing index is still awaited; no build was repeated here.

## Original checks and current blockers

| Check actually run | Result |
|---|---|
| Main original U7 prepare | rc0; 319/319, 5 deltas, 35 writes, no additions |
| Main original complete U7 dry-run entry | rc2; static five-target review rejected |
| Original native_predeploy, both packages | rc3 INVALID; N1 historical host profile binding refusal |
| N2 from those runs | each104 rejected,0 excepted; old assumptions, not current acceptance |
| Original frozen package checks | both rc0 |
| Local package consistency +3 refusal cases | PASS; missing host, alias drift, old-route mutation refused |
| Rust selector | PASS:1 test,0 failures; no runtime rebuild |
| agent-spec lifecycle lint/boundary only | 3 scenario SKIP; not contract acceptance |

The complete dry-run stopped before G1/G2. Neither was rerun separately or claimed
passed here. There was no VM/device command, timeout retry or permission change.
`gate-commands.json` records exact sanitized original argv; the original records,
stdout/stderr/rc remain under `.private/gates-{u7,native}-01` and are SHA-indexed.
Large native findings/stderr are not public copies.

The static policy is a new empty unsigned policy. G24 window exceptions and
signatures are not reused as authority. Both bundle and native manifests set
`rollout_ready=false`; no current gate ticket or owned transaction state is made.
Historical profile files are retained unchanged and **not relabelled** as current
source attestations. N1 therefore refuses even the repackaged baseline; N2's104
historical findings likewise need a new exact review. Native artifact owner hashes
are rebound to actual input bytes, which is not source attestation or approval.

`host-binding-review.json` records the actual code locations: U7 `_bind_start`
binds the explicit side's package/manifest/ticket and host; original
`Deployment.start(digest)` applies the original label recipe and compares the
live parent against that digest. No hardcoded old-host check was found there.
The real blocking old-host binding is the N1 historical profile check at
`native_initialization_gate.py:33`. This card does not modify it or manufacture
current evidence to satisfy it. Outer review must bind current G26 sources,
manifest/inputs, namespace deltas, exact exceptions and signatures separately.

## Recovery and freshness

`baseline-319.json` is the complete recovery map. Eight actual G24 closure hash
outputs were parsed and match every target, not just a reported count.
`recovery-binding.json` retains Boat3 hashes and the original boot identity.
These are historical closed-window evidence, not new device readiness. Outer
reported fresh same-boot parent4331/birth1279054 with baseline host2a871 and no
test children; complete direct319/parent319 capture is MATCH with0 mismatches in
`$COMMERCIAL/g27-outer-fingerprint-01/results.json` (21:29:30.466874+08:00).
This external read-only receipt is not promoted to deployment admission. No old journal ownership is invented.

`package-index.json` binds both complete bundle/native/input manifests by SHA.
`transaction-plan.json` includes the actual35 write members and both319 maps.
Raw package bytes stay private. `source-index.json` binds original G26 receipts,
G24 closure and original tool sources; `evidence-index.json` pins command outputs.
All public paths are aliases; originals remain untouched.

## Reproduce or review without builds

From this directory:

```sh
python3 check_receipt.py --private
```

The checker rehashes the indexed originals and all590 native package members.
Without `--private`, it checks the portable delivery and three rejection cases.
It validates unsigned consistency only; it cannot turn the rejected original
preflight into approval.

`prepare.py --main "$WORKSPACES/westlake-harness" --commercial
"$HOME/.local/share/westlake/commercial-game-20261021" --g26
"$WORKSPACES/westlake-harness-t4/benchmark/2026-10-21-commercial-game/native-route-candidate"
--out <fresh-card-private-directory>` reproduces the initial pending unsigned
assembly using G20's clone/rebind method and unmodified main U7. It never executes
legacy stage/main, builds or devices. Output must be fresh. Subsequent outer G26
acceptance is evidence in this delivery, not an approval generated by the recipe.

Branch creation `analysis/g27-native-route-package` failed rc128 because shared
refs are read-only. Original stderr is preserved in `.private/git-branch.stderr`
and sanitized in `failures.json`; no retry, commit, board write or push followed.
The outer loop lands the fixed `landing-paths.txt` list. G14/T38 remain stopped.

The initial lint/boundary-only run and its3 skips are retained. After the outer
clarified that Rust acceptance builds are allowed, the exact G27 Rust test ran
and passed; this supersedes NOT_EXECUTED for the selector, not the native gate
rejections. No runtime object was compiled.
