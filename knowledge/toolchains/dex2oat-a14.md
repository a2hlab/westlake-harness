# Fixed dex2oat for the OH 6.1 BMS route boot image

**Status: building (started 2026-09-30 10:30).** When this page says "fixed", every boot image
rebuild uses exactly this dex2oat and this command line. Nobody reconstructs dex2oat again.

## Why this page exists

The board's boot image (9 segments) was produced by a dex2oat whose recipe was never recorded. Every
boot-class fix (tagsoup `Parser.setProperty`, Gallery's `MediaStore.Images.Media.EXTERNAL_CONTENT_URI`)
then turned into hours of archaeology: a static cross-built dex2oat from a branch commit, patched
exemptions, qemu runs. That broke the AGENTS.md rule that every runtime artifact keeps its source,
patches, toolchain hashes and build script.

## Target versions (measured)

- Board `libart.so` 59e1bb45: image version 108, oat version 230 (oc-t4, 2026-09-30).
- AOSP `android-14.0.0_r1`, `_r10`, `_r16`: `kImageVersion` 108, `kOatVersion` 230 (read from the
  art trees on hw248). `_r29` is 239 and `_r50` is 241, so they do not match.
- Chosen: **android-14.0.0_r16**, the newest tag with oat 230 found on hw248.

## Recipe

Machine: hw248 (32 cores, 62 GB). Tree: `/home/alvin/aosp-14.0.0_r16-dex2oat`.

```sh
export REPO_URL=https://mirrors.tuna.tsinghua.edu.cn/git/git-repo
repo init --repo-rev=stable -u https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/platform/manifest \
  -b android-14.0.0_r16 --depth=1 --no-clone-bundle
repo sync -c -j16 --no-tags --no-clone-bundle --fail-fast
# next steps, filled in as they are done:
# source build/envsetup.sh && lunch <target> && m dex2oat   (host tool, out/host/linux-x86/bin)
# repo manifest -r -o pinned-manifest.xml
```

## To record when done

- Pinned manifest (`repo manifest -r`) committed next to this page.
- SHA-256 of `dex2oat64` and every host library it loads (`ldd`), and of the prebuilt clang used.
- The exact dex2oat command line that reproduces the board's 9 segments, taken from the board
  `boot.oat` key-value store (`dex2oat-cmdline`), and the per-segment checksum comparison.
- Once the 9 segments reproduce, register the tool in `knowledge/frozen/` so it cannot drift.
