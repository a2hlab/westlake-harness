# APK network permissions: preserve declarations through BMS and ATM

Previously, adding supplementary gid 3003 did not clear Wikipedia's `missing INTERNET permission` / `getaddrinfo EPERM` wall (cc-wiki's device observation). The APK parser already collected `usesPermissions`, but its C-entry JSON omitted them. The BMS APK branch manually built `InnerModuleInfo` and called `AllocHapToken` with an empty permission policy, bypassing normal HAP permission registration. Changing only the generated resource HAP would leave both BMS records and ATM unchanged.

This candidate connects all three representations: the generated HAP's `module.requestPermissions`, BMS's persisted `InnerModuleInfo.requestPermissions`, and ATM's fresh-token `permStateList`. It maps only Android `INTERNET` and `ACCESS_NETWORK_STATE` to OH `INTERNET` and `GET_NETWORK_INFO`. Undeclared/unrelated requests never acquire these permissions; duplicates are removed. It uses OH's normal `InitHapToken` system-grant processing, starting permission states at `PERMISSION_DENIED` with `PERMISSION_DEFAULT_FLAG`, not forcing grants.

## Evidence and limits

- Real production C++ HAP packing passed on the pinned original Wikipedia `eba82a0f…` and Noice `8e11b313…` APKs. Both output exactly their two declared mapped permissions. See `host-hap-results.json`; APK bytes were not edited.
- Five mapping assertions cover empty/unrelated/malformed requests, duplicates, one permission and both permissions. Four deployment tests cover exact apply/rollback, failure midway through apply, wrong baseline and changed candidate.
- Installer compiled **31/31** translation units. Both libraries passed their existing strict undefined-symbol link. Dynamic NEEDED order, SONAME and flags are unchanged versus their build baselines; no exports were removed. Installer adds standard libc/libc++ JSON-parser imports and 106 exported template instantiations; BMS drops the unused `AllocHapToken` import and already imported `InitHapToken`. See `elf-diff.json`.
- Repository known-answer tests: **69 run, 2 skipped, 0 failed**. B8 lifecycle: **6 Skip**, all selectors match zero tests; this is not lifecycle acceptance. Board #89 explicitly authorizes the installer/5ea handoff beyond the generic B8 Java-only wording; no spec was edited.
- **R2 partially:** offline evidence verified; no board writes by cx-t0. ATM grants, DNS, screenshot content and regression results remain **unverified**, owned by cc-wiki. Screenshot/alive counts: **unknown**, not inferred from planned tests.

## Provenance and implementation

Base repository commit: `2e5bdd73c5afa46693e159812554a2644f482d3e`. Exact two mappings already exist in `bms/src/adapter/framework/package-manager/jni/permission_mapper.cpp`. The requested-permission state construction and four-argument token initialization are copied from OH 6.1 `BundlePermissionMgr::GetPermissionStateFullList` / `InitHapToken`: `/opt/build-trees/oh610_lts_source/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_permission_mgr.cpp`. The excerpt and source SHA are in `oh_permission_provenance.txt`.

Changes are in `apk_network_permissions.h`, `apk_installer.cpp`, `oh_adapter_install_apk_c_entry.cpp`, and `base_bundle_installer.patch` for the external OH build kit. The shared header must also be copied beside OH's `base_bundle_installer.cpp`. The C-entry schema requires the new array, so both libraries must be replaced before restarting services. Reusing an existing APK token with a different network-permission set is rejected with a clean-reinstall diagnostic. This task's `bm uninstall` followed by install avoids silently retaining an old ungranted token. General permission-update transactions are not implemented here.

The candidate inherits accepted B79 1 MiB manifest buffering / APK routing and B7 XML-only icon fallback. Installer baseline rebuilt from current sources is `d555bd73…`; it is not the board's old `675536e8…`. Rollback uses actual board backups, never a rebuilt approximation. `libinstalls`, runtime providers, JAR and host are unchanged.

## Build and persistent inputs

All compilation ran locally through `dockbuild.sh`. OH clang-15 SHA: `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913`. Recipes: `build-bms.sh`, `build-installer.sh`; host developer test: `run_host_test.sh`.

Base BMS kit: `/home/alvin/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/oh61-bms-kit-b79-r3-final.tar.gz`, SHA `61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6`. Preserve its frozen APK route objects and link recipe. Do not substitute the stock OH output objects.

Delta: `/home/alvin/westlake-oh6.1-b89-network-permissions-6f94d4f4/westlake-b89-network-permissions-6f94d4f4-source.tar.gz`, SHA `8d60bc40bfa8ff1ddac3a0204aa0eae0c68474555827006f692e472825de0fca`. It contains the full installer source slice, build scripts, installer OH header/link-input kit, exact BMS before/after source and patch, output libraries and raw build/ELF evidence. The identical Mac archive is under `/Users/zhaoyue/orca/workspaces/`. Existing SDK symlinks resolve to the dockbuild toolchain; restore at the paths specified in scripts or rebase those local path variables consistently.

To replay: restore the B79 base kit, apply `base_bundle_installer.patch`, copy `apk_network_permissions.h` next to that source; restore archive `adapter/` to `bms/src/.work/b89-network-permissions/adapter` and the installer kit to `oh61-bms-kit`. Run the two scripts with `DOCKBUILD_MOUNTS=/Users/zhaoyue/orca/workspaces dockbuild.sh run -n <name> -- bash <script>`. Require `Compiled: 31/31`, no compilation errors and successful strict links. The host test runs actual resource packing using Linux g++, OH minizip and the existing Linux `libz.so.1`.

## Deployment ownership

Mac-readable package: `/Users/zhaoyue/orca/workspaces/westlake-b89-network-permissions-6f94d4f4`. Full identities and commands are in [HANDOFF.md](HANDOFF.md). The script accepts only cc-wiki's 5ea lock. Announce the foundation restart; replace each library at both aliases, restart, verify foundation-root hashes/maps, and reinstall both APKs. Reboot requires cc-wiki's normal runtime/host/JAR replay. Rollback restores exact files but does not undo installed-package database or token changes.
