# Fixed dex2oat for the OH 6.1 BMS route boot image

**Status: the most promising path, not yet confirmed.** It becomes the confirmed, final path only
when the reproduction below passes and the recipe, hashes and command line are recorded and frozen.
Until then nothing downstream (tagsoup, Gallery's MediaStore field) may be declared solved by it.

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

## Inputs (measured 2026-09-30 10:50)

The boot image is **9 segments over 9 jars**, in this order of files under
`/system/android/framework/`: core-oj (boot.*), core-libart, core-icu4j, bouncycastle, apache-xml,
okhttp, framework, oh-adapter-framework, adapter-mainline-stubs. The 9 jars and all 27 image files
(`arm64/boot*.{art,oat,vdex}`) are **byte-identical on 5cd, 5ea and 61b**; the SHA-256 list is in
`boot-image-inputs.sha256`. Earlier reproduction attempts fed 5 jars, which is not the board's input
set. The 715/723 String sizes that suggested the boards differ were garbage reads.

## Risks, and how each is closed

1. **The board libart carries our own patches.** `libart.so` 59e1bb45 is the R155 build (route-a,
   from pr03-74e6-portable); its source and patch series were never archived, and rebuilding from the
   frozen inputs produced a different libart (be688d0f, DIGEST E.7). If those patches change object
   layout or the image format, an official dex2oat's image will be rejected. Checks, in order:
   (a) compare the layout-defining constants of the board libart with an official android-14.0.0_r16
   arm64 libart built from the same tree (Thread offsets used by the asm entrypoints, mirror class and
   object sizes, ImageHeader/OatHeader layout); the String layout already matches (oc-t4);
   (b) the board test in step 2 of the acceptance levels. If either fails, recover the R155 patch set
   (hw248 Westlake build archives, real-work) and build dex2oat with the same patches.
2. **Byte-identical reproduction may not be possible** (different tag or flags in the original run).
   Acceptance has two levels:
   - L1 (ideal): all 27 files byte-identical to `boot-image-inputs.sha256`.
   - L2 (minimum): oat version 230 / image version 108, the boot-image checksum and header fields that
     libart validates match, and in a short board window (overlay the 27 files, then roll back) HW,
     ZigZag and at least five currently lit apps still show their own UI at t20.
3. **Input jars might differ between boards**: checked, they do not (see Inputs).

## Recipe

Machine: hw248 (32 cores, 62 GB). Tree: `/home/alvin/aosp-14.0.0_r16-dex2oat`.

```sh
export REPO_URL=https://mirrors.tuna.tsinghua.edu.cn/git/git-repo
repo init --repo-rev=stable -u https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/platform/manifest \
  -b android-14.0.0_r16 --depth=1 --no-clone-bundle
repo sync -c -j16 --no-tags --no-clone-bundle --fail-fast
# sync finished 2026-09-30 10:55, 111 GB
repo manifest -r -o pinned-manifest.xml     # pinned project revisions, copy kept next to this page
source build/envsetup.sh && lunch aosp_arm64-userdebug
m -j32 build-art-host libart                 # host dex2oat set + arm64 libart for the R155 layout check
```

## To record when done

- Pinned manifest (`repo manifest -r`) committed next to this page.
- SHA-256 of `dex2oat64` and every host library it loads (`ldd`), and of the prebuilt clang used.
- The exact dex2oat command line that reproduces the board's 9 segments, taken from the board
  `boot.oat` key-value store (`dex2oat-cmdline`), and the per-segment checksum comparison.
- Once the 9 segments reproduce, register the tool in `knowledge/frozen/` so it cannot drift.
