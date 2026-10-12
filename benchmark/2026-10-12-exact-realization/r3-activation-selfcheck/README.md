# Activation-aware read-only selfcheck

The frozen placement proof describes disabled startup bytes. Comparing those bytes
with a successfully activated package would reject the two intentionally enabled
startup files. R3 verifies the original proof and a completed activation history,
then compares the exact activated SHA values. It does not weaken the original
proof or modify any frozen source.

**Actual successful execution is not established by this deliverable.** The old
900-second attempt ended with executor_rc=-15 and is rejected. The r2 execution
must finish with rc=0 and all 487 original placement receipts before a binding can
be built. All positive transaction histories in the tests are explicitly synthetic.
No device, executor, production lock, or restore command was run by these tests.

## Evidence boundary

* Pin the checker, frozen seven modules, origin/final proofs, prepared manifest,
  admission, exact old/r2 restore adapter, parent execution receipt, transaction,
  completion, and each of 487 member receipts independently.
* Recompile the origin proof with its own pinned generator location and identical
  frozen dependency bytes. Reproduce the activated package with frozen `prepare`
  and `checked_package`. The disabled and activated plans have identical 487
  targets, sources, before images, and metadata. Only `startup.env` and
  `startup.expected.sha256` have different SHA values; execution_enabled changes
  from false to true. Every other plan field remains equal.
* Require parent executor_rc=0, exact executor argv and authorization SHA, full
  admission target map, origin serial/boot, and each numbered placed receipt.
  Verify preimage backups against the unchanged plan. Reject failed or rolled-back
  transactions. Pin historical lock_tool bytes, without invoking the tool.
* Admission expiry is recorded as historical evidence only. It creates no new
  authority and does not permit replay. The current boot may differ from the
  placement boot. Independent boot/UID/GID/HAP/proc/WMS readings establish current
  host identity and the single dynamic run.sh window ID.
* A final seal appendix must bind the same candidate proof, unchanged existing
  targets, identical prepared manifest and parameters, and the exact additional
  static files. All additional files and original seal non-file checks remain in
  comparison. Appendix status remains UNSIGNED_REQUIRES_OUTER_SIGNOFF.
* Synthetic binding/history/source identity/placement evidence/source-window
  evidence cannot be relabeled as actual. Offline recordings return OFFLINE_MATCH,
  never live PASS. The checker grants no signature, UI acceptance, or execution.

## Build a binding from completed evidence

Run from the landed main checkout. No binding is emitted while files are missing,
receipts disagree, or parent execution is unsuccessful. FINAL_PROOF and APPENDIX
are the separately verified final-seal appendix paths; for candidate-only checking,
use ORIGIN as FINAL_PROOF and omit --appendix.

```sh
R3=benchmark/2026-10-12-exact-realization/r3-activation-selfcheck
RUN=benchmark/2026-10-12-v1-seal-execution
ORIGIN=$RUN/exact-5cd-placement/realization.json
python3 "$R3/build_binding.py" \
  --origin-realization "$ORIGIN" --realization "$FINAL_PROOF" \
  --appendix "$APPENDIX" \
  --prepared-manifest "$RUN/exact-5cd-preview/manifest.json" \
  --admission "$RUN/exact-5cd-admission-r2/admission.json" \
  --restore-adapter benchmark/2026-10-12-exact-realization/r2-timeout/restore.py \
  --execution-receipt "$RUN/exact-5cd-transaction-r2.realization-receipt.json" \
  --transaction-dir "$RUN/exact-5cd-transaction-r2" \
  --execution-cwd "$PWD" --out "$RUN/activation-binding-r3.json"
```

`build_binding.py` only enumerates, hashes and verifies existing local evidence.
It prints the output SHA; pass that exact SHA independently to the checker. The
example JSON is an intentionally non-executable template, not an actual receipt.

```sh
python3 "$R3/selfcheck.py" \
  --activation-binding "$RUN/activation-binding-r3.json" \
  --binding-sha256 "$BINDING_SHA" \
  --serial 5cd1e3dd00000000000000000923012c --boot-id "$CURRENT_BOOT" \
  --hdc "$EXPLICIT_HDC" --out "$RUN/activation-selfcheck-r3.json"
```

Only the external operator may invoke the shown --hdc command. It uses the frozen
read-only collector. For offline validation replace --hdc with --observed FILE;
this cannot produce live PASS. Output must be fresh. Exit 0 means a comparison
match, 1 a file mismatch, and 2 rejected evidence/input; read the output mode and
status as well as the code.

## Targeted offline checks

`python3 test_activation.py` runs only the R3 suite. It uses the actual pinned main
placement proof and reproduces its package locally, then creates explicitly
synthetic transaction journals in temporary directories. subprocess.run is
blocked throughout. This is not the historical 39-case transaction matrix and is
not evidence of board placement or UI health. Raw final stdout/stderr/exit are in
`evidence/`; `results.json` records the exact run outcome.
