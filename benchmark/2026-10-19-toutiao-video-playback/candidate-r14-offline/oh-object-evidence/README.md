# R14 optional OH static object

**OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE**

The previously accepted C/header bytes were compiled, unchanged, with existing
DevEco OH clang15.0.4 and its sysroot. All six actual commands returned rc0;
check_frozen reported 8 entries / 30 checked / 0 violations. ELF header independently
shows ELF64 little-endian AArch64 ET_REL, zero program headers. The target Buffer
and Rect static assertions compiled successfully. The object is 5,752 bytes.

This closes only the missing OH static compilation evidence. It does not execute
the module, link any shared library, bind a provider, establish real window ABI,
or prove playback. The compiler version's default host Target is Darwin; the
actual compile argv explicitly uses `--target=aarch64-linux-ohos`, and the output
ELF confirms AArch64. All 26 actual source/header dependencies were SHA-pinned
before compilation and compared against the generated full dependency file after.

```sh
python3 benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/build_oh_object.py \
  --source-repo "$SOURCE_REPO" --sdk "$OH_SDK_NATIVE" --out "$FRESH_PERSISTENT_OUT"
```

SDK defaults to the installed DevEco path, or OH_SDK_NATIVE/--sdk. Only the exact
recorded clang/readelf pair is accepted; source drift is refused. No package is
installed. Original commands/stdout/stderr/rc and the original receipt are retained
in the private raw directory indexed here; portable JSON replaces paths with
aliases without claiming byte identity to the originals. Readelf output and the
small ET_REL object are included verbatim. No prior R14 source, host tests or signed
manifest was changed. This directory has its own landing and SHA manifest.
