# #48 arm64 hook-engine baseline handoff

Read-only retrieval from board61's actual Toutiao runtime, with no app launch, binary replacement, profile reset or speed-layer changes. All four shared binaries are **ELF64 little-endian AArch64, e_machine183**. Both pre/post board SHA and local bytes match.

Actual board prefix:
`/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/lib/arm64-v8a/`

The source_app_namespace private mount exposes this as `/data/local/tmp/asx/lib/arm64-v8a/`, exactly the path in the recorded crash maps. Each filename below is appended to that prefix. This is not a v7a APK copy or an unverified build artifact.

| Library | SHA256 | Bytes | Crash-map coverage |
|---|---|---:|---|
| libbytehook.so | 238e7bc3e0c36247de86fe80453d596503ec0c45bc3ece578fc351d638506d61 | 63504 | r3 and r4 |
| libshadowhook.so | 88351a015be00254f961d5c559187513f8a657a40fb9d13f50b5d0733d7e9cbf | 77936 | r3 and r4 |
| libjato.so | 5e03163a8da80d489fc3f9d11c489f47c5a3f791a183ec4050f43cb2a42806dc | 1201984 | r3; absent in r4 maps |
| libhotfix-opt.so | fe9d9d3834c10f964f7279c6c0d0cadc3b78d481997daaeb224df9f6a553e7f0 | 22600 | r3 and r4 |

Shared directory (Mac and a2hlab VM use this same `/Users` path):
`/Users/zhaoyue/orca/workspaces/westlake-harness-engines48/benchmark/2026-09-26-hook-engines-arm64-48/`

The four `.so` originals are in that directory and in the commit. `manifest.json` provides full per-file actual path, namespace path, shared path, SHA, size and architecture. `crash-maps-excerpts.json` preserves relevant complete-map lines from clamp-r3/r4. `board-hashes-before.txt` also records current inodes matching the historic maps: bytehook137370, shadowhook137195, jato137407, hotfix137393. This strengthens artifact continuity; maps alone still do not prove which hook API was invoked or caused corruption.

Hollow+clamp board state is unchanged: no app/parent PIDs; both guardians stopped; map_count1048576; consent untouched. Reverified34 component hashes, including the patched BCP jar plus27 boot files, three protection patches, npth9966e296, shim85c789f4 and unchanged run.sh ffb324e4. No new dynamic stability result is claimed. R2=verified for this artifact handoff only.

`pull_baselines.py` is the bounded read-only retrieval script, run via `orb -m a2hlab bash -lc`. Its HDC calls target only61 and use deadlines≤25s; no system or app data writes. The operator's proposed engine patches are not deployed by this handoff.
