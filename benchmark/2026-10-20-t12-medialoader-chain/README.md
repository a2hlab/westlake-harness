# T12 medialoader static chain: stop before an unproved repair

The earlier top-level library inventory missed an embedded plugin. The corrected inventory is in `../2026-10-20-t12-video-prefix-review/apk-inventory`; the prefix records actual loader failures, while this package records static conditional paths. None proves which video path executed in T12.

## Exact identities and retained evidence

The actual private APK and local APK both hash to a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395. The embedded plugin is 6e8fd7cb523bf51c56f24433932b2cc845d0eeaa6eb9a942502eff73acbddeed. REA initially rejected its `.jar` extension; an identical byte copy named `.apk` then produced package `com.ss.ttplugin.medialoader`, versionCode 13900500, versionName 1390050.0. No signature or execution verification is claimed.

REA Evidence envelopes are retained privately and SHA-indexed in rea-raw-index.json. The `.java.txt` files are explicitly extracted method representations from those envelopes, not raw Evidence. Source completeness and static/runtime limits remain in each original.

## Bounded chain

1. `MediaLoaderPreFindABInitTask.run` asks IMiraService.isMediaLoaderInternalPlugin(). Only the true branch submits an IO task calling getMDlPluginPath(). A further settings/first-install condition controls startDataLoader(). Actual service implementation, returned path and extraction are unproved here.
2. `PluginDirHelper.getNativeLibraryDir(package, version)` uses buildPath(package, `version-N`, `lib`). The absolute base and actual installed version are not established; do not invent a deployment path from the name.
3. `AVMDLDataLoader.init(ZZZ)` returns early if already loaded. Otherwise it catches any ttopenssl error; base loading also catches errors. When useV2 is true it tries avmdlv2, catches UnsatisfiedLinkError, then tries avmdl if still unloaded. It returns -1 if loading still failed. Hotfix branches and caller flags remain unknown. Missing ttopenssl alone is therefore not the first fatal. These alternatives must not all be treated as required simultaneous libraries.
4. `v2-needed-closure.json` closes DT_NEEDED names through the exact APK and plugin (seven packaged providers, six outside-package system names). It does not close dynamic symbols. Fresh run.sh 5a3aef63 selects cronet/crypto/boringssl/vcbasekit/libc++ for explicit ART android-native loads, but does not select avmdlbase/v2. Needed-library resolution is not equivalent to explicit ART target selection; raw-copying two files does not prove an eligible provider chain.

## Prior evidence reused, not redone

Main `benchmark/2026-10-19-toutiao-video-playback/static/README.md`, Updates 1-8, records conditional loader/error behavior and exact 61b P1 evidence. Update 4's real video-card tap produced an actual libttmplayer LOAD-FAIL for SL_IID_ANDROIDSIMPLEBUFFERQUEUE and subsequent native-call error. That is stronger than the feed-only missing-MDL requests. It is not a claim that the same first failure occurred in T12. Updates 3/8 retain maps limitations and namespace/init-array boundaries.

## Next smallest action

Do not extract or deploy libraries yet. In a separately admitted narrow window, after a screenshot-confirmed feed, make one ordinary visible video-card/play action selected from the current UI. Bind the same child and stderr regular-file inode; capture a bounded byte delta starting immediately before the action, preserve timeout bytes, full maps and spaced screenshots. A bottom-tab click plus an unchanged cover does not establish an attempted native player creation.

If there is an exact player LOAD-FAIL, compare it with P1 and subsequent recorded walls. If no attempt appears in the bounded delta, report unobserved/unknown; do not diagnose a loader, network, or random-exit cause. The expected first-fatal removals remain unknown and no fix is dispatched.
