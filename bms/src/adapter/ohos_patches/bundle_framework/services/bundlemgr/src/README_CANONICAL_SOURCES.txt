Canonical source rule for libbms adapter integration
======================================================

This directory holds OH-side glue code that lives in
`oh/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/` at
build time but is sourced from the adapter project at restore time.

Files and their canonical locations:

  adapter_apk_install_minimal.cpp  [ARCHIVED / DEAD CODE]
      Historical location: HERE (this file)
      Archive location: $ADAPTER_ROOT/archive/ohos_patches/bundle_framework/services/bundlemgr/src/adapter_apk_install_minimal.cpp
      Status: superseded. The real APK install path now routes through
      `libapk_installer.so` (dlopen'd by base_bundle_installer.cpp / bundle_installer.cpp)
      and calls `oh_adapter_install_apk` / `oh_adapter_install_apk_with_manifest`.
      `ProcessApkInstall` has no caller. The file has been removed from
      apply_BUILD_gn.py, from restore_after_sync.sh phase B10, and from the OH
      source tree. It is kept in docs/archive/ for historical reference only.

  apk_manifest_parser.cpp
  apk_manifest_parser.h
  axml_parser.h
      Canonical location: $ADAPTER_ROOT/framework/package-manager/jni/
      Reason: this is a self-contained Android AXML parser that's part of the
      adapter's package-manager subsystem. It no longer depends on AOSP
      libandroidfw, so the old AOSP-header include paths are not required.
      It needs to be inside libbms at gn compile time, so we deploy a copy via
      restore_after_sync.sh — but the canonical source stays in adapter.
      Deployed by: restore_after_sync.sh phase B10
        cp $ADAPTER_ROOT/framework/package-manager/jni/apk_manifest_parser.{h,cpp} \
           $ADAPTER_ROOT/framework/package-manager/jni/axml_parser.h \
           $OH_ROOT/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/

  apk_signature_verifier.cpp
  apk_signature_verifier.h
  apk_verify_result.h
      Canonical location: $ADAPTER_ROOT/framework/package-manager/jni/
      Reason: APK Signature Scheme v2/v3 verifier used by ProcessApkInstall
              before any APK bytes are copied or trusted. It links against
              OpenSSL and must be compiled inside libbms alongside the parser.
              apk_verify_result.h is the shared identity structure.
      Deployed by: restore_after_sync.sh phase B10
        cp $ADAPTER_ROOT/framework/package-manager/jni/apk_signature_verifier.{h,cpp} \
           $ADAPTER_ROOT/framework/package-manager/jni/apk_verify_result.h \
           $OH_ROOT/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/

  permission_mapper.cpp
  permission_mapper.h
      Canonical location: $ADAPTER_ROOT/framework/package-manager/jni/
      Reason: bidirectional Android <-> OpenHarmony permission name mapping.
              Used at install time to populate ApplicationInfo::permissions.
      Deployed by: restore_after_sync.sh phase B10
        cp $ADAPTER_ROOT/framework/package-manager/jni/permission_mapper.{h,cpp} \
           $OH_ROOT/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/

  native_payload_inspector.h
      Canonical location: $ADAPTER_ROOT/framework/package-manager/jni/
      Reason: header-only APK native-library ABI scanner. Used by
              ProcessApkInstall to decide which lib/<abi>/ slice to extract.
      Deployed by: restore_after_sync.sh phase B10
        cp $ADAPTER_ROOT/framework/package-manager/jni/native_payload_inspector.h \
           $OH_ROOT/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/

Why this layout (item 3 collapse, 2026-04-12):
  Previously, apk_manifest_parser.{h,cpp} existed BOTH in the adapter source
  and as a duplicate copy here. That was a "two-source-of-truth" footgun —
  any edit on the adapter side had to be manually re-copied. Now there's
  exactly one canonical location per file, and restore_after_sync.sh phase
  B10 deploys them on every restore. To modify any of these files, edit only
  the canonical copy and re-run restore_after_sync.sh.

Compile path verification:
  After restore_after_sync.sh, all source and header files exist as siblings
  under oh/.../bundlemgr/src/. The libbms BUILD.gn (patched by phase B8) lists
  the .cpp files in `sources +=` and adds `openssl:libcrypto_shared` to
  external_deps.
