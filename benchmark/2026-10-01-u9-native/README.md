# U9 offline native staging: N10b plus invalid-icon installer

The SHA-correct approved installer base was still the wrong behavioral baseline: `1ffed6bc` omits the **INTERNET/background requestPermissions projection** present in the active installer source `45438280`. A source-hash match alone would have silently removed a validated behavior. The rejected `bbe6af64` candidate is retained as evidence and is not staged for deployment.

The final build first applies the supplied invalid-raster patch to `1ffed6bc` with **zero fuzz**, checks the intermediate bytes against `59a23b34`, then applies `preserve-network-background.patch` with zero fuzz to restore the old permission implementation unchanged. Candidate and independent repeat are both **33558acd4fa0f00a5060f2dde582c825ef4d82b2278a8a356b3ad70dd035cb91**. Its NEEDED, SONAME and complete dynamic export set equal U8 `7048c7c5`; they also equal the permission-preserving patch-off build. The historical recipe rebuild `a4c81ba1` does not reproduce U8 byte-for-byte; this is recorded, not excused as exact source identity.

## Staged package

`$WORKSPACES/westlake-generation-u9-native-33558acd/` is offline staging:

- Native core is exact N10b manifest **a118aca0**, child dc73a28d / runtime ac59dec0. U8 host **1d3b0881**, bridge **84695d62**, ART, frozen provider **0509fe23** and all other native bytes stay unchanged. Failed N11 e20df22e / 5811e0f7 are excluded.
- J9 and T7e remain placeholders copied from the N10b bundle; the outer-selected U9 JAR must be assembled later.
- Installer component has new libapk_installer 33558acd, unchanged libbms 6aadb8b4 and exact rollback installer 7048c7c5, all declared and SHA-checked in `installer/component.json` and bundle `service_group`.
- Native/Java/boot identity count **312**, preview runtime **b8bf5873ac30**, boot **4db882a81732**. These preview values exclude a not-yet-applied installer service and a not-yet-selected U9 JAR.
- **rollout_ready=false**. `prepare.py` checks the separate service hashes; ordinary `u7_executor` does **not** handle the service group. The fixed-mount production gate rejected the initial proposal to add two service mounts (`upgrade changes mounts`); no gate was bypassed. Its rejected manifests are saved separately.

The installer must replace both `/system/lib64/libapk_installer.so` and `/system/lib64/platformsdk/libapk_installer.so`, reload foundation under an authorized board window, and verify foundation proc-root SHA plus a fresh library mapping. The existing background-installer handoff applies. Native activation, boot/JAR activation and installer activation require a coordinated outer plan. Do not set rollout_ready and assume the appspawn-only executor applies the service component.

## Reproduction and checks

`build-installer.py` runs inside a2hlab with WORKSPACES/U9_BUILD_OUT/U9_SDK variables; it uses the preserved OH6.1 recipe and SDK clang 15.0.4 (feef13a36e78…). Recipe/tool/source/objects are hashed in `permission-preserving-build-receipt.json`. Source archive `$WORKSPACES/westlake-u9-native-build-r3/u9-installer-source-33558acd.tar.gz` is persistent and indexed by `source-archive.json`; the original adapter seed came from the prior background-installer build recipe in westlake-harness-bms-deploy. Current SDK/headers are explicit inputs; no stock version is guessed.

`prepare.py --out <new-directory>` reproduces the staging package offline and rejects any service SHA mismatch or accidental rollout flag. `verify.py` checks exact patch/tool provenance, repeat equality, ABI compatibility and staging boundaries. The original invalid-icon production-helper host suite is **15/15**; API permission segments are restored byte-for-byte, not reimplemented. Frozen check: **8 entries, 2 provider artifacts, 0 violations**. N1/N2 for the unchanged N10b core: **51+103 excepted, 0 rejected**. These native gates do not prove foundation activation or icon rendering.

Expected device checks, after the outer approves a service window: Frequent Habits logs `invalid selected raster file=res/d2.webp reason=invalid-webp-header` and `DECLARED_INVALID_RASTER`, own placeholder tile is tappable; canonical WebP/PNG/shoppinglist controls preserve tiles; INTERNET/background grants remain; t20 content is separately signed. No board I/O was done by this preparation.

The full production dry-run passes G1/G2, receipt binding, frozen checks and native gates with **312 expected identities** (`executor-production-dry-run.json`). It correctly reports **gates_passed=true, deployable=false, device_io=false**. The first attempt omitted oatdump and was refused by G2; `executor-dry-run.log` preserves that failure, the retry supplies the locked remote oatdump wrapper. Offline assembly was independently replayed with the same preview fingerprints. Installer consumers inspected: 103 generation ELFs plus libbms; interface equality is the stronger preserved check, not a claim about every system consumer.
