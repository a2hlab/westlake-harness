# N11b baseline-reference rejection

The child-only candidate incorrectly retained U8 bundle reference files describing the older U5/U7 underlay. The strict baseline check rejected 13 paths before candidate deployment: J9, the mainline-stubs JAR, and 11 boot-image files. `board61b/baseline-diff.json` records both expected and observed SHA-256 values for every mismatch. No transaction journal was created and no candidate was applied.

A fresh read against the actual U8 expected identity map matched all 312 paths; runtime/boot fingerprints remained `e953c0921536 / 4db882a81732`, with unchanged boot ID. The lock was released. Correct candidate reference rows must describe the resident baseline, not inherited underlay metadata. The native manifest and approved sidecar remain unchanged.

`read_baseline` now saves a per-path diff before asserting exact equality. A negative check with one wrong SHA confirmed rejection and both hashes in the receipt; an exact match was accepted. No assertion was relaxed.
