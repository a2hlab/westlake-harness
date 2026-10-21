# G08-BUILD-PREFLIGHT — shortest narrow rebuild of libinstalls.z.so for a zip_file.cpp fix (not built)

Offline, read-only preparation for the cx fix of the G06 first blocker
(`zip_file.cpp(CheckEndDir:71) endDir.numDisk != 0` in `libinstalls.z.so` 51e1b525). No build, device or REA.

## What existing tooling does and does not cover

- `sources/api-implementations/JAVA-042-installer/build.py --check-only` → rc 0 (source pins + archive
  `61ff2def…`, 478 511 698 B, 8 873 members). Its full mode extracts a fresh kit, checks clang-15 `b107ce03…`,
  touches `base_bundle_installer.cpp`/`installd_operator.cpp` and runs ninja for `libbms.z.so` + `libinstalls.z.so`.
- **It cannot carry a zip_file.cpp fix.** `out/wukong100/installs.ninja` (`9952d7d4…`) has only two edges:
  `cxx installd_operator.o` and `solink libinstalls.z.so`. `zip_file.o` (`2e2a6247…`) and `base_extractor.o`
  (`1f650cb8…`) are prebuilt link inputs listed in `libinstalls.z.so.rsp`.
- The kit's main tree has only `zip_file.h`/`base_extractor.h`. The source lives at
  `verified-seed/private-source/oh/.../bundlemgr/src/zip_file.cpp` (`1fa70c83…`); its line 71 is
  `APP_LOGE("endDir.numDisk != 0")` in `ZipFile::CheckEndDir`, matching the device log. The seed out-overlay
  `zip_file.o` is byte-identical to the kit's (`2e2a6247…`). The compile command is
  `verified-seed/metadata/narrow-commands/zip_file.cmd` (246 args, `/usr/bin/ccache …/clang++`, cwd `out/wukong100`,
  `-c ../../foundation/.../src/zip_file.cpp -o obj/.../parser_common/zip_file.o`, aarch64-linux-ohos, no prefix map).
- `base_extractor.cpp` source is **absent** from the archive: a fix that must change base_extractor cannot be built here.

## Environment

Use OrbStack `a2hlab`: x86_64, Python 3.12.3, `/usr/bin/ccache`, archive readable via `/mnt/mac/...`.
hw248 has Python 3.10.12 and cannot run `build.py` (it uses `tarfile` `filter='fully_trusted'`, 3.12+).

## Shortest recipe after cx delivers the patch (`results.json.recipe`)

1. New `$SCRATCH` on a2hlab; persistent `$LOG = $HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/build-runs/<run-id>`
   (Mac side); tee every step's stdout/stderr/rc there at run time.
2. `build.py --check-only`, then `tar -xzf $ARCHIVE -C $SCRATCH`; verify clang-15, `zip_file.cmd`, seed source SHAs.
3. Copy the seed `zip_file.cpp` to `$KIT/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/`.
4. **Baseline** (unpatched, `CCACHE_DISABLE=1`, cwd `out/wukong100`): run `zip_file.cmd` → expect `2e2a6247…`;
   `tool-bin/ninja -d keeprsp -v -j2 bundlemanager/bundle_framework/libinstalls.z.so` → expect `51e1b525…`.
   A mismatch is recorded and makes binary equivalence unproven; it is not edited away.
5. Apply the cx patch to that `zip_file.cpp`; repeat the compile + relink; record both libinstalls SHAs.

## Gaps

cx patch; base_extractor.cpp source; compile/link reproducibility (steps 4) unproven; seed `zip_file.cpp` not in
`source.lock.json`; hw248 archive copy not SHA-checked here. Raw receipts:
`$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/build-preflight/raw/b01–b06`.
