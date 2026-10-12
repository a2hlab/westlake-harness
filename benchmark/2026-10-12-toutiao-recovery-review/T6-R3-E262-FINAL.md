# R3 activated selfcheck: final narrow review

## Evidence and verdict

**OFFLINE CODE RELEASE ACCEPT. Actual successful placement history also binds
locally with exit 0. This is not a device selfcheck, UI result or seal signature.**

- Freeze: `e262c89986aa80c0aed9254a1c5cb24cf46cc7e562b6490dfefa2cfee2eebb58`.
  **10/10** physical SHA/size rows and **12** landing paths close exactly.
- selfcheck.py: `2537f4422f544b2831388a95968336e933cd00ecd706951deb849cb3b1740b6c`.
- build_binding.py: `8f8b1553eff79d934383f62e014c5a5869d98f533f8fe8da972b1e1a67594367`.
  Both are byte-identical to the independently checked preview.
- Independent narrow preview: **8/8**, exit 0; apply argv shape and early refusal
  of interrupted/timeout/bool/failed parent outcomes. No successful synthetic
  transaction was claimed by those checks; no old 39-case matrix was repeated.
- Independent real-history build_binding CLI: **exit 0**, using main's actual
  successful r2 transaction, admission, prepared manifest and origin proof.
  Output binding SHA:
  `b6a0e01ca3c20dde019219f7251998f314fc12a66a0e3ec81c0d9a957591ca68`.
  Python audit rejected subprocess/process execution; no transport/device/lock
  tool or executor was called. Raw stdout and generated binding are included.

## Strict activation/history path

The checker reproduces original prepare/checked_package and checks the exact
enabled package, original executor496fa, identical 487 target set, preimages,
metadata and plan context. Only the two complete hashes of startup.env and
startup.expected.sha256 differ from disabled expectation. It replaces precisely
those two expected hashes before the independently evidenced WID derivation;
there is no ignored-file list or loose hash exception.

Actual history requires exact executor_rc0/apply, proof/source/manifest/plan,
reviewed adapter, historical admission and authorization roles/bindings,
transaction origin boot/serial/487 backup rows, every named placed-000..486
target/SHA receipt, final exact PLACED_ONLY and no failed/rollback journals.
The completed main r2 objects satisfied this path in the independent local
builder invocation. Expired historical admission is audited, not renewed
execution authority; the original lock tool is pinned but never invoked here.

The outer's actual process exit0/duration809.23s is outer-reported evidence;
the independently executed local builder verified the resulting actual
executor_rc0 receipt and all 487 tickets. It does not retroactively execute a
placement or issue a new authorization.

## Final seal/appendix boundary

verify_appendix preserves all original candidate targets, requires equal
placement parameters/prepared bytes and authentic original seal identity, pins
both proof objects and original appendix generator, and checks the exact entire
final target map. Extra static rows require no edits and template==target SHA.
The original full seal package/system/inventory checks remain in comparison.
Thus the five added static files are not excluded from actual readback.

Producer's eight targeted synthetic tests include five extra static targets
and appendix drift refusal; those remain producer evidence. **This independent
actual-history binding is candidate-only, without an appendix:** the final real
seal and its additional static rows must be supplied/pinned for the final seal
entry. We do not claim that missing final-seal work is already complete.

## Concrete next entry for outer

Use the generated independently pinned binding (candidate-only), or generate a
fresh final-seal binding with the exact appendix/final proof when available:

```sh
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-exact-realization/r3-activation-selfcheck/selfcheck.py" \
  --activation-binding "$ACTUAL_BINDING" --binding-sha256 "$ACTUAL_BINDING_SHA" \
  --serial 5cd1e3dd00000000000000000923012c --boot-id "$INDEPENDENT_CURRENT_BOOT" \
  --hdc "$EXPLICIT_HDC" --out "$FRESH_SELF_CHECK_RECEIPT"
```

Only outer may run the shown live read-only collector. Offline observed input
remains OFFLINE_MATCH, never live PASS. New kernel boot/WMS/proc/HAP identity
must be independently observed; no WID is accepted from run.sh itself.
Preboot's 57-baseline label gate plus existing authorized label supplements is
not widened by this review. Original raw evidence and candidates remain intact.
