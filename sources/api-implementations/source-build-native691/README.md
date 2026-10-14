# Later native implementation source

Previously, r84–r89 rows linked reports without the implementation. This package preserves exact Git blobs from a2hlab/westlake **691433b967ba01365a382d30fbd820c1231c0811**, including native bodies, original build scripts and local headers. `sources.lock.json` pins each file; `api-resolutions.json` identifies actual members. No device or compiler was run. The full original Apache-2.0 LICENSE and file-specific notices are retained. The large firmware ABI inventory is excluded and explicitly pinned as an external catalog; it is not an input to the two recipes below.

## Build the delivered implementation families

Use a fresh disposable output. The original bionic script removes its output directory. Do not pass a source tree or an existing artifact directory. From the repository root:

```sh
bash sources/api-implementations/source-build-native691/westlake/tools/build_bionic_shim.sh "$OH_SDK_NATIVE" "$FRESH_BIONIC_OUT"
bash sources/api-implementations/source-build-native691/westlake/tools/build_missing_natives.sh "$ANDROID_SOURCE" "$OH_SDK_NATIVE" "$FRESH_MISSING_OUT"
```

The first produces `libwebview_bionic_shim.so`, `libaaudio.so`, and artifacts.json. Its complete in-repository inputs include webview-shim C/assembly/maps, third_party/aaudio and third_party/jni. The second produces `libwl_missing_natives.so`; its in-repository inputs include all javacore-shim units, expat-compat headers and the version map. External inputs are the OH SDK clang/sysroot/CRT/OpenSLES and Android libcore/libnativehelper/expat. Their source/toolchain acquisition locks are in the already delivered `source-build-host/manifest-tools/` sibling. Those locks identify a candidate source build stack, not a recovered historical producing toolchain. Original r84–r89 paired build logs and exact deployed ELF equality remain unknown. New build rc/stdout/stderr must be captured by the caller; this delivery does not claim a compile.

Camera count returns zero; PerformanceHint acquisition returns no service; the InputQueue fallback does not deliver input. Their existing API grades are unchanged. NATIVE-159 is an unresolved surface-competition item, not a newly implemented API. NATIVE-155 here is the routed-name consumer; the launcher default-routing producer and JAVA-115 are being delivered separately. JAVA-104 is the real `wl_getSpace0` statvfs body. NATIVE-160 references the existing host microphone resource without duplicating the Java/host source package.

This source snapshot is newer than historical experiments. Code delivery, source build success, historical byte reproduction and deployment acceptance are separate claims. None of the latter three is inferred from source presence.
