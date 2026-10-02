spec: project
name: "U12 upstream audio transplant, offline"
---

## 约束

- No device access, current bundle changes, deployment or window approval.
- Pin each requested upstream commit and compare framework68/shim architecture with current route-A owners before transplanting.
- OpenSL Android identifiers are16 bytes, the pinned OH owner identifiers24; do not compare the two raw layouts.
- Buffer consumption/read requests are not hardware PLAY completion; preserve a negative control for OH return12.
- Real PLAY completion and route-A media owner registration remain explicitly incomplete in the first delivery.
- Upstream ledger outcomes are historical comparisons, never proof of this batch's unlocked apps.

## 排除范围

- No generic success/failure facade claimed to be working audio; no duplicate runtime or owner loads.
