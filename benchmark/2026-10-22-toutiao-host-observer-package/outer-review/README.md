# T41 independent acceptance

The initial criterion incorrectly treated signer-generated `.pages.info` as an unchanged resource.
The first failed signing remains evidence, not a retroactive pass. The bounded exception checks both
exact metadata hashes and actual ZIP local-header page layout. Seven other members, the certificate
chain and provisioning profile remain unchanged.

The final delivered HAP is **02f56d181fa883f96505e196570eab6ea75911fa2f1e5edab15f5180c9f19485**,
59,008 bytes, from `release-02`. Its packager is
**075170c786a6b3aafe7275ef2d331037f0ad4b82389322f0cebfd410053ac579**.
This artifact hash is mandatory for any later deployment; different signing runs may produce different
signature containers. The earlier `release-01` peer review is not substituted for final-artifact review.

Outer independently copied the 13-file delivery, checked its manifest, backed up and rehashed 20 raw
records, and ran the frozen checker with `--require-raw`. Seven artifacts, four actual signing/verification
stages, eight production rejection cases and two CLI refusals passed. A separate ZIP parser re-derived
the final bitmap and compared every member against `release-01`; all member payloads matched.
Original certificate/profile bytes matched; all four recorded return codes were zero and timestamps ordered.
See `author-intake.json`, `payload-verification.json`, `verification.json` and the parent `results.json`.

The landing gate ran the Rust selector. Outer then made the selector require raw evidence explicitly,
so a machine missing external artifacts cannot satisfy the task with receipt-only checks. Final peer review
also identified a missing declaration case: omitting a log and its index entry bypassed iteration over
the index. Outer requires the exact seven-artifact and twenty-record sets and added two production
rejection cases. The final complete-mode rerun passes ten production negatives plus two CLI refusals.
These integration changes do not alter the packager or claim a new build. The packager's opening docstring retains its
pre-exception wording; the implemented `verify_candidate`, pinned policy and this acceptance record
define the actual two-member delta. Its exact compiled-build source is preserved unchanged.

## Reproduce and inspect

1. Reproduce the bytecode using [T40's build instructions](../../2026-10-22-toutiao-host-observer-compile/outer-review/BUILD.md).
   The input must be `db781436…`; T39 provides its exact source and patch.
2. Use the accepted `b18978b8…` base from [T32](../../2026-10-20-t32-host-page-accepted/README.md),
   the Java/signer/distribution hashes in `package_observer.py`, and the same public OH development identity.
   Pass paths and the password file explicitly using the parent README recipe. Use new output directories.
3. The driver produces a new receipt and original private logs during actual execution. Preserve both.
   For this historical release, `check_package.py --require-raw --build-dir <release-02>` verifies
   the committed receipt against the actual artifacts and their raw records. A new build must use its own
   receipt; its whole-HAP hash must not be relabeled as this release's hash.
4. `cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_host_observer_package`
   requires the complete historical evidence. The Python receipt-only mode is useful for structural
   inspection on a fresh clone but does not constitute acceptance.

Original and backup artifacts are under
`$HOME/.local/share/westlake/toutiao-host-observer-package-20261022/release-02` and
`$HOME/.local/share/westlake/t41-outer-20261022/` respectively. Private argv contains credentials;
do not publish it. Public records use aliases and hashes. These local archives are persistent but
are not claimed to be a remotely published binary archive.

This accepts offline packaging only. No installation, callback, white-screen fix, video playback,
API freeze or Genshin result is inferred. The repository-wide path gate has a previously recorded
literal-path failure in `benchmark/2026-10-14-verified-source-closeout/jar/verify.py:67`;
the scoped landing gate passes and does not imply a clean whole-repository gate.

Final lifecycle: three task scenarios plus the boundary check passed (4/4, no skips). The Rust selector ran the actual complete-mode checker. `acceptance.json` binds the final source and original verification logs.
