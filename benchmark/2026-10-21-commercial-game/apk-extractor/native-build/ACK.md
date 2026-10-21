# COMMERCIAL-G09 — native build complete, offline only

- Native-03: 13 actual stages rc0; executed by outer(codex), inner recipe and analysis. No inner Orb retry, device action, deployment or push.
- Baseline object `2e2a6247…` and library `51e1b525…` exactly reproduced. Candidate `7c24bd11190b0728b81ecd958519f01c688efb2533ef26c9b7ae4eefc82151db`, 1286024B.
- Recipe `3b2a31e0abdd5f89d7612c275af38ef136d5b80a9b45b6ddf0d55d9f208e71bc`; source4068, only zip TU recompiled. Original246/effective247 argv recorded. ABI1539/NEEDED28 equal; APK unchanged.
- Four recipe tests rc0; actual private-output receipt check rc0; public receipt check rc0; Rust1 PASS/0 ignored with G09_BUILD_RUN; frozen8 entries/30 checks/0 violations.
- Native-01 object mismatch and native-02 missing real host SONAME16 remain preserved, alongside actual outer metadata proof and R10 host dependency provenance.
- Local archive `G09_PRIVATE/archive-01/g09-native-build.tar.gz`: c7ad618645f8a7b80486b51b5a95ec43a20f5dc0abb098826719d4ee3d7c4965 /10867480B/552 members; remote pending, not claimed uploaded.
- Exact landing: `landing-paths.txt` (236 paths, 232 payload). Manifest SHA `dc30f1a7fadba9fa32a8a973156a42df2a8b5c33be21b6918ef9bc2c5ee070ca`.
- Installation and gameplay NOT_TESTED. No new public API freeze. Git/blackboard submission delegated to outer under the already-known permission boundary; no commit claimed.

- Clean-checkout correction: original test wrapper rc1/errors2 reproduced; revised wrapper 4/4 rc0 with no ignored `.private` dependency. Test SHA `90bf8f8594c7afb063021feeaf9dd3a17562998a1fff262ca3598bfc736212e6`. Native recipe/logs/artifacts/archive unchanged; no rebuild. Evidence: `evidence/clean-test-fix-01/`.
