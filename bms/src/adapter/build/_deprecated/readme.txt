Build Scripts Directory
=======================
Updated: 2026-04-11 (晚间清理)
Target:  DAYU200 (RK3568, ARM32 userspace) — current
Future:  DAYU600 (UMS9620, ARM64) — migration target, not current
Host:    ECS cloud server (oh-build: HanBingChen@1.95.175.212)

This directory contains all build scripts for the Android-OpenHarmony adapter
project. Scripts run on the ECS cloud server (~/adapter/build/). The local
copy (D:\code\adapter\build\) is a backup/mirror synced from ECS via scp.

The one-command entry is restore_after_sync.sh followed by oh_full_build.sh
(see doc/build and deployment design.html appendix Z for full choreography).


==============================================================================
0. SINGLE-COMMAND RECOVERY (always run first after repo sync)
==============================================================================
restore_after_sync.sh           12-phase orchestrator (A1-A9, B1-B8, C1, POST1/2)
                                Applies all patches + deploys stub files +
                                fetches missing AOSP source trees + cross-
                                compiles minikin stack. Idempotent. See doc
                                appendix Z.1 for phase table.

check_placeholder_patches.py    CI gate: fails if any .patch contains
                                literal `@@ -xxx,N +xxx,M @@` placeholder.
                                Called by restore_after_sync.sh pre-flight.


==============================================================================
1. SHARED CONFIGURATION
==============================================================================
config.sh                       Shared env vars: OH_ROOT, OH_PRODUCT_NAME,
                                5 build targets, patch mappings
build_env.sh                    AOSP build environment (source this before
                                `m framework-minus-apex`)
synced_repos.txt                115 AOSP projects that are in partial sync


==============================================================================
2. OH SYSTEM SERVICES BUILD (Category 1)
==============================================================================
oh_full_build.sh                >>> MAIN ENTRY for OH build <<<
                                Builds 5 targets: abilityms, libappms,
                                scene_session_manager, scene_session, libbms
                                Auto-fixes the musl SYS_* syscall.h bug.
                                See doc appendix Z.8 for full explanation.

apply_oh_patches.sh             Apply ohos_patches/ via `patch -p1`
revert_oh_patches.sh            Revert (for iterative dev; rarely used)
collect_oh_artifacts.sh         Copy .z.so from ~/oh/out/rk3568/ to
                                ~/adapter/out/oh-service/


==============================================================================
3. AOSP NATIVE CROSS-COMPILATION (Category 3)
==============================================================================
cross_compile_arm32.sh          Cross-compile ~22 AOSP native .so to
                                out/aosp_lib/ using OH clang + musl sysroot
                                (libart, libandroid_runtime, libbase, libcutils,
                                libutils, libnativehelper, liblog, libziparchive,
                                libdexfile, libartbase, libprofile, libsigchain,
                                libtinyxml2, libnativebridge, libelffile, libvixl,
                                libunwindstack, libartpalette, libbionic_compat,
                                libcxx-ohos, libcxxabi-ohos, ...)

cross_compile_minikin_stack.sh  Cross-compile minikin text-layout stack to
                                out/aosp_lib/ (libft2, libicuuc, libicui18n,
                                libharfbuzz_ng, libminikin, libandroidfw).
                                Added 2026-04-11 to resolve P10.C.full.
                                Uses --only=libxxx for incremental rebuild.

aosp_build_patches/
  fetch_minikin_deps.sh         git-clone frameworks/minikin +
                                external/harfbuzz_ng + external/freetype
                                from Tsinghua AOSP mirror (ECS has partial
                                sync; these are filtered by groups="pdk*")
  install_app_spawn_x_init.sh   Mirror AppSpawnXInit.java from
                                framework/appspawn-x/ into AOSP source tree
                                (called by restore_after_sync A3b)
  *.patch                       18 AOSP source patches (build_make, art,
                                frameworks_base, 9 modules_*.patch, etc.)


==============================================================================
4. ADAPTER JAVA / JAR (Category 2 & 4)
==============================================================================
compile_oh_adapter_framework.sh >>> MAIN ENTRY for jar build <<<
                                Compiles oh-adapter-framework.jar using jdk17
                                javac + turbine header jars (Soong-bypass
                                because `m oh-adapter-framework` is blocked
                                by unrelated SystemUI license analysis error).
                                Output: out/adapter/oh-adapter-framework.jar
                                (~136 KB, 31 classes incl. AppSpawnXInit)

generate_pma_stubs.py           Auto-generate 109 IPackageManager.Stub
                                abstract method overrides from javap output,
                                inject into PackageManagerAdapter.java
                                (770 → 1504 lines)

Android.bp                      AOSP Soong build definition (legacy,
                                Soong-bypass path above is now primary)

apply_patches.sh                Apply aosp_patches/ via `patch -p1`
apply_aosp_java_patches.py      L5 reflection injection into 4 AOSP
                                framework .java files (reflection-based
                                adapter loading)
auto_build.sh                   Iterative `m framework-minus-apex` with
                                auto-sync when deps missing
save_build_config.sh            Export current AOSP build env to a file


==============================================================================
5. ADAPTER NATIVE C++ (Category 5)
==============================================================================
compile_appspawnx.sh            Build appspawn-x (hybrid spawner executable)
compile_apk_installer.sh        Build libapk_installer.so (standalone lib;
                                currently NOT linked into libbms — its
                                sources are instead pulled directly via
                                BUILD.gn.patch. See adapter_apk_install_
                                minimal.cpp in ohos_patches/bundle_framework/)
compile_oh_graphic_buffer_producer.sh
                                Standalone compile of oh_graphic_buffer_producer.cpp
                                (deprecated — the file is already in
                                framework/jni/BUILD.gn as a source of
                                liboh_adapter_bridge.so; this script is for
                                quick standalone verification only)
compile_rs_surface_helper.sh    P13.2 — compile rs_surface_helper.cpp using
                                OH ninja flags verbatim. Produces a small
                                helper that exposes a C ABI to create an
                                RSSurfaceNode wired to the real RenderService
                                and return its producer OH::Surface* to caller.
                                Part of the Surface buffer routing path
                                (complements android_view_surface_stubs.cpp)


==============================================================================
6. libhwui BUILD PIPELINE
==============================================================================
compile_libhwui.sh              Top-level libhwui compile (not the main path)
compile_libhwui_v9.sh           Phase 1+2 (~63 .o)                 [step 1]
compile_libhwui_jni.sh          Phase 3 JNI (56 .o) + apex/         [step 2]
                                jni_runtime.cpp (provides
                                register_android_graphics_classes)
compile_hwui_stubs.sh           hwui_oh_abi_patch.cpp +     [step 3]
                                hwui_register_stubs.cpp +
                                typeface_minimal_stub.cpp
compile_android_view_surface_stubs.sh
                                3 register_android_view_* in        [step 4]
                                namespace android (not extern "C")
compile_hwui_shims.sh           liboh_hwui_shim.so                  [step 5]
link_libhwui.sh                 Final link: libhwui.so ~2.33 MB     [step 6]

Source files (not in build/ — compiled by above pipeline from their semantic homes):
  aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp
                                 link-time resolver for 6 Skia/minikin symbols
                                 (P10.A/B/C now real — 3 stubs removed)
  aosp_patches/libs/hwui/hwui_register_stubs.cpp
                                 4 register_android_graphics_* for #if 0'd JNI
  aosp_patches/libs/hwui/typeface_minimal_stub.cpp
                                 Typeface JNI register no-ops
  framework/surface/jni/android_view_surface_stubs.cpp
                                 Real vsync timer + Surface Java JNI (P13)
  framework/surface/jni/rs_surface_helper.cpp
                                 P13.2 — C ABI wrapper creating RSSurfaceNode
                                 backed by real OH RenderService, returning
                                 producer OH::Surface* for buffer routing
  framework/surface/jni/surface_oh_helper.cpp
                                 small helper used by android_view_surface
  skia_compat_headers/hwui_force_include.h
                                 -include header for all libhwui .cpp files
  skia_compat_headers/vulkan/vulkan.h
                                 minimal VK header for -DHWUI_NO_VULKAN paths


==============================================================================
7. BOOT IMAGE
==============================================================================
gen_boot_image.sh               Generate ARM32 boot.art / boot.oat / boot.vdex
                                using AOSP Soong host dex2oat + patched
                                framework jars. Auto-includes
                                oh-adapter-framework.jar when available.


==============================================================================
8. SKIA M133 RTTI REBUILD
==============================================================================
skia_rebuild/                   Rebuild libskia_canvaskit.z.so with RTTI to
                                enable cross-.so typeinfo for libhwui. Uses:
  build_skia.py                 full rebuild
  build_skia_deps.py            dependency targets
  build_targeted.py             target-list limited
  link.sh                       final link

skia_compat_headers/            Forced-include headers that bridge Skia M116
                                (AOSP source) ↔ M133 (OH runtime) API diffs.
                                Included via `-include hwui_force_include.h`
                                in libhwui compile scripts.


==============================================================================
9. DEPLOYMENT
==============================================================================
prepare_deploy_package.sh       Assemble out/deploy_package/ from all categories
                                (53 files, ~199 MB). Strips libskia 196 MB →
                                23 MB preserving typeinfo. Includes
                                AppSpawnXInit.class integrity check.

deploy_to_dayu200.sh            Local-Windows hdc-based deploy to DAYU200.
                                Uses OH-native `bm install -p` (NOT Android
                                `pm install`). Supports --dry-run, --apk-only,
                                --skip-libskia, --uninstall.

verify_appspawnx_cfg.sh         Parse appspawn_x.cfg, assert BOOTCLASSPATH
                                integrity + AppSpawnXInit.class presence in
                                oh-adapter-framework.jar. Run after
                                prepare_deploy_package.sh.

_deprecated_push_so.sh          [DEPRECATED 2026-04-17] DAYU600-only (/system/lib64/platformsdk), superseded by deploy_to_dayu200.sh. Kept for reference; do not invoke.


==============================================================================
10. OH BUILD PATCHES
==============================================================================
oh_build_patches/               Patches to OH build system (not source):
  ets2abc_config.gni.patch      Disable ETS SDK deps
  app_internal.gni.patch        Disable ace_js2bundle
  ui_lite_updater_BUILD.gn.patch Disable graphic_utils_lite
  musl_syscall_fix.sh           sed SYS_* aliases into generated syscall.h
                                (called by oh_full_build.sh — see Z.8.5)

ninja_patches/                  Phony-edge patches for OH ninja graph:
  apply_all.sh                  Entry; calls the 3 patch_*.sh scripts
  patch_irtoc.sh                Phony irtoc target (segfault workaround)
  patch_arkruntime.sh           Phony libarkruntime (not needed by project)
  patch_ani_helpers.sh          Phony libani_helpers (not needed by project)

device/                         AOSP custom product definition
  adapter/oh_adapter/           oh_adapter-eng product (minimal, no system_server)


==============================================================================
11. PATCH APPLICATION HELPERS
==============================================================================
patch_dex2oat_apex.py           Inject `"//apex_available:platform"` into
                                apex_available blocks of AOSP Android.bp
                                files (art, libcore, external). Called by
                                the dex2oat host build chain.


==============================================================================
12. DEPRECATED (moved 2026-04-11, safe to delete if space reclaim needed)
==============================================================================
_deprecated/
  hwui_increment_scripts/       32 files — 30+ Python scripts and
                                hwui_phase2_batch_fix.sh. These have been
                                sedimented into
                                aosp_patches/libs/hwui/hwui_rk3568.patch
                                (1263 lines, 47 files). restore_after_sync.sh
                                phase A9 now uses `git apply` on the patch
                                instead of calling these scripts.

  checkpoint_scripts/           3 files (add_checkpoints / insert_checkpoints /
                                insert_checkpoints2) — one-time debug helpers
                                that injected checkpoint printfs into OH/AOSP
                                sources during the stub-tracking era.

  oneshot_fixes/                3 files — fix_appspawnx.py, fix_cross_compile.py,
                                _remove_a7.py — served their purpose, no
                                longer needed.

  legacy_compile_scripts/       4 files:
    compile_libhwui_phase1.sh   Superseded by compile_libhwui_v9.sh +
                                compile_libhwui_jni.sh
    cross_compile_100pct.sh     ARM64/DAYU600 variant; current target is
                                rk3568/ARM32
    oh_build.sh                 Superseded by oh_full_build.sh (latter has
                                auto musl SYS_* fix)
    deploy.sh                   DAYU600-era deploy script; superseded by
                                deploy_to_dayu200.sh

  (pre-2026-04-11 content)      cross_compile_layer2.sh, dayu210_config.json,
                                fix_and_build.py, fix_oh_build.py,
                                fix_pma_stubs.py, gen_patch_diff_report.py,
                                oh_build*.log
                                — earlier deprecation round


==============================================================================
SUMMARY
==============================================================================
Scripts at top level:           ~35 (was ~80+ before 2026-04-11 cleanup)
Subdirectories:                 7 (_deprecated, aosp_build_patches, device,
                                ninja_patches, oh_build_patches,
                                skia_compat_headers, skia_rebuild)
C++ source files in build/:     0 (moved to aosp_patches/libs/hwui/ and
                                framework/surface/jni/ on 2026-04-11 late
                                cleanup — build/ is now scripts + config only)
Config files:                   3 (config.sh, build_env.sh, Android.bp)
Meta:                           2 (readme.txt, synced_repos.txt)

For the authoritative 2026-04-11 build state description, see
doc/build and deployment design.html appendix Z.
