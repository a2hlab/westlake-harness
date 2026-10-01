# U7 stopped-parent production executor

The previous U7 artifact was a validator and deployment design, not an executor. Chaining a native deployment and a Java sweep would start appspawn-x between them and expose a mixed generation. This change adds **one journaled transaction** in `scripts/lab/u7_executor.py`. It reuses `Deployment.stop/start/snapshot_files/hashes/ps`, `check_maps`, frozen/native gates, and the sweep tool's extracted `stage_file/bind_file/unbind_file` primitives. Neither complete deploy command is invoked.

**Current follow-up:** the approved provenance exception makes the original T7d example deployable. The 61b first-board validation is in progress; see `board61b/` for actual receipts. Reboot replay is explicitly host-driven, not an installed startup service. The original offline delivery below is retained as history; its initial `unknown` provenance was not silently promoted.

## Identity and actual dry-run

- Example directory: `$WORKSPACES/westlake-generation-u7-executor-example`.
- Approved bundle: `49ad559c331f8f1befb34f7f59b589ade3d4e3e9b86b9ec0cfcadbe4331e0ce4` (original offline bundle `fcd4c0d8`).
- Native U5/N4-order manifest: `7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe`.
- Runtime JAR J7b: `381110a675fb543b6ad4102c8fc721fcb5673bc0da8644ececd1bab1ca60bec8`.
- Stubs T7d: `d8b2406eb89d2947a8cb313a471d4858ff6be86018ece3bb5c2068a11b42ca2c`.
- Real image G1 passed; G2 String.hashCode matched **36/36 instructions**.
- Both candidate and rollback native inputs passed N1/N2 with **28 + 103 excepted, zero rejected**, using the approved 257-entry registry `d40f3b9d…`.
- Frozen package and composed-identity checks passed. The real example has **29 binds** (27 images, stubs, runtime JAR), zero native changes and zero additions. The complete expected identity includes native files, aliases, installer/reference files and platform prerequisites.

`results.json` retains the original offline delivery outcomes; `approved-preflight-summary.json` and `board61b/` record the follow-up. The original report retains compact gate outcomes, fingerprints and raw-report hashes. Full local reports are `paired-dry-run.json` and `dry-run.json`; stderr is not committed. Reproduce from this checkout (environment paths are examples of configured lab variables, not code constants):

```sh
export WORKSPACES="$(python3 scripts/lab/lab_paths.py)"
export LAB_HOME=/home/alvin
export NATIVE_READELF="$(command -v llvm-readelf)"
python3 scripts/lab/u7_executor.py --dry-run \
  --package "$WORKSPACES/westlake-generation-u7-executor-example" \
  --baseline-native "$WORKSPACES/westlake-generation-n4-order-216b68fb" \
  --oatdump "$WORKSPACES/westlake-harness/scripts/lab/oatdump_remote.sh" \
  --out /tmp/u7-dry-run.json
```

The new example is an APFS clone of `westlake-generation-u7-format-example-u5`, with only `receipts/t7d-build-receipt.json` added and its hash referenced in `bundle.json`. Neither the original example nor any payload byte was modified.

## Transaction and rollback

1. Before a Board exists, validate every sealed member, exact 28-member boot group, source containment, native alias precedence, native sidecars/approved exceptions, G1/G2, frozen candidate and baseline. Bind the policy and inputs. Apply additionally requires complete paired-build provenance and `rollout_ready=true`.
2. Require the assigned lane's held board lock, whitelist serial and unchanged boot ID through the existing batch Board guard. A per-serial local advisory lock prevents concurrent executor processes. Read and compare the full baseline SHA map, declared absences and existing mount stacks before staging.
3. Expand native directory mounts into **file-level overlays**, resolving longer nested mount targets first. Stage each distinct source once so two aliases use the same staged inode. Verify SHA, mode and SELinux label. Keep all original directory/JAR layers untouched underneath; do not briefly expose r8b or remove the current JAR.
4. Cold-stop the known control children and stop appspawn-x using the existing `begetctl` primitive. Unknown live Android children cause refusal; this tool does not kill arbitrary processes. Recheck baseline, boot/lock and mount stacks. Persist and fsync a write-ahead journal before each placeholder/bind. Assert service stopped for every mutation.
5. After all native, 28 boot-group and runtime JAR binds, verify the entire expected map and mount ownership while stopped. Recheck gate-bound input identity, start once, verify executable and full SHA views through parent and HelloWorld child roots, plus single route-a ART/openjdkjvm and bridge maps. This is an identity check, **not a visual verdict**.
6. Any caught failure invokes rollback. A lost bind response is reconciled against the recorded previous stack and unique staged root. Rollback stops the service, removes only owned top layers in reverse order, removes only empty owned placeholders for previously absent additions, then checks the exact original mount stacks and full baseline hashes before restart. A modified/foreign layer, boot drift, changed placeholder or failed recovery leaves a `recovery_required` receipt; the tool never automatically unlocks. A new process can resume `--rollback` after a crash. Remote staging is retained for recovery/audit; there is no broad directory cleanup.

Authorized device entry points run **inside a2hlab**, not directly on Mac:

```sh
python3 scripts/lab/u7_executor.py --apply \
  --package "$BUNDLE" --baseline-native "$U5_NATIVE" --oatdump "$OATDUMP_WRAPPER" \
  --serial "$SERIAL" --lane cx-t0 --journal "$JOURNAL" --out "$REPORT"
python3 scripts/lab/u7_executor.py --rollback \
  --serial "$SERIAL" --lane cx-t0 --journal "$JOURNAL" --out "$ROLLBACK_REPORT"
```

The original offline milestone did not run these commands; the authorized 61b follow-up below records actual execution. Package paths must be visible inside the VM and the gate tools configured there. Each attempt uses a new journal; an existing journal is never overwritten by apply. The journal and report must be different files. Existing native receipts remain untouched: use this compound journal for rollback rather than the older native CLI while U7 overlays are active. After reboot, an old journal cannot unmount anything; restore/verify the authorized baseline first, then replay apply with a new journal. Missing baseline directories or undeclared absent files are refused, not manufactured or remounted writable.

## T7d provenance recovery

Followed Mac worktrees/vm-copies → OrbStack → hw248. Local `t7d-build-results.json` described an **earlier** stubs/image revision (`6e2f450e`, `53b970ec`); it cannot attest the final `d8b2406e`/`13aeb841` cohort. The VM still has `t7-stubs-build`. Read-only inventory of hw248's final `cc-wiki-t7d-jars` and `cc-wiki-t7d-out/arm64` supplied all **9 input JAR hashes and 27 output hashes**, matching the example. `boot.oat` itself embeds the full final dex2oat command and these paths.

The present T3c dex2oat64 is `ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b`, matching the previously recorded T3c identity. `t7d-build-receipt.json` records the current compiler hash/version and T3c build-log hash separately. They are **present-day inventory**, not proof of the exact compiler and inputs used at image-build time. A contemporaneous final T7d image build log and toolchain receipt were not found in the inspected locations; both remain **unknown**. No reconstruction is labeled an original receipt and no build was launched.

## Verification and limits

- `test_executor.py`: stopped-parent ordering, aliases, all 33 bind positions before/after/crash (99 injected boundaries), child verification failure, resumed rollback, foreign mount, changed placeholder, staging corruption, restore-gate failure, boot drift, pre-device rejection, real adapter call shape and unknown provenance.
- `test_format.py`: exact boot group, SHA/path/symlink/undeclared member rejection, receipt input binding and unknown handling.
- Executor tests: 16 passed; format/receipt tests: 12 passed. Existing sweep self-tests: 8 passed. Known-answer suite: 82 run, 3 skipped.
- Full spec-check gate under the RUNBOOK Python 3.12 environment: **105 passed, 9 approved exceptions, zero unexpected failures**, gate exit 0 (raw cargo exit 101 retained). The first system-Python 3.9 run failed and is retained locally as `spec-checks.log`; `spec-checks-env.log` is the corrected environment run.
- `specs/u7-executor/t1-executor.spec.md`: 4 mechanically bound Rust selectors, each calling the offline Python tests; lifecycle results are in `results.json`.

The transport/state-machine tests use an in-memory mount/process model, not an OH kernel. The actual dry-run uses the real U7 bytes and trusted native/image/frozen checkers; G2 invokes the existing hw248 oatdump wrapper, never a board. Device authorization and the subsequent execution are recorded in the follow-up below. R2: offline checks verified; production device behavior unverified; historical build provenance partially recovered.

## Follow-up reproduction

The authorized FZ-005 rerun matched **26/27** files. Only `boot.art` differs: two bytes in a CancellationException backtrace long-array element, not OAT path/header strings. Strict reproduction failed; no T7d replacement or eligibility change. See [t7d-reproduction/README.md](t7d-reproduction/README.md).

Authorized R2/R3 follow-up: all six comparisons differ only in that same backtrace element; reproduction values differ from one another. Provenance now classified `verified-with-exception`, with one proposal awaiting outer approval. All four words are outside image ArtMethod ranges; normal PendingFuture cancellation avoids inspecting the sentinel, while explicit stack decoding dereferences it. This historical proposal was subsequently approved as recorded below.

## Approved provenance and 61b solidification follow-up

Outer ACK(95) 2026-10-01 06:58:55 approved
`T7D-REPRO-BACKTRACE-001`. The permanent registry is
`knowledge/gates/image-provenance-exceptions.json`. Its exact nine inputs,
27 original output hashes, tools, embedded command and hashed reproduction evidence
are required by `receipt_check`; revoked or changed entries fail closed. This is
provenance equivalence, **not** a runtime safety waiver. Original T7d binaries and
frozen tools are unchanged. The example bundle now has `rollout_ready=true`,
receipt status `verified-with-exception`; its historical build-log/toolchain fields
remain unknown rather than being retroactively invented.

U5's `PendingFuture.CANCELLED` is the same object graph and file offset, established
independently with oatdump. The method word is `0x60a0ea00`, outside all nine image
ranges and ArtMethod sections; see `t7d-reproduction/u5-backtrace.json`. This risk
is not unique to T7d. No runtime harmlessness is claimed.

The original request for automatic boot replay was explicitly revised by the
outer: **no board startup configuration changes**. Automatic replay remains an
unimplemented proposal requiring a separate user decision. The test instead
reboots, records loss of overlays, explicitly restores the recorded U5 baseline
with `--restore-baseline --from-journal FIRST --journal BASE_REPLAY`, then uses
`--apply` with the same bundle and a new journal. Recorded persistent source hashes
must match before any baseline bind; new-boot/serial and unexpected-mount guards
reject stale or foreign states. A failed recovery keeps appspawn-x stopped and
records `recovery_required`. Never reuse a prior-boot rollback journal.

The board window is 61b only, at most 45 minutes from LOCK. Expected U7 identities:
312 paths; RUNTIME `68b7fb016253`, BOOTIMAGE `8fe2e5fd7d65`; parent/child views and
one ART. Controls: HelloWorld, ZigZag. Reinstall sample: aegis, fd-gallery, noice,
markor, opencamera. Repeat HelloWorld after explicit reboot/replay. Any failed gate
rolls back U5; image verdict remains outer human review.

Outer ACK(95) 07:35:39 corrected the sample gate: Noice is a registered flaky key,
so its observed white t20 is retained but is not a deployment regression claim.
The first transaction was rolled back and verified as U5 before this correction
was acted upon. The revised hard sample replaces Noice with fd-catima; three
additional Noice cold launches are observational only. New journals are used.

## 61b result: partial, replay acceptance incomplete

Both pre-reboot U7 applications verified 312 identities, parent/child views,
single ART and RUNTIME `68b7fb016253` / BOOTIMAGE `8fe2e5fd7d65`.
HelloWorld, ZigZag and the five revised samples (Aegis, Gallery, Markor,
OpenCamera, Catima) have own-UI t20 observations; outer review remains authoritative.
Noice was white in the reinstall sample and in all three additional cold launches;
these observations are retained, not used as a hard gate.

The first Noice-triggered rollback verified U5 before the outer revised that gate.
A deliberate reboot then produced a new boot ID and 300 absent target paths.
The production baseline recovery restored 18 recorded overlays and verified U5
RUNTIME `73ecf422dba2` / BOOTIMAGE `0876029078e2`, including parent/child views.
The subsequent U7 replay was interrupted after the outer explicitly denied a
window extension. It had bound two files; only production rollback and recovery
verification continued. The recovery tail exceeded the original 07:59:25 deadline;
this is recorded rather than presented as an authorized extended test window.
No further app test or post-reboot U7 screenshot was performed. The board evidence
scenario correctly remains failed, not weakened to make this attempt pass.

See `board61b/results.json`, the immutable apply/rollback reports, `reboot.json`,
`baseline-replay.json`, `rollback3.json`, raw `facts-all.txt`, and `evidence/`.
The post-reboot U7 replay + final HelloWorld screenshot needs a separately assigned
window. No automatic startup configuration was installed.

Follow-up verification: executor unit tests 24/24; known-answer suite 82 run, 3 approved skips; user-path gate 0 violations. T1 lifecycle 4 pass. T2 lifecycle 2 pass / 1 fail (post-reboot U7 board evidence incomplete); the failure is retained. Final recovery receipt is `rollback3.json`, status `rolled_back`; 61b was unlocked after U5 fingerprint and parent/child verification.

## Authorized post-reboot replay follow-up (08:03 ACK95)

A separate 30-minute 61b window started at 08:04:08. Read-only preflight found
all 312 U5 identities unchanged on the already-rebooted boot
`2f4be4aa-e0ed-4208-8cfe-db5f1b31bee4`. The production CLI applied the same
bundle `49ad559c331f8f1befb34f7f59b589ade3d4e3e9b86b9ec0cfcadbe4331e0ce4`
using a new `apply4-journal.json`. `apply4.json` is the immutable successful
receipt: 312 identities, parent/child views, single ART and U7 fingerprints
`68b7fb016253` / `8fe2e5fd7d65` all match the pre-reboot deployment.

Only HelloWorld was tested. Its t20 shows its own title, controls and lifecycle
text; raw facts retain `foreground_unconfirmed` rather than rewriting the WMS
result. Screenshot interpretation is submitted to the outer for signature.
The raw facts and t5/t20 images are in `board61b/evidence/after-reboot/`.
No additional app and no further reboot were performed. The production rollback
uses the same new journal; its final receipt is `rollback4.json`.
`replay4-results.json` records this follow-up separately from the previous partial
window, whose timeout and failed acceptance receipt remain preserved.

Final follow-up: rollback4 verified U5 and 61b was unlocked at 08:16:03, within the 30-minute window. Outer ACK95 08:16:53 accepted the U7 solidification. T2 lifecycle: 2 pass, 1 pending human review (machine result retained); outer acceptance is recorded separately. Known-answer 82 run / 3 skips, user-path gate 0 violations.
