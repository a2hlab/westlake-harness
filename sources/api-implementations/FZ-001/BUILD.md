# Build and dependency boundary

The source archive SHA is `aaf8165cd8ac1b1b7f48f5656cb349dd0a2bc908fec2f68c8b6a9e75b91ff3dd`; both contained SO files matched the frozen registry before extraction. No SO is delivered. Final `base_bundle_installer.cpp` SHA is `9acb43858dd43c4d1898f2e2a7ef4b960e2719c9c17f758b7826512c9989225a`; the older cc-wiki input c96e992d is not this final production file.

Acquire the original kit/archive using your configured host and root (not an agent worktree):
```bash
scp "$HW248_HOST:$HW248_HOME/westlake-oh6.1-installer-background-launcher-6aadb8b4/westlake-installer-background-launcher-6aadb8b4-source.tar.gz" .
scp "$HW248_HOST:$HW248_HOME/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/oh61-bms-kit-b79-r3-final.tar.gz" .
```
Check archive hashes from `build-evidence/archive.json` before unpacking. B79 kit SHA is `61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6`; compiler SHA is `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913`. The B89 network baseline and final 6033-byte patch remain explicit, not inferred from the older baseline kit alone.

Installer: `OH_ROOT=... AOSP_ROOT=... BUILD_OUT=/new/scratch ./build.sh`. The source copy stays isolated in BUILD_OUT. BMS: restore a new scratch kit, overlay the final delivered BMS source and permission header at the original paths, and invoke `tool-bin/ninja -C out/wukong100 -d keeprsp -v -j2 bundlemanager/bundle_framework/libbms.z.so`; the exact original rules and build stdout are in `build-evidence/`. Those historical paths must be relocated in the scratch kit; this task does not claim a cold build from the patch alone.
