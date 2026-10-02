# U12 private zlib: copy the reviewed route, do not redesign it

## Actual first fatal and prediction

Window5 BurgerKing PID 570/TID 604, original hilog **19583–19587**:
`libmmkv.so` needs `libz.so`, not found in **westlake.anl.app.570.3**;
NitroMmkv load throws, APPSPAWN exits 1 at **19919**. The real consumer mmkv
SHA **d19d1957…** needs libz and imports **crc32**. Exact provider **ab0820c6…**
exports it. This is a private namespace search failure, not an absent policy
name: libz already belongs to the seven shared SONAMEs.

Predict **one conditional first-fatal movement (BurgerKing)**. Element remains
in the reviewed two-package route but is not counted as another currently moved
first fatal. Remaining NitroMmkv relocations/JNI_OnLoad, private libandroid
selection and next fatal/t20 are **unknown**, not a new-lit claim.

## Original implementation reused verbatim

Local reviewed `benchmark/2026-10-02-u11-native-batch/` is the donor. Candidate
host source and route header are copied byte-for-byte; `build-receipt.json`
asserts the reviewed source SHA, snapshots it and all **73** compile inputs.
No remote source lookup needed after finding the reviewed local donor.

- Base: exact deployed r3 **65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284**,
  retained source **507bf160…** and unchanged resident-compat header.
- Rebuilt host **2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e**,
  two identical builds from the copied reviewed implementation. The original
  67753f77 comparison used another source path; this candidate's source/debug
  paths differ, not its intended route implementation.
- Alias **50b9ab6af637c8573736a595417f6177d5845d21fc48da5b8e1299a078b1e48d**,
  SONAME libz, NEEDED libshared_libz.z. Original local r109c recipe is
  real-work commit **be16148da9ae7bb89c62e81e144ed0bceb5c4669**, function
  `build_android_zlib_soname_alias:581`, pinned in sources.json and excerpt.
- Unchanged existing deployed provider **ab0820c6a33c58f2b5aa6d7b5f967f0eae42319baa2d7a42b779d1583f8a14fc**,
  SONAME libshared_libz.z, NEEDED libc only. It is copied, not rebuilt. The U9
  ROUTE_A_INPUTS dependency `d88df…` is **not** this ELF; do not invent a
  byte-exact build provenance from that different receipt.

One rebuilt runtime file (host); two already-existing donor files copied only
under **westlake_native**. Never add a root libz alias, never add a policy name.
Exact package-component checks retain `im.vector.app` and BurgerKing only;
similar-prefix/suffix apps fail negative controls. Keeping
`u11_original_search` for the old private-branch condition is essential: adding
the route must not reclassify every target into another owner-inherit branch.

## Static-first deltas

WHOIS ran before comparison; its U9 coverage is historical, current host r3
identity is independently checked against the U10.1T8 package. Host scans
**8 -> 8 open sites**, **17 -> 17 namespace edges**, **four unchanged source
inherit calls**, **INHERIT-REPEAT 0 -> 0**. Four existing INHERIT-AFTER-OPEN
syntactic may-paths remain (two opens against each of the bridge/compat
inherit edges). They are not new reachable operations from the zlib edit.
All raw fields, PCs, DEFAULT-NS and possible MULTI-NS are retained; first-edge
shared/parent expressions and stack slots differ in analyzer formatting, not
silently coerced into a proof of named identities. No new owner edge is claimed.

Focused N2 with the original fixed private search/permitted paths (no inherit)
has **one new missing-dt-needed: private libshared_libz.z -> libc.so**. The alias
itself resolves the exact private provider. This is retained as a rejection,
not automatically excepted or "fixed" by cloning libc. Assembly must enumerate
this new row on its final manifest; it cannot call all rows auto-identical to
the former 103. Dynamic normal-app paths/inherited libc owner remain unproven.

Strings against **actual r3**, not U9: **2 drop / 5 add**; two source-path
replacements plus `%s:%s`, private directory and U11-ZLIB-ROUTE diagnostic.
Existing compat/INET/SoundPool/owner messages stay. ABI exports **15 -> 15**,
removed/drift **0**; calls change only StockCreateConfiguredNamespaces adding
U11ZlibRoot. ABI report has no supplied executable-export consumers; actual
mmkv zlib coverage is checked separately, not disguised as a whole-app consumer
gate. Alias/provider scans have **0 opens / 0 edges**, unchanged-copy strings
**0/0**. This does not prove final private DT_NEEDED/libc owner selection.

## Composition and rollback

`payload-edit.json` lists exact three target hashes and preconditions: replace
host r3; add currently absent private alias/provider. Rollback restores exact
65cc host and removes only the two additions, preserving existing root zlib.
If N11h-r2 also changes host, apply the included original route.patch to that
source and re-run gates; do not overwrite another host delta with this file.
Final native manifest/child rebinding, N1/N2 sidecars and outer exception
registration are the assembly owner's responsibility; no standalone exception
is approved here. `execution_enabled=false`, confirm/refute explicit.

`build.py` tees subprocess stdout/stderr **while running**, pins compiler
**6a5ec844…**, reused objects, full commands and include closure. Large ELF files
stay in persistent `.artifacts/`; source/tests/receipts are admitted.
`test_route.py` compiles the admitted original route fixture without requiring
ignored artifacts. No live/draft package edited and no device command issued.
