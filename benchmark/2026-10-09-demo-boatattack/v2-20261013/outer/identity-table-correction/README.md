# Correct the spare-board recovery-table source

The original r4 preparer copied all four recovery-control sources from the61b final seal. A real5ea read rejected one of337 identities: recovery-table.json expected d70e0dbd, actual2e389a20. The full319 runtime/boot members matched. This was an expected-source error, not permission to copy arbitrary current bytes into the proof.

The corrected preparer selects the existing U13 autostart JSON, pinned by `benchmark/2026-10-10-demo-seal-61b/plan-template.json` at inputs.recover_table. It checks both the exact source path and full SHA. The old proof and rejection remain intact. `delta.json` verifies unchanged337 membership and336 hashes, with only that JSON source changing. Compiler, identity Reader and guard implementations remain unchanged. T0 independently recompiled and accepted this scoped correction.

The new proof is d8f13bf33e431bc8821e4e29c573161c41d1527e276828b8e725efad3e959b22, generation4ef64a7881c994ddb9f0e518736e59ec920e889c54a6cf9616c780eb42a538aa. Real readback at `../smoke10-r4b/window-01/pre-lock-identity/identity.json` reports337 equal, same35da boot and parent4516. This does not establish installed APK identity or UI success.

Control-side transport is explicit: the master board runner stays on Mac, native HDC is exposed by a task-local shim, and the unchanged identity Reader runs through Orb. Earlier failed starts are retained under `../smoke10-r4b/window-01/runner*`. No HOME variable is changed, no identity check is removed, and no board runtime file is repaired by this correction.

The ten-control window produced nine actual t20 screens and one missing-install record. A separate full128 APK read found117 matching,10 missing and one Noice version mismatch. Those are preparation facts, not runtime regressions or accepted exclusions. Completion requires actual missing-control evidence and a separate fresh128 run.61b remains protected.
