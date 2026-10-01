# U9 native and J10g rollout preparation

The earlier preview included installer 33558acd, rejected by FZ-001. Outer ACK(80) at 17:28:02 removed that change from U9. This package is **U8 + accepted N10b native + J10g**, with frozen installer **7048c7c5** and libbms **6aadb8b4** unchanged. It does not restart foundation or include an installer kit. The rejected preview and invalid-icon evidence remain separate historical artifacts.

Candidate directory: `$WORKSPACES/westlake-generation-u9-j10g-238ffc14`. Runtime JAR SHA begins **238ffc14**; full SHA is recorded in `package.json`. Native manifest is the accepted **a118aca0**; child **dc73a28d**, runtime **ac59dec0**. N11/N11b are not included. Fingerprints are **a8cb9a5a45a6 / 4db882a81732**. Executor checks **312 identities**, and the hook additionally checks four unchanged system-service aliases. A successful final receipt therefore covers **316 identities**. The two extra bridge/runtime instances are the explicitly accepted U8 baseline, not a claim that N11 succeeded.

The package remains `rollout_ready=false` until the final J10g window is accepted by the outer loop. No board lock or device command has been issued for this preparation. Production G1/G2, native/frozen checks and the readiness state are recorded in `production-summary.json`; full local reports are not listed for landing.

## Composition and gates

`prepare.py --jar FILE --jar-sha SHA --out NEW_DIRECTORY --extra-smoke DONOR_SPEC` checks the donor JAR hash, copies the accepted native artifact, removes its installer kit/service declaration, and rewrites reference hashes to **resident U8** values. It asserts all 312 baseline identities equal the U8 executor plan. Comparing only native `generation_bundle.validate()` output (172 paths) would miss the composed Java/image/reference identities.

The final donor smoke markers are merged without replacing N10b's four markers or J10d/e/f markers. All donor workspace paths are converted to `$WORKSPACES`. The spec requires ART/JVM one instance and bridge/runtime exactly two load-address instances. A third is refused. Installer ICONLESS/DECLARED_INVALID_RASTER markers and frequent-habits are absent. Frozen service hashes are still read-only assertions.

Native provenance/build inputs remain those of the approved N10b evidence; this step does not rebuild any native library. J10g donor source/build evidence is in `westlake-harness-t3/benchmark/2026-10-01-j10g-jar/` (commit 706a3bfa87; source 8ff080357a). Any later changed JAR requires a fresh output directory, new fingerprint/spec and repeated production dry-run.

## Sequential deployment after outer approval

Use the three plans as templates. Before opening a real window, record J10g acceptance in the bundle, set its rollout-ready flag, and rerun the production dry-run. Keep the gate code unchanged. Select a **fresh** output directory in both hooks and the runner for every attempt.

1. Run the offline service gate, then start **master** `board_run.py PLAN --detach`. The runner validates `offline_precheck.expect`, locks the full serial, and invokes `native_window.py --apply`.
2. The hook refuses an unready package before device access. It reads all 312 U8 identities and the four frozen installer aliases with an explicit per-path mismatch receipt, then applies native/JAR/image as one stopped-parent executor transaction.
3. Activation smoke must PASS its merged markers, parent/child identity, expected fingerprints and owner counts. Deliver every facts.txt verbatim and t20 screenshot paths for outer review. Processes and markers alone do not prove lit.
4. Successful `before_unlock` re-reads all 316 desired identities and retains U9. A failed smoke rolls back using the same transaction journal, then explicitly verifies U8 plus unchanged service identities. Failed rollback or verification returns nonzero and retains the lock; do not claim recovery.
5. Finish the first board and obtain its verification before proceeding to the next. No foundation restart, installer swap, reboot or board startup configuration belongs to this rollout.

Configure `WORKSPACES`, Mac `MAC_HOME`, and remote oatdump `LAB_HOME` explicitly; the established remote lab root is `/home/alvin`. `production-command.sh` contains the portable offline invocation. The VM executor wrapper is reused, not rewritten.

## Independent tool improvement

`swap_installer.py --transaction-name NAME` is retained as a separate tool improvement, **unused by U9**. It isolates backup and per-board state directories for future approved installer transactions. Omitting the option preserves the original paths; unsafe names are rejected. Dry-run verifies kit bytes without constructing a board. Fixture-based tests cover isolated/default receipts and invalid names without depending on an actual installer candidate.

## Offline checks and evidence limits

Five rollout tests cover marker/plan coverage, unchanged service identities, backup isolation, unsafe names, strict copy counts, incomplete baseline rejection with per-path diff and failed rollback retaining the lock. Existing U9 candidate verifier still passes its three historical build tests; this does not authorize that rejected installer for U9. Native/frozen gates are authoritative. The first J10g gate invocation used an incorrect remote LAB_HOME, was stopped, and is preserved locally; the corrected invocation uses the established lab root and a new report filename.

`landing-paths.txt` omits old previews, large/raw logs and the unapproved frozen-installer proposal. Both this list and the separate N11b offline-failure list must pass lane-side `land.py --preflight` before handoff. Local submission only; no push.
