# Exact T12 APK inventory follow-up

The directory token `c91d26...` is not an APK digest. The local APK actually hashes to `a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395`, 138,641,340 bytes. This matches the fresh parent-bound private APK read (`actual-apk.log`, inode 66352:160011, T12_APK_OK), not merely the filename.

The zip has 138 `.so` entries. None of the five failed basenames exists as a top-level zip entry: `libttopenssl.so`, `libavmdlbase.so`, `libavmdls.so`, `libavmdlv2.so`, `libavmdl.so`. `libraries.json` contains the full library entry inventory and member hashes. `libttmplayer.so` and `libmffmpeg.so` are included. These are original APK member bytes, not proof of byte equality to a modified deployed media file.

The fresh run.sh has `ASX_APK_PATH=/data/local/tmp/asx/toutiao.apk` and an empty `ASX_SPLIT_APK_PATHS`; this launch does not configure split APK inputs. The APK contains an embedded medialoader plugin (see below); its actual extraction/initialization and whether these are optional probes remain unknown. Empty split configuration does not exclude an embedded plugin.

The five missing-library failures are already recorded as four each in the historical feed-only RouteB run (`static/prediction.json`, network row; `static/README.md:18`). Reappearance here is not a newly identified video first fatal.

## Existing loader source, bounded claim

The preserved source `static/evidence/r2-review/link_stubs_arm64.cc`, SHA 87a2e823fadc8dfa6752542a8f68777145f8774557bedd32f7b9479c9a6654eb, lines 516-604, is excerpted unchanged. Lines 530-545 log non-zip candidates (skip paths containing `!`); 552-559 call namespace/plain dlopen; 568-591 retry an identical packaged copy only for `failed to map library` with `errno=13`. This is not a general ENOENT APK-zip extraction fallback in this source. The printed APK classpath alone does not establish that such a fallback executed. This review does not newly verify source-to-deployed-ELF equivalence or all behavior below dlopen.

## Decision

Two of these five libraries do have exact nested packaged inputs. A candidate plan is to preserve the full plugin inventory, check original plugin extraction/initialization and symbol/namespace closure, then consider a scoped extraction only if missing integration is proven. No deployment is yet justified. The predicted number of video first-fatal cases removed remains unknown. Preserve the concrete missing-library evidence, but first establish an executed player-request path or explicit prepare error before choosing a repair. Do not add fake libraries or re-run full hilog. No device or production operation was performed by this review.

## Embedded plugin correction

A top-level-only inventory misses `assets/plugins/com.ss.ttplugin.medialoader.jar`: it is a ZIP with manifest, DEX and six arm64 libraries. Its SHA is `6e8fd7cb523bf51c56f24433932b2cc845d0eeaa6eb9a942502eff73acbddeed`, size 6,125,342 bytes. It contains `libavmdlbase.so`, `libavmdlv2.so`, `libnetworkpredictor.so`, `libabrmodule.so`, `libcachemodule.so`, and `libpreload.so` (the exact count is in nested-medialoader.json). The missing outer three names are not members of this plugin. Actual plugin execution is unknown.

The nested library member hashes and complete LLVM ELF header/dynamic-table output are retained. This is archive/LLVM metadata inspection, not REA decompilation or an executed load. Native layout REA's advertised profile is x86-64; no engine setup or install was performed. The original extracted inputs are retained at the aliased persistent directory.
