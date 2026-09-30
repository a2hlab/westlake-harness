# ACK(95) U5-feedback-v1 handoff

Status: **verified offline**, branch `analysis/bms-route-study`, base `5a9984c8e`. No device commands, no push. Local staging is denied at the shared `index.lock` (`Operation not permitted`, exit 128); files remain in the worktree for outer-loop adoption.

## What to take

Take all **new** files under these paths (exclude Python caches):

1. `benchmark/2026-09-29-static-wall-prediction/rules_u5_feedback.py`
2. `benchmark/2026-09-29-static-wall-prediction/scan_u5_feedback.py`
3. `benchmark/2026-10-01-u5-feedback-v1/`
4. `specs/u5-feedback/`
5. `tools/spec-checks/tests/u5_feedback.rs`

Append only the **single new U5-feedback-v1 line** from root `README.md` and `.octos/KNOWLEDGE-DIGEST.md`. Do not copy those stale branch files wholesale. Do not take any other dirty/untracked paths: earlier B10 path/scoring deliveries are already in master; branch-local exception registries are older than master. Existing scanner sources, selector bodies, exceptions, CSV bae8fd74 and historical scores are unchanged.

## Findings

- **7 rule families, 14/14 known missed keys** matched by actual static inputs; all fourteen scanned APK SHAs agree with their U5 records. Pure rule functions do not accept key allowlists; prediction generation does not read outcomes. `summarize.py` evaluates the known training cases separately.
- **66 keys / 214 DEX**; 29 keys have conditional new-rule requirements. Table verdicts: 23 input-valid conditional-risk keys, 7 input-blocked keys, 36 with no new-rule hit (not a pass). No collection errors. Unknown reachability/producer state/namespace scope is explicit.
- Input categories: split **5**; invalid AArch64 sidecar **2**; SHA drift **1**. Seven unique keys, eight memberships; subway carries split + drift. `noice`/`x` null apps.json pins are metadata-resolved, not falsely called mismatches. `fd-client` is mono-APK, seven DEX. No input repairs performed.
- New CSV SHA **`97014f7146fcbe1ba5c8285cf1112a9c2653ea1f46385836d3eb3a10365ac739`**; JSON SHA **`ac47481c6414f29924822ec1ce46336450878448d701fad180ac59388caf5cda`**; static facts SHA **`f960fa4a1ceff4f074d1cd0614bb86d6e9834370a78dd80dc23a51bdf7384116`**. Rules and parser dependencies are pinned separately in `SHA256.json`.
- Facts use apps.json bytes from fixed master **7fb4a24e2**, SHA `b814abf97d2377387b8611688c5ca7bd4994e83e81eab98168d90ed245258825`, and the local original input copies. They do **not** describe oc-t4's subsequent merged/repaired inputs. Rescan and version those separately before deployment.
- Private preload facts bind **U5/N4-order**, not N5. All six Flutter keys match both the field-ID and private-runtime requirement; no fabricated static ordering or claim that XPM errno 22 is deducible. The native symbol rules are consumer-specific and exclude weak imports.

## Validation

Fixed master **7fb4a24e2dc6acc1ceec422d6a6c37963166a8ef** exported into a temporary directory, with only the payload above plus the two document lines overlaid. No local old exception tables were copied. Exact overlay hashes and both exit codes: `validation/gates.json`.

- `check_user_paths.py`: **exit 0**, 25 approved exception entries, **0 violations**. Explicit archive path list includes the new untracked source files; the initial executable-payload run covers 9508 files, final delivery sweep is recorded separately.
- `spec_checks.py`: **exit 0**, `GATE PASS: cargo_exit=101 passed=68 failed=9 excepted=9 unexpected=0`. These are the unchanged nine approved exceptions, **not** zero cargo failures. Four new Rust selectors pass.
- Python **13 tests, 0 failures**; known-answer **69 run, 2 skipped, 0 failures**; both contracts lifecycle/explain **2 pass, 0 skipped, 0 failed** each. Old `predict.py --verify`: `PASS frozen forecast bytes`. Rustfmt and `git diff --check` pass.

Commands need the normal lab environment, `WORKSPACES` set to the directory containing the harness checkouts, and `CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER=/usr/bin/cc` on this Mac. The archive lacks Git metadata: pass its baseline tracked paths plus the payload explicitly to `check_user_paths.main([...])` rather than accidentally scanning another checkout or zero files. The spec gate command is `python3 <archive>/scripts/lab/spec_checks.py --repo <archive>`.

The rule catalog gives the exact signatures and U5 raw line references. A future wall score must keep input failures separate, bind APK/sidecar/candidate identity, require target-PID (and causal same-TID) evidence plus positive execution for a crossing, and leave t20 to screenshot review. This delivery's 14/14 is retrospective coverage, not a new accuracy claim.
