# APK-contained native libraries versus external sidecars

An empty `native_sidecars` list was a possible preparation concern. Source inspection shows that this list only describes additional files beside the APK. The normal installer has an independent `APK_NATIVE_SO` path for APK-contained `lib/<ABI>/` entries, checks extraction and records `nativeLibraryPath`; the Java converter projects that field to `nativeLibraryDir`.

The exact Genshin APK contains 32 arm64 libraries. Do not duplicate them as sidecars merely because the external list is empty. Inspect the actual installation result in the first authorized window. These source capabilities do not establish which installer/JAR version is currently deployed, successful extraction, or Genshin startup.

`results.json` pins four inspected source files and their line references. No device action, new implementation, or runtime success is claimed.
