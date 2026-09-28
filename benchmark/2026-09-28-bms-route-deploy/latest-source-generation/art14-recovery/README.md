# AOSP14 frozen-source recovery and local build evidence

Treating the provider-v12 binary snapshot as a reproducible source tree was
incorrect. Its manifest contains modified AOSP14 sources, generated files,
mixed dependency revisions, Git metadata, and a different compiler. Recovering
the C++ sources alone does not reproduce the frozen provider bytes.

The source manifest SHA256 is
`84ddec0e2dbbc249d6f7ef912663b015356500272f1ce9647302dd936b319ef1`.
The initial inventory recorded **16,908/18,060 exact, 350 missing, 802 different**.
The final inventory is **16,909 exact, 348 missing, 803 different**
(`restoration-comparison-final.json`).
At the initial inventory the only *existing* C/C++ source/header mismatch was
`art/libnativeloader/include/nativeloader/native_loader.h`. Missing generated
headers, backups and build metadata are retained in the report; they are not
silently counted as verified. See `restoration-comparison.json`.

## Exact recoveries

- All 71 Android 14 tags reduce to five unique trees. Comparing all 9,819 ART
  entries ranks r1 first: 9,005 matches, versus r10 8,996; r16 8,993; r29 7,982;
  r50 7,400. Source commit: `3c05e56adf5b268ec5b20bf8aec460815e45161c`.
- Existing Hanbin patch subsets recover 15 modified C/C++ files byte-for-byte.
  In particular, older `runtime.cc.patch` hunks 4–11 produce `077582e9…`.
  The later JIT and OH_PROBE changes are excluded. Receipts retain patch SHA256
  and selected hunk numbers; `recover_patch_subsets.py` writes only exact matches.
- Extracting CLI_CP, OAIDF_CP, AIS_CP, ABCP_CP and RDFL_CP diagnostics from the
  `25fed424…` historical copy and restoring their active fprintf calls produces
  **class_linker.cc = 2c801ab0…**. No later vtable or GC changes are included.
  `class-linker-exact.patch` and `class-linker-receipt.json` record the result.
- tinyxml2 cpp/header are upstream commit
  `418229dc5ca6943294378556a0208578dd48064a`: **4da3fcc2… / 665fc63d…**.
  Inferring their revision from the frozen Android tag refs was incorrect.
  `Android.bp` and `tinyxml2.h.stub` are absent at that commit; neither is
  claimed recovered. Their expected hashes are in `tinyxml2-main-recovery.json`.
- The frozen lzma source files match Android 16 r3. This dependency revision
  does not change the ART selection: ART remains Android 14 r1.

All new downloads were individual projects on the designated download host;
no full repo sync or remote build was performed. Sources were copied back for
local builds. Paths in published receipts use account-neutral placeholders.

## Remaining header and build results

The bounded native_loader.h search did not recover `519e1476…`. The authorized
r1 fallback remains in staging. A compiler `-H` probe, using the recipe's
include order, selects the adapter's native-loader-oh header ahead of that
AOSP header (`native-loader-header-resolution.txt`). This verifies header
selection for the probe; it does not establish a full linked ABI match.

The local dockbuild run uses the existing provider recipe with strict undefined
symbol checks. The recovered SDK needs its existing native-libc++ compatibility
switch and declarations for two objects already exported by SDK libc. The
original source files remain unchanged by those build adjustments. Original
OH provider bytes are used as link inputs, following import_inputs.sh.

The historical `build-r4.txt` documents an intermediate failure, not the final
build. The authorized compiler is now OH 6.1 clang **b107ce03**. Because the
historical compiler cannot be recovered, the outer reviewer changed Gate 2 to
functional equivalence: exports, NEEDED, SONAME and sections must be compared
against actual R155 files. Byte equality is informational. Identity enforcement
still uses the newly built files' actual SHA256 and Build-ID.

Current local results:

- ART **245/245** compiled, 24 provider libraries strictly linked (`build-r8.txt`).
- Musl special-slot sigchain rebuilt with the same compiler: **6d5d5538…**.
- Latest bridge **55 units**, strictly linked (`bridge-strict.txt`). Its old
  recipe included two CLI main programs and omitted three account JNI units;
  `bridge-source-inventory.patch` records the source inventory corrections.
- ICU **199/199** and androidfw **26/26**, strictly linked. The three existing
  real-work androidfw patches were applied unchanged (Entry completeness and
  IncFsFileMap assertion compatibility).
- Latest native runtime strictly linked and passed its Profile B edge check
  (`runtime-strict.txt`). The old recipe omitted existing AudioTrack JNI code;
  it now uses that implementation and the OH native-window library explicitly.
- The missing procinfo header uses unmodified Android14 r1. This is an explicit
  source deviation, not an exact recovery (`procinfo-recovery.json`).

`provider-abi-comparison.json` inventories the first complete provider build.
ART has the same NEEDED list but four fewer R155 exports, including a diagnostic
method and inline/type-resolution symbols; these require consumer review.
No blanket claim that all differences are diagnostics is made. Production
palette and zlib were rebuilt by the complete-generation recipe. Initial SDK
zlib linkage was corrected by source relinking to `libshared_libz.z.so` before
final sealing (`zlib-relink.json`); no binary patch was used.

## Completed verification and later trials

The 26 original provider outputs reproduce over two complete builds
(`provider-repro.json`). OpenJDK JVM was added and reproduced separately
(`openjdkjvm-repro.json`). `final-abi-comparison.json` inventories the final 33
libraries. Final NEEDED closure is 34 required / 338 reachable / 3,023 edges,
with zero unresolved (`final-closure.json`). Four original closure negatives and
a false absent-SONAME declaration reject; four missing-sigchain-export controls
also reject (`closure-negatives.json`, `new-art-sigchain-symbols.json`).

Generation/TGR verification passed with only the explicitly authorized tuple
receipt waiver. Latest00 activation failed HelloWorld because its entry is an
unconditional -3007 stub; all 36 mounts were rolled back and B5 HelloWorld and
ZigZag screenshots restored. The follow-up real-work entry is implemented but
requires an ART symbol absent from the fixed provider, so its strict link failed
before another deployment. See the parent README and `../real-work-entry/`.

Source integrity controls reject mutated and missing input. Fresh B6 lifecycle
is 3 pass / 5 fail, as recorded by the parent report. Source recovery itself
performed zero board operations; the later complete-generation trial did write
5ea and was entirely rolled back. R2 host/source evidence is verified; repaired
VM boot compatibility, Wikipedia UI and NPE conversion remain unverified.
