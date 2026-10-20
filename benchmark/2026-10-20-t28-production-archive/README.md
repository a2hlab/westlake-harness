# T28 RGBX production incremental archive

The local T28 producer and independent peer evidence are now preserved remotely. This record proves archival integrity, not on-device behavior.

Candidate: SHA256 `89b9a8b9868bb35d3cd70108e9114714c7f525cbed7006974b4f095912ff0b33`, 97,464 bytes. Incremental archive: `HW248_ARTIFACT_ROOT/t28-rgbx-production-20261020-89b9a8b9/production.tar.gz`, **610,414 bytes**, SHA256 **`106382eeb1c43551658bbede82632dbfb81dcfac7fbb24683114568e4c73b1d2`**, **589 members**.

This is intentionally an incremental package. Its required base is `HW248_ARTIFACT_ROOT/t26-t27-joint-production-20261020-fc58cec5/production.tar.gz`, SHA256 `5d16542a056fca0b2ac102743b1669236de4b4670f35c88924e81247c80ed515`, 69,494,594 bytes, whose prior remote verification is retained. All 156 T28 receipt inputs were checked against actual current bytes: 148 rows match exact base members, 8 new rows are included here. Every reused member was also read back from the exact local base tar and checked. `base-reference.json` lists the required members; private original-path mappings bind them without publishing personal build paths. Both archives are required for full recovery.

The incremental archive includes all current T28 benchmark source/receipts/diffs, frozen landing sources, original compile/link/ABI/host/selector argv and outputs, candidate/baseline artifacts, independent production review and deployment preview/refusal evidence, and the original static peer snapshot. Rebuildable `cargo-target` and `__pycache__` caches are excluded; original test/check receipts and failed attempts are retained. No test, REA, compiler or device action was rerun for archival publication.

Remote creation was absent-only. All three transfer commands returned0; directory700/file600 and the complete new archive, exact membership and every member hash/size were verified locally and remotely. Sanitized envelopes are separate from original private bytes. Earlier pending records remain unchanged. Runtime first-start behavior and playback are governed by the separate T28 window, not this archive.
