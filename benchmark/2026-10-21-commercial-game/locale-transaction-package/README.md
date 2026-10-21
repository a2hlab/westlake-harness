# G32: unsigned locale ABI transaction inputs

G27's historical source profiles did not bind its repackaged manifests. This
package starts from G28's source-bound assembly and preserves its actual source,
artifact, namespace-owner and configuration relations. The 15 candidate profile
identities bind the new manifest; the 15 baseline profiles remain unchanged.
ABI provenance is a separate exact G30 source/build binding, not an invented
namespace or JNI initialization profile.

The actual original U7 preparation returns **319 targets, 6 logical changes,
36 writes, 30 writes with unchanged SHA, no additions**. The complete baseline
and historical G28 direct319/parent319 restoration and Boat3 evidence are retained.
The candidate keeps G26 host ee5649 and ANL640b, and G24 policy878c. Only one
additional target changes:

| ABI target under `/system/android/lib64/` | Baseline | Candidate | Consumer/source evidence |
|---|---|---|---|
| `libwestlake_native_abi.so` | d2053066 | d2053066 | No direct DT_NEEDED in99 package ELF objects; other dynamic consumers unknown |
| `westlake_flutter/libwestlake_native_abi.so` | d2053066 | d2053066 | Existing host explicit Flutter-domain load |
| `westlake_native/libwestlake_native_abi.so` | d2053066 | 4296f805 | Existing host explicit native-domain load; user-selected replacement |

All hashes are complete in `current-abi-aliases.json`. Host source lines350–352
select the two private paths and call the existing `dlopen_ns` operation.
The99-object scan found zero direct DT_NEEDED consumers of this SONAME; this does
not mean no consumers. The existing32-game-ELF evidence supplies24 locale import
rows. Actual runtime namespace relocation/provider selection remains unverified.
No new namespace, search root, GLOBAL operation or runtime source was added here.

## Exact accepted inputs

The outer receipt `$COMMERCIAL/g30-package-acceptance-01/acceptance.json` has status
`ACCEPTED_FOR_OFFLINE_UNSIGNED_ASSEMBLY_ONLY`. All20 pins (SHA and size) and all55
current build inputs were checked. Assembly consumes candidate-02,41984 bytes,
SHA `4296f8052b6ccc130df83366717903695eba38fcde19c462ee64521414696f0b`.
Acceptance binds actual candidate/baseline sources, scripts, two input snapshots,
completed build receipt, function/preservation evidence and independent ELF
review. G30's longer public report is supplementary and was not substituted for
those inputs. No compilation was performed here.

`$WORKSPACES` is the workspace parent; `$COMMERCIAL` is
`$HOME/.local/share/westlake/commercial-game-20261021`. The private new package is
this directory's `.private/assembly-01/{baseline,candidate}`. Source is the t37-peer
`native-route-admission/.private/assembly-01`, pinned by main G28
`native-route-admission/public-v2` (89 input pins checked). The original assembler
pattern and main `u7_executor.prepare` are reused; deployment tools are unchanged.
`assembly-command-01` holds argv/stdout/stderr/rc. First-slice13 files remain fixed
under `first-slice-01`; they describe the earlier pending state, not current status.

## Actual original checks

| Entry | Result |
|---|---|
| U7 prepare | rc0;319 targets/6 changes/36 writes |
| U7 complete dry-run | rc2, stopped at static checks |
| generation_static_checks | rc2; two ANL namespace reviews required |
| native_predeploy baseline | rc1; N1 55/N2 104 rejected,0 excepted,no invalid-input errors |
| native_predeploy candidate | rc1; N1 55/N2 104 rejected,0 excepted,no invalid-input errors |
| check_frozen both packages | rc0 each |
| G1/G2 | Not reached; no VM/wrapper invocation |

`findings.unsigned.json` is generated from this run:318 native rows and2 static
review rows. The numerical match to historical318 is not approval reuse. Each
row binds current manifest/inputs and relevant profile identity or object hashes.
The native-domain ABI changes bytes even when a finding's text is unchanged.
The registry is read unchanged; no old window signature is copied or issued.
Raw complete native/stdout/stderr remain in `.private/gates-01`, SHA-indexed in
`evidence-index.json`; large output is not duplicated into public delivery.

Original complete preflight remains refused. Outer review of exact new inputs,
new signatures and subsequent complete preflight are pending. If Linux image
checks are needed later, the outer loop must use its existing wrapper/environment;
this task did not compete for a VM. Historical recovery evidence is not a new
fresh-device check. `rollout_ready=false`, `deployable=false`; no device, journal
ownership, game launch, runtime build, exception signing, or push occurred.

## Recheck

Run `python3 check_receipt.py --private` in this directory to rehash private
payloads/evidence and compare the original U7 plan. Without `--private`, the
checker validates the portable delivery plus four rejection cases: missing
acceptance, non-selected alias drift, source-profile manifest drift and a false
readiness claim. The Rust selector invokes that same offline checker; validation
receipts record actual results. No runtime code is built by the Rust selector.

`prepare.py --workspaces "$WORKSPACES" --acceptance
"$COMMERCIAL/g30-package-acceptance-01/acceptance.json" --out <fresh-card-private-dir>`
repeats assembly only. `run_checks.py --main "$WORKSPACES/westlake-harness"
--assembly <assembly-dir> --out <fresh-card-private-dir>` invokes unchanged original
gates and persists outputs. It never requests a VM or device. Old evidence and
first-slice metadata are preserved. Shared refs are known read-only; no repeated
Git/board write was attempted. Land only `landing-paths.txt` through the outer loop.
