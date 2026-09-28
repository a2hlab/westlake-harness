# OpenHarmony 6.1.0.31 D600 target external roots

These files are immutable OpenHarmony target-side dependencies, not Bridge product
implementation. They are checked in because the Route-A target builder and sealed manifest
require their exact ELF identity, while the previous ignored `out/` location made a clean Git
worktree impossible to build.

The bytes were read from the stock target paths below on three connected D600 devices. Every path
and all three devices produced the same SHA-256 values recorded in `SHA256SUMS`:

- `/system/lib/ld-musl-aarch64.so.1` (canonical target path; the
  `/system/lib64/libc.so` alias resolves to these same bytes but is intentionally
  excluded from the sealed manifest because identity verification rejects
  non-canonical paths)
- `/system/lib64/chipset-sdk-sp/libc++.so`
- `/system/lib64/chipset-sdk/libhilog.so`
- `/system/lib64/chipset-sdk-sp/libbegetutil.z.so`
- `/system/lib64/chipset-sdk-sp/libconfigpolicy_util.z.so`
- `/system/lib64/chipset-sdk-sp/libsec_shared.z.so`
- `/system/lib64/chipset-sdk-sp/libsystemparam.z.so`
- `/system/lib64/chipset-sdk-sp/libutils.z.so`
- `/system/lib64/chipset-sdk-sp/libclang_rt.ubsan_minimal.so`

The build verifies `SHA256SUMS` before using any ELF and records every file in
`ROUTE_A_INPUTS.json`. Device identity and command receipts for the PR reproduction are stored in
`var/evidence/journeys/J01-first-frame-visible/developer-runs/20260805T060207Z-main-pr-repro-r1/`.
