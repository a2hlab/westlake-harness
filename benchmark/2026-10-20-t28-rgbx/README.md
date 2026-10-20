# T28: preserve RGBX2 while presenting OH12

T26 child 7603 requested Android RGBX2 at 720×1280; its actual OH11 buffer reached the exact Mali create entry and returned NULL. The first-child [excerpt](evidence/first-child-excerpt.json) binds the selected 486077-byte raw transfer. This is not a verdict on the whole T26 window: later children and YV12 playback are separate outer evidence.

Only a successfully recorded RGBX2 request now maps to OH12. The caller still receives RGBX2, its original bits, actual dimensions and pixel stride. Before the existing Unmap, the added `rgbx.c` checks the complete mapped extent, then writes alpha 255 for active pixels. RGB and row padding remain untouched. No allocation, loader or provider call is added. Unmap/Flush/Abort ordering and retained-error handling stay in the original derived R14 path. Unknown history, other formats, YV12 conversion, three-slot admission, alias exclusion and observer sources are preserved.

Actual host results: 34 inherited core cases, 10 invalid-layout checks, an RGBX alias race/state-reuse check, and 22 exported-shim/pair/R15/R14 routes with the real observer enabled. Five Rust selectors pass; lifecycle has five passed and one human PendingReview. Initial test sign-comparison and Rust receipt-cwd failures remain in the raw index. Neither failure was erased or described as a device result.

Production reproduces `fc58cec5c7a445a28ed0c0e3ec44d486f16f0921afe8ef4b6974bd96ca9574e9` exactly. New candidate `89b9a8b9868bb35d3cd70108e9114714c7f525cbed7006974b4f095912ff0b33` is 97464 bytes. All 78 versioned exports, the sole libc dependency, no TEXTREL and both exact consumer ABI checks pass. Export offsets: lock `0x6ec0`, unlockAndPost `0x6ed4`, geometry `0xe3b0`. No device commands were run; this package does not authorize deployment.

[Production receipt](production-01/receipt.json), [source index](production-01/source-index.json), [tools/dependencies](production-01/toolchain-dependencies.json), [raw index](production-01/raw-index.json), [host receipt](production-01/host-receipt.json), [ABI](production-01/abi.json), [peer](evidence/peer-results.json). Original argv/stdout/stderr/rc and complete source snapshots remain under `.private/`; large original inputs are pinned by exact path and SHA, not represented as reconstructed historical logs.

Aliases: `$T28` is this directory; `$T26` the frozen sibling benchmark; `$REPO` this checkout; `$MAIN` main checkout; `$CC_VIDEO` frozen observer checkout; `$VIDEO_PLAN` original producer checkout; `$WESTLAKE_INPUTS` persistent input repository; `$ORB_WS` existing Orb workspace; `$HOME` execution user's home; `$BASE20` persistent toutiao-resume-20261020 directory. SDK paths are the actual non-personal DevEco installation.

## Reproduce offline

Run `build_host.py --repo "$MAIN" --observer "$OBSERVER_SOURCE" --out "$NEW_HOST_OUT"`. Run `build.py --repo "$MAIN" --sdk "$OH_NATIVE" --base-build "$T26_BUILD" --t27 "$OBSERVER_SOURCE" --joint-glue joint-glue.json --consumer "$EXACT_HWUI" --player "$EXACT_PLAYER" --out "$NEW_BUILD_OUT" --execute` from this directory (use an absolute joint-glue path if invoked elsewhere). T26_BUILD must contain the original production-02 receipt and objects; the recipe refuses source/input drift. Set `T28_HOST_OUT` and `T28_BUILD_OUT` for the Rust selectors. Existing outputs are never reused as a fresh build directory.
