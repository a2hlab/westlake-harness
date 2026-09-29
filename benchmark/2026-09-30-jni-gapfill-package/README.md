# JNI gapfill: one declared addition, three resident baselines

Artifact copied unchanged from oc-t4 commit **56b5295c**:
`westlake-harness-b4/benchmark/2026-09-29-westlake-port/jni-gapfill/build/`.
`libwestlake_jni_gapfill.so` SHA256:
**c5ed50d53d20e97f6450fa9be899455e23e55b41dc450f42869f2f4bd0a8aba0**.
JNI_OnLoad export verified; this delivery does not rebuild its implementation.

Bundle: `/Users/zhaoyue/orca/workspaces/westlake-jni-gapfill-c5ed50d5`.
Child target: `/system/android/lib64/libwestlake_jni_gapfill.so`.
Java loading: `System.load` that absolute path from a runtime PathClassLoader
class during child initialization. Coordinate the Java call with cc-t3. New
library names are not accepted on the fixed boot/null-loader system route.
Require actual per-class `[JNI-GAPFILL]` registration logs, not just load
success, before interpreting app results.

## Resident baseline matters

The three prebuilt packages all add exactly this one file; other bytes are
inherited from each board's recorded active package:

| Package | Recorded base |
|---|---|
| package-5ea | B92 plus the declared TLS/HTML pair (`...tls-html.../2-html`) |
| package-5cd | B92 bigstack 0509fe23 / ANL a9c9187d |
| package-61b | B90-61b network baseline, retaining B87 runtime c835a93e + liblog 8c81a937 |

Do not select a different board's package to get past a mismatch. If its base
advanced, prepare a new immutable package from the **current** resident one:

```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-jni-gapfill-c5ed50d5/prepare.py CURRENT_RESIDENT_PACKAGE NEW_OUTPUT_PACKAGE
```

The helper pins the original artifact SHA and copied deployer tools, verifies
the entire base manifest, and refuses an already-declared target. It performs
no device I/O. `packages.json` contains exact baseline paths and manifest SHA.

## Deploy and roll back (outer loop owns the boards)

Under the current board lock, stop test apps and expose the resident package's
JAR for SHA checks. Replace SERIAL, PACKAGE and OWNER with the exact values:

```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-jni-gapfill-c5ed50d5/tools/deploy_generation.py SERIAL PACKAGE --add /system/android/lib64/libwestlake_jni_gapfill.so --lane OWNER
# Undo the last owned addition:
python3 /Users/zhaoyue/orca/workspaces/westlake-jni-gapfill-c5ed50d5/tools/deploy_generation.py SERIAL PACKAGE --add /system/android/lib64/libwestlake_jni_gapfill.so --lane OWNER --rollback
```

Then restore the Java candidate with its load point. The deployer verifies
package/staged/device/child-root SHA, single ART, bridge, parent and owned
mounts with HelloWorld smoke; a failure rolls back this file. It never deletes
an existing target or a changed mountpoint. Read screenshots and preserve
master-batch facts; process survival or JNI load alone is not visual proof.

## v3c

The unified base is **westlake-generation-b87-vt-c835a93e**, as directed by the
outer loop: preserve VelocityTracker runtime c835a93e and liblog 8c81a937.
Add this gapfill artifact alongside the network trio, bigstack/ANL, TLS/HTML
and other accepted native fixes. CommonEvent runtime 9e14bf20 derives from
c835a93e and retains VT/SQLite, but is still awaiting device validation.
Do not promote it merely because the host build passed. The three incremental
packages above are not the final identical v3c generation.

Host checks: three full package dry-runs pass with device_io=false; the same
addition engine passed 36 transaction/existing-deployer tests in B93. No new
board writes by cx-t0. R2: package/SHA verified, native runtime effect pending.
