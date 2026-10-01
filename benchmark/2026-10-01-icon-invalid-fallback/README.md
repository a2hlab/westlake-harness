# U9 proposal: invalid selected raster uses the existing placeholder

## Evidence and corrected boundary

The U8 installer reads the selected raster successfully even when its non-PNG bytes are malformed. `NormalizeLauncherIconPng` is cosmetic and fail-open: lodepng cannot decode WebP/JPEG and leaves the bytes untouched. Frequent Habits therefore publishes its malformed 1485-byte `res/d2.webp` as `android/icon.png` and has no own tile in the signed retry. This is **not generic WebP incompatibility**: all 24 other canonical-header WebP selections have tiles. The companion `../icon-format-scan/` report binds the 166 APKs, resource selection, signed outcomes and tile witnesses.

The narrow change is to reject bad selected non-PNG headers before publication, bypass the legacy filename search for that specific condition, and enter the existing `ICONLESS_APK_TEMPLATE_PLACEHOLDER` branch as `DECLARED_INVALID_RASTER`. The generic icon belongs to the template itself, not another APK. A single diagnostic records `file=<selected member>` and `reason=<header failure>`. The existing typed placeholder marker is retained; its text now says no **usable** launcher icon rather than falsely claiming no declared icon.

## Exact source and patch

- Target: `bms/src/adapter/framework/package-manager/jni/apk_installer.cpp`.
- Source commit: `e0adc3c7f99526ee64683e6fa5cdffdf5614c967`.
- Base SHA256: `1ffed6bcd4941767d048988ee230577d8134fcd256055705ce104ca6a51b2730` (byte-equal to that master commit, including B7 `DECLARED_XML_ONLY`). The older cx-bms worktree source lacks B7; it is not the landing base.
- `base-apk_installer.cpp` is the unchanged source snapshot; `proposed-apk_installer.cpp` is the complete proposed result. `apk_installer.cpp.patch` changes only that production file. All hashes are in `results.json`.
- The companion scan ran `artifact_identity` on the U8 installer binary SHA `7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18`. This does not claim that the source snapshot independently reproduces that binary.

PNG handling is untouched. WebP checks its RIFF/WEBP header, total RIFF length, bounded first chunk and VP8/VP8L/VP8X header. JPEG checks its initial marker/segment bounds and presence of an end marker, allowing bytes after that marker. These are bounded header/container checks, **not full decoder validation**: a corrupt later chunk or compressed payload may pass. Do not claim all malformed images are caught. No decoding dependencies, resource rewriting or new image transcodes are introduced.

Manifest/ZIP/selected-member read failures retain the old boundary. XML composition and legacy raster fallback are unchanged. A missing or unreadable template placeholder still fails closed. This patch changes only the special case of readable, selected non-PNG bytes whose supported image headers fail validation.

## Offline tests

```sh
python3 benchmark/2026-10-01-icon-invalid-fallback/test_fallback.py
```

Fifteen tests apply the patch with zero fuzz to the SHA-pinned base in scratch, verify the result equals the proposed snapshot, and compile the actual production helper, `ReadIconByManifest`, classifier, template-placeholder reader and initial carrier-selection branch with `/usr/bin/clang++ -Wall -Wextra -Werror`. External manifest/resource/ZIP services and the template payload are mocked. The carrier test stops before unchanged normalization/label/HAP packaging; this is not a complete native build or minizip integration test. An explicit B7 XML-only regression test preserves its existing template-placeholder classification.

Coverage includes PNG and three WebP variants, JPEG, RIFF length overflow, first-chunk overflow, every truncated VP8X prefix, unsupported bytes, invalid-selected legacy bypass plus member/reason/typed logs, healthy-byte preservation, XML/read-error legacy behavior, manifest/physical-entry fail-closed cases, existing iconless handling, and unreadable-placeholder cleanup. Original selected bytes are separately replayed from the 25 SHA-bound APK members: **24 accepted unchanged, only Frequent Habits rejected**. No input is repaired or modified.

## Handoff to cx-t0 / U9 native

Apply the patch only after the target source SHA matches the base (or explicitly adapt and rerun the tests); never replace a diverged source with the snapshot blindly:

```sh
shasum -a 256 bms/src/adapter/framework/package-manager/jni/apk_installer.cpp
patch --dry-run -p1 -i benchmark/2026-10-01-icon-invalid-fallback/apk_installer.cpp.patch
patch -p1 -i benchmark/2026-10-01-icon-invalid-fallback/apk_installer.cpp.patch
```

cx-t0 integrates this into the single U9 native build with source/toolchain/build hashes, then the outer authorizes a device check. Expected Frequent Habits logs are `invalid selected raster file=res/d2.webp reason=invalid-webp-header` and `ICONLESS_APK_TEMPLATE_PLACEHOLDER ... class=DECLARED_INVALID_RASTER`; the resulting own tile must be observed and tappable, and t20 is separately signed. Negative controls should include canonical WebP, PNG and framework-icon shoppinglist. A generic tile only removes the installer wall; it does not predict app UI success. This lane performed no native build or device operation.
