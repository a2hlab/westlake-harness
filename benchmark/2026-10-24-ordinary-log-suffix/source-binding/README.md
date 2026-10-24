# T122 ordinary rendering marker source binding — first slice

A same-name source or binary-copy index is not a producing-source receipt. No full marker-to-source-to-original-build chain is claimed by this slice.

- **Exact segment:** T106 records mapped `libhwui.so` SHA `a11c9154…` and bridge `b0e5602a…` on both boards with stat/maps identity checks. `mapped-identities.json` preserves the selected records; this does not retroactively bind failed children 7011/9860 or select a namespace winner.
- **Missing source/build link:** an independently hashed local copy of a11c contains `EglManager::swapBuffers ENTRY` at file offset 2820172. The indexed artifact/build ID is exact; producing source, patch and original compilation logs were not established.
- **Related-only source, exact final-link segment:** `sources/api-implementations/bridge-d4fa-source-snapshot/base/westlake/framework/window/jni/oh_anativewindow_shim.cpp:874` contains `WESTLAKE-SWAP`. T29's production receipt links object `673c6893…` into exact b0e. Its final-link argv/stdout/stderr/rc hashes are retained in results. The source-to-original-object compilation link remains unverified in this slice. Logging is limited to the first six calls and each 120th call; missing logs alone do not prove no swap call. `rc=1` is the forwarded return, not proof of a visible frame.
- **Related-only:** the ability38 `oh_window_manager_client.cpp:1326` snapshot contains the RS-flush marker; T29 links f91b object, but original source-to-object compilation evidence is not yet independently bound.
- **Missing:** NativeWindow/BLAST generic string membership is insufficient to bind the precise log emitter. No source attribution is promoted from similarity.

`evidence-index.json` records exact metadata/source SHA and matching line numbers. `results.json` records full artifact/source/object/log hashes and the existing T29 remote archive reference (ead48782…). This task did not fetch or reverify that remote archive. No device, VM, remote command, build, REA, or stopped-object investigation was performed. These are provenance limits, not a failure/root-cause diagnosis.
