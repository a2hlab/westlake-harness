==============================================================================
  OH BMS / installd / ability_runtime / appspawn Patches for Android APK
  Installation and Launch Support
==============================================================================

Overview:
  These patches extend OpenHarmony so that raw Android APKs can be installed
  by `bm install -p foo.apk` and launched by `aa start`. The architecture is
  intentionally layered:

    * BMS (Bundle Manager Service) detects the `.apk` suffix, dispatches to
      `libapk_installer.so` for manifest parse / verification, and then uses
      `InstalldClient` IPC to publish files to
      `/data/app/el1/bundle/public/<pkg>/`.

    * installd adds `ExtractFileType::APK_RESOURCES_HAP` and
      `ExtractFileType::APK_NATIVE_SO` so the resources HAP and native libs can
      be synthesized in the privileged `installs` domain.

    * ability_runtime reads `BundleType::APP_ANDROID` from the registered
      `InnerBundleInfo` and routes spawn requests to `appspawn-x` instead of the
      standard OH appspawn.

    * appspawn client headers are extended with the `APPSPAWNX_SERVER_NAME`
      constant and related spawn message fields.

  All patches are applied idempotently by `restore_after_sync.sh` phases B11
  and B12 using `git apply --check` / `git apply`.

Patch Files (maintained under ohos_patches/):

  Bundle Manager Service (BMS):
    foundation/bundlemanager/bundle_framework/interfaces/inner_api/appexecfwk_base/include/application_info.h.patch
      - Extends ApplicationInfo fields needed by Android apps (debuggable,
        primaryAbi, nativeLibraryPath, etc.).

    foundation/bundlemanager/bundle_framework/services/bundlemgr/src/base_bundle_installer.cpp.patch
      - Detects `.apk` inputs in BaseBundleInstaller::ProcessBundleInstall.
      - Accepts a pure list of APK inputs and processes each APK as its own
        independently published install unit; mixed APK/HAP/APP lists fail.
      - dlopen("libapk_installer.so") and calls oh_adapter_install_apk_with_manifest.
      - Parses returned JSON manifest, routes all filesystem writes through
        InstalldClient IPC, allocates AccessToken, builds InnerBundleInfo with
        BundleType::APP_ANDROID, and persists it reboot-safe. The registered
        app codePath is the package-owned root so normal BMS uninstall removes
        base.apk, entry.hap, and extracted native libraries together.

    foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_installer.cpp.patch
      - Historical / alternative `.apk` dispatch path. It is intentionally not
        in restore_after_sync.sh's active patch list because its C ABI is
        disabled and would create a competing admission route.

    foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_data_mgr.cpp.patch
      - Allows Android bundle records to be queried / updated by BMS.

    foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_util.cpp.patch
      - Utility helpers used by the Android install path.

    foundation/bundlemanager/bundle_framework/services/bundlemgr/src/ipc/extract_param.cpp.patch
    foundation/bundlemanager/bundle_framework/services/bundlemgr/include/ipc/extract_param.h.patch
      - Adds APK_RESOURCES_HAP / APK_NATIVE_SO extract types.

    foundation/bundlemanager/bundle_framework/services/bundlemgr/src/installd/installd_operator.cpp.patch
    foundation/bundlemanager/bundle_framework/services/bundlemgr/include/installd/installd_operator.h.patch
      - Installd-side dispatcher for APK resource HAP and native SO extraction.

  Ability runtime (AMS spawn routing):
    foundation/ability/ability_runtime/services/appmgr/src/app_mgr_service_inner.cpp.patch
      - In StartProcess, routes BundleType::APP_ANDROID to the Android spawn
        client (-> appspawn-x).

    foundation/ability/ability_runtime/services/appmgr/src/remote_client_manager.cpp.patch
    foundation/ability/ability_runtime/services/appmgr/include/remote_client_manager.h.patch
      - Adds AndroidSpawnClient / GetAndroidSpawnClient() plumbing.

    foundation/ability/ability_runtime/services/appmgr/src/app_spawn_client.cpp.patch
      - Reserved / historical; currently empty because APPSPAWNX_SERVER_NAME
        handling is already present in the upstream snapshot.

    foundation/ability/ability_runtime/services/abilitymgr/...
      - Mission / ability record adjustments for Android bundle lifecycle.

  AppSpawn client headers:
    base/startup/appspawn/interfaces/innerkits/client/appspawn_client.h.patch
    base/startup/appspawn/interfaces/innerkits/client/appspawn_client.c.patch
    base/startup/appspawn/modules/module_engine/include/appspawn_msg.h.patch
    base/startup/appspawn/interfaces/innerkits/include/appspawn.h.patch
      - Add / extend appspawn-x related constants and message fields.

Canonical adapter sources copied into OH tree by restore_after_sync.sh B10:
  - framework/package-manager/jni/apk_manifest_parser.{cpp,h}
  - framework/package-manager/jni/axml_parser.h
  - framework/package-manager/jni/apk_signature_verifier.{cpp,h}
  - framework/package-manager/jni/apk_verify_result.h
  - framework/package-manager/jni/permission_mapper.{cpp,h}
  - framework/package-manager/jni/native_payload_inspector.h

  NOTE: adapter_apk_install_minimal.cpp is dead code. It implemented
  ProcessApkInstall() which has no caller since the install path moved to
  libapk_installer.so. It has been removed from the libbms source list and
  from B10 deployment.

Dependencies:
  - framework/package-manager/ module builds `libapk_installer.so`.
  - minizip, OpenSSL (libcrypto_shared).
  - framework/appspawn-x/ (Android process spawner).

Application Order:
  Run `bash restore_after_sync.sh --only-oh` after a fresh repo sync.
  Phases B8 (BUILD.gn), B10 (canonical source deploy), B11 (BMS), and B12
  (ability_runtime + appspawn) apply the above in the correct order.
