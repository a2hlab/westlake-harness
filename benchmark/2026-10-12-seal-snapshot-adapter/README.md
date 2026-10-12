# Receipt-backed seal snapshot adapter

The existing seal provider emitted a generic board snapshot summary, not the demo-seal-snapshot/v1 object required by the real compiler. Separately, the selfcheck recursively collected versionCode values; the real Anki BMS result contains the installed top-level 22401300 and a nested applicationInfo placeholder 0, so the correct installation was rejected as ambiguous.

The offline adapter consumes SHA-bound raw read receipts with explicit remote status, exact read commands, stable boot, complete explicit file groups and the full demo package list plus active overlay hosts. Android codePath and HAP entry.hap paths are observed from BMS, not inferred from manifest versions. The selfcheck now checks the matching top-level installed bundle version. Synthetic input stays marked; successful conversion is never UI acceptance.

Validation: two Rust selectors invoke four Python cases. Real Anki/imehost fixtures verify version and archive identity; the actual selfcheck read_live function is run with a recorded BMS transport substitute. A complete synthetic observation compiles through the unchanged real t5 compiler. Missing hashes, remote failure, cross-boot, wrong bundle and missing version reject. This is offline verification; the final live capture is still required after placement and autonomous boot.

Sources: scripts/lab/demo_selfcheck.sh (baseline master c23fa35f5), benchmark/2026-10-09-demo-baseline/t5/build_seal.py and test_seal.py. Fixtures are original read-only BMS output from 61b at 2026-10-12 19:39, with explicit remote status; no board mutation.

`collect.py` is the outer-owned live read-only producer. It accepts a whitelisted full serial, explicit four-group path inventory, complete manifest and extra host bundle. It saves every stdout/stderr and host/remote status, hashes actual installed APK paths observed from BMS, and converts only after matching bookend boot IDs. The new recorder test executes the actual collector against preserved protocol fixtures and checks that every requested board command is read-only. No live collection is implied by that test.
