# Disabled U14 Stage B promotion preparation

A blind U13 port would restore U10.1T8, reuse 318/321 identities and read an old U13 decision. This port instead binds **U14 322 assertions / 320 unique paths → armed U13 321 / 319**, with a future U14 Stage A decision and exact parameterized selftest outputs. No old signoff, historical production receipt or enabled plan is copied as promotion authority.

| Board | Candidate U14 | Restored U13 |
|---|---|---|
| 5ea / 5cd | `56974aa051137bfd0da6f0dba2d714891c2aea4f65114e1600ebc5854a721770` | `2abe4a4917e09d53f47edcfec0ec21b9e131fc72253b8f4aa3d47ff87e8d5aa0` |
| 61b | `afb443708cdb9f7b4a26657b0f00068547f5918ea10802d6aafbb30156c95a1a` | `0a31ad3515c021ce22d00c3d2e2543e16f9164a1b7d2fc6d1d966f3f2fbba761` |

All three plans and both compositions are **execution_enabled=false**. The package byte copies remain externally armed Stage A inputs; this preparation neither edits nor enables them. Production Stage B authorizations, future decisions and fresh Mac/VM production proofs are deliberately absent. Dispatcher refuses before VM/USB/LOCK. Synthetic tests mock device callbacks; a correct-input test is not permission to deploy.

## Port and wiring

- `promotion_dispatch_u14.py`: U13 dispatcher architecture plus the current U14 Stage A pre-lock VM/DEX/shared-scratch/remote-oatdump/RSS guards. Stage B checks exact board/package/smoke/restoration paths, current authorization and future Stage A first; it never calls the Stage A apply admission.
- `promotion_hook_u14_runtime.py`: retains only after future Stage A admission, fresh same-board/window outer signature, exact smoke/identity SHA, both bright control screenshots and final 322/320 verification. Every refusal, malformed signature or expiry selects U13 rollback; restoration failure propagates to preserve the lock.
- `review_wait_u14.py`: maximum 20-minute wait, cutoff no later than lock-start+20 minutes to reserve at least ten minutes of the 30-minute window for rollback. Partial signature is not a decision; malformed smoke still enters the finalizer. Uses `candidate-identity.json`, never stale `candidate-318.json`.
- `common/runner.py` and `61b/runner.py`: configure only their own variant. Their captured current U14 Stage A `transaction_backend.py` supplies journal apply/rollback, same-board snapshot/fingerprints/process views, recovery smoke and final verification. Only path-depth/WORKSPACES and the disabled direct-entry guard are changed. Do not call its Stage A `apply` routine for Stage B.
- No old U13 `after_shards`/window4 fallback remains. Stage B has smoke groups and no extra sweep shards, as the U13 promotion pattern; reference protection was measured in Stage A, not claimed again here.
- `source-provenance.json` pins original U13 four files, current U14 transaction/dispatch sources, identity maps, arming proof, reference and accepted smoke JSON. `port-deltas/` shows exact source changes. Cold tests need only landed JSON/source plus shared production Python helpers, not private ELF/JAR `.artifacts`.

## Smoke and identities

Use the admitted `outer-smoke-review.json` limits: ART/JVM exactly 1; bridge/runtime/javacore 1..2; newly added ICU compat 0..1. The production `single_copy` list contains all six libraries; explicit `copy_limits` override only the four reviewed members. HW/ZZ schema2 selftest is strict: error/badtag/probe_error/unknown rejects. Every copied smoke and restoration spec has a composition SHA binding; fingerprints and exact probe files are unchanged. 61b retains its own libinstalls51e1 identities; no installer alignment occurs.

## Future Stage A signoff contract

Run the real reusable aggregator, not this packet's fixtures:

```sh
python3 "$WORKSPACES/westlake-harness/scripts/lab/stage_a_selftest.py" \
  --root "$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan" \
  --pattern 'window*/u14-A*/*/runner/**/record.json' \
  --out '<outer-owned-persistent-output>' > '<outer-owned-persistent-summary.json>'
```

Outer signs `outer-stage-a-{common,61b}.json` under the future U14 Stage A decision directory. Templates in each variant are unsigned contracts, never executable evidence. Required fields: release U14/phase A/signed_by/signed_at; exact native manifest+inputs and armed U13 baseline; exact 126-key reference hash and regression verdict; promotion_authorized=true; process_selftest_gate report, explanations and stdout-summary **paths+SHA**, full measured_records, exact root/pattern and stage_a_selftest tool SHA/exit0. The approved unarmed or exact corresponding armed bundle can be signed only after byte-identical arming metadata is proved. No unrelated bundle can pass.

The gate retains U13's schema2 per-process failure veto and exact individual outer explanations for unknown coverage. It additionally binds the actual aggregator summary and explanations even when no unknown exists, rejects any-pid failure, and requires the complete U14 candidate runner domain rather than U13/control-only selection. Failure classes cannot be explained away. Do not hardcode future report names: the signed decision supplies their precise paths.

## Outer / cx-t0 handoff

1. Review wiring and all per-board identities/specs; keep this packet disabled.
2. After Stage A is signed, supply exact decisions and separate `outer-stage-b-authorization-{common,61b}.json` (signed_by, promotion_authorized, exact armed bundle and manifest). Refresh both production gate-pass receipts against current policy, using the existing four-surface execution path; old Stage A PASS is not automatically fresh Stage B proof.
3. cx-t0 creates fresh per-board output/plan copies with `U14_B_RUN_ID`, rebinds all hook/plan/spec paths if copied away from master, obtains outer execution approval, then alone enables those copies. Never mutate the reference packages or this disabled preparation to fake authority.
4. Fresh Stage B outer decision binds release U14/phase B, signed_at, same serial/window_root, candidate bundle+manifest, smoke+identity SHA, bright HW/ZZ and zero regressions. Missing/stale signature restores U13. Do not revoke the enabled window composition during cleanup; use its unconditional journal rollback if any prerequisite fails.

## Known answers and reproduction

```sh
python3 benchmark/2026-10-03-u14-stage-b/prepare.py
bash benchmark/2026-10-03-u14-stage-b/replay-known-answers.sh mac
bash benchmark/2026-10-03-u14-stage-b/replay-known-answers.sh vm
CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc cargo test --manifest-path tools/spec-checks/Cargo.toml --test u14_stage_b
```

Wrong bundle rejects, one badtag rejects despite OK, no fresh signature restores, correct synthetic inputs pass; extra cases cover payload drift, 320-path truncation, report/explanation/selection drift, any-pid failure, stale smoke/window, malformed signature and malformed-smoke finalization. The original Mac 16/16 and outer VM Linux x86_64 16/16 replay are historical, not proof for the P1/P2 revision. That historical VM raw output SHA256 is `c388ce371ecc39ce06b08a052d6c0aadbe4c95b2e4545257b23a855a5aae2fab`; its receipt is preserved in `inputs/history-p1p2/vm-replay.json`. Earlier local timeout attempts (exit124) remain diagnostic evidence, not the VM result. Fresh P1/P2 Mac and cold-copy tests cover 23 cases; Rust has three selectors. See `validation-runs.json` for fresh command exits and `vm-replay.json` for the explicitly pending outer VM replay. Raw logs/exit receipts are in `evidence/` and persistent `.artifacts/raw/`. No lock, device transport, deployment, VM restart or native rebuild was performed by this revision.

## P1/P2 wiring correction (outer 13:14)

The original lock+24-minute cutoff reserved only six minutes, below the measured 447–479-second restoration duration. P1 now cuts off by lock+20 minutes, leaving at least 600 seconds (121 seconds above the slowest measured restoration, not a new timing measurement). The coordinator does not yet expose its lock epoch to the waiter. On Mac, the stable `runner` directory birthtime is captured before LOCK and used as a conservative lower bound: cutoff can be earlier but never later than lock+20 minutes. Missing/nonfinite/future start time fails closed into the finalizer; the former post-lock `window-input.json` mtime fallback is not used. Receipt fields record this basis, the deadline and ten-minute reserve. At or after the exact boundary an already-present signature is rejected, and the finalizer receives no decision, even if the file appeared late. No fresh wait starts after the cutoff.

P2 retains summary/policy checks but additionally reads full `gates/mac/executor` and `gates/vm/executor` receipts. Each must be deployable, bind the exact candidate/root and restoration baseline, and provide exactly two correctly owned native tickets. It invokes the same production `deployment_native_gate.assert_unchanged` used by Stage A on candidate and baseline on both surfaces (four assertions). Registry, checker, native sidecar, payload or ticket drift refuses before transport. Tests use the real binding algorithm against temporary fixture files; green summaries alone cannot bypass it. No active gate table, Stage A executor, composition payload or candidate identity is changed.

The fresh outer VM command is tests-only; do not reuse the archived 16-test PASS:

```sh
WORKSPACES=$HOME/orca/workspaces bash benchmark/2026-10-03-u14-stage-b/replay-known-answers.sh vm
```

### Subsequent smoke-spec revision

This disabled packet captures the admitted smoke specifications from before the outer 12:02:29 r3 correction. The correction removes mandatory M6@fd-app and accepts nonzero Flutter EGLSurface pointers with or without `0x`; it does not change copy limits or payload identities. **These captured smoke files are not the final Stage B execution specifications.** Before activation, cx-t0 must copy the approved r3 specifications, rebind each composition smoke SHA and plan path, and refresh the production receipts. Do not relax the SHA check or treat this synthetic Mac/VM replay as validation of an actual r3 board window. M6 remains Stage A record-only observation, not a mandatory smoke marker. This packet and the currently running Stage A plans are unchanged.
