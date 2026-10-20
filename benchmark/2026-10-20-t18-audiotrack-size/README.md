# AudioTrack effective buffer size: one owner method

T17 did not merely lack optional APK libraries: the complete log interval contains three `AudioTrack.native_get_buffer_size_frames()I` failures in `AJVoice.initAudioTrack`. The prior Java-field getter is not a correct substitute for this owner's effective ring limit. This package adds one getter in the existing AudioTrack translation unit and one per-entry registration. Expected first-wall benefit: **toutiao only**. It is source/host preparation, not a deployed fix or proof of sound.

## Exact evidence and scope

- Actual T17 log: `../2026-10-20-t17-network-reuse/actual-video-log-review/`, source offsets 9636343, 31543238, 40140450. Complete selected range SHA `4c4893c463f2074619ef580c7b1179afbcaade65b9d3f03d8f8a1e7884c289eb`.
- `checks/dex-declaration.json`: framework `4a3d1688…`, classes3.dex `58044180…`; method 2801 is private final native `()I`. Field 1778 stores requested frames. Independent DEX review: `audioBuffSizeCheck` at 0x195c5c stores requested bytes at 0x195ca0 then divides by Java frame bytes at 0x195ca4 and stores field 1778 at 0x195ca6. Public getter at 0x1947c8 invokes method 2801.
- Exact bridge `d4fae8e…`: nSetup 0xeccd8 (972 bytes), pushPcm 0xee1d8 (560 bytes). Independent LLVM review found cap at owner +56 and bytesPerFrame at +24; allocation at 0xecdd4–0xece50, pushPcm count/cap loads 0xee254/0xee25c and comparisons 0xee288/0xee30c. This owner's ring write limit is cap; no separate effective limit was found in these functions. These are ELF VAs, not runtime addresses.
- Fresh read-only receipt binds physical/private missing-natives `d8f51c90…`, media-jni `f3943601…`, Android runtime `8ab6742d…`, framework `4a3d1688…`; parent 6067 environment is **parent** evidence. It is not a newly read child 7906 environment. `private-raw-index.json` preserves raw paths, lengths and SHA.
- Historical U12 donor reports a getter wall movement for MuseKit but reads the Java requested field. Its registration function also replaces unrelated natives. Neither behavior is copied here. Full source provenance is in `source-profile/metadata.json`.

## Implementation and checks

`audiotrack_effective_size.inc` uses existing `getShim`, then the owner's mutex. It returns floor(cap/bytesPerFrame), independent of queued bytes. Missing owner, stopping, invalid frame width, cap beyond ring extent, zero complete frames or jint overflow produces IllegalStateException/-1. Existing pending exceptions are preserved. It does not change cap, count, allocation, release, or other methods.

`derive.py` requires the exact source profile SHA and adds only the include plus one required entry in the existing per-method RegisterNatives loop. Reconstruction checks prove all original owner bytes remain unchanged. No UnregisterNatives or new raw-pointer/offset access is added.

Fourteen host cases compile the actual include against explicit JNI/owner seams, including overflow without allocating gigabytes. Rust runs this real compiler/executable, not a Python implementation mirror. Host seams do not prove ART behavior, deployed object layout or lifetime. Existing getShim/nRelease has no demonstrated retain protocol: the field mutex does **not** protect lookup against concurrent deletion. This change does not repair or claim that pre-existing guarantee.

```sh
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_t18_audiotrack_size
python3 benchmark/2026-10-20-t18-audiotrack-size/build_object.py \
  --sdk "$OH_SDK_NATIVE" --out "$HOME/.local/share/westlake/t18-owner-object/new-build"
# Add --execute only after review; default is zero-build preview.
```

The object recipe uses pinned real OH clang/sysroot, JNI declarations and the original Apache-licensed Android log header. It records argv, stdout/stderr, rc, tool/source SHA, dependency list and hashes. It does **not** link a bridge library. Original warnings remain visible; it does not manufacture a successful production link.

## Remaining integration gate

Exact d4fa whole-library producing closure is still `UNKNOWN_EXACT_BUILD_CLOSURE` in the release audit. A compiled owner object cannot establish that replacing the full bridge preserves its existing APIs. Before any production build/deployment, obtain the exact full source/patch/link recipe and dependency/toolchain closure, review the owner lifecycle prerequisite, run ABI/frozen checks and preserve original build logs. Then independently verify the one registration and actual audio behavior in an authorized 5cd window. ANW and continuous video/audio acceptance remain separate. No device calls or production library builds occurred for this package. After review the OH owner object compiled successfully (rc=0), SHA `c96b3456640641c493e3dc125bee7cf944935520e0c5d2d012f200d6f7331f0f`; the independent reviewer reproduced that object twice with the same current SDK. It is AArch64 ET_REL, not a shared library. The 600 actual include dependencies are recorded after compilation; two executable pins alone are not a complete cross-machine SDK reproducibility proof. Three existing owner warnings remain in original stderr. Two additional host tests verify preview creates no output and timeout preserves both partial streams plus rc/status 124.

Independent LLVM/DEX original outputs are under `$BASE20/t18-peer-static/` (nsetup, pushpcm, classes3-dexdump), rc=0. Independent review is `../2026-10-20-t18-audiotrack-peer/results.json` in the peer worktree. Original commands and SHA are indexed privately.

Frozen checks: the correct `check_frozen.py --git` checked 30 registered source objects, zero violations. Earlier no-argument check covered zero objects; an incorrect `--git HEAD` invocation treated HEAD as a repository path and produced false missing-source failures. Both unsuccessful verification attempts are retained and not treated as actual source regressions.
