# G24: compare exact native-cluster reuse with one-symbol publication

The comparison supports reviewing the mature native-cluster route first. It does
**not** authorize a package-list edit. A one-symbol atfork leaf would remove only
one of three consecutive known relocation gaps in the exact game core. Reusing
the actual d205 ABI can remove all three, conditional on successful ANL selection,
host selection and `RTLD_NOW | RTLD_GLOBAL` publication. No route was implemented,
built, deployed or run in this slice. Game success remains false.

| Question | Existing native-cluster + d205 | Proposed single-symbol host seam |
|---|---|---|
| Expected observed first-fatal movers | genshin: 1, conditional | genshin: 1, conditional |
| Exact libyuanshen known gap coverage | 3/3: atfork + FD_SET + FD_ISSET | 1/3: atfork; next FD_SET, then FD_ISSET |
| Direct existing ABI coverage across 32 ELFs | 20 import/library pairs in 8 ELFs | 4 pairs in 4 ELFs |
| Generous disk-closure diagnostic | 50 -> 28 missing pairs | 50 -> 46 missing pairs |
| Newly exposed namespace admission gap | 1 direct edge: cri_vip_unity -> mediandk | No new DT_NEEDED edge if leaf needs only libc; hypothetical |
| Publication surface | Existing 26 exported names incl. stdio/property | Proposed 1 LIBC export |
| Runtime pieces requiring a future build | Exact ANL and host selectors, existing ABI reused | Host plus new leaf/map/recipe; no candidate ELF exists |
| Other package selection changes | Expected 0; keep existing 13 native / 6 Flutter selections | Expected 0 with exact predicate |

The 50/28/46 numbers are **disk graph diagnostics**, not a complete namespace
simulation or a claim that all remaining imports resolve. Twenty removals are
attributable to d205; two additional removals depend on transitive providers.
Thus direct known-gap coverage is 40%, conditional disk-model coverage 44%, versus
8% for the leaf. Only the core's three-gap cluster reaches 100% with reuse. There
is no evidence for “80% of game blockers solved.” Thirty-two ELF files were read;
`libmsaoaidsec.so` has six undecodable DT_NEEDED names and is unknown, not passed.

## Exact identity and visibility conditions

`results.json` binds G24 loader 878c7019 versus baseline b8be63d2, ANL eebd62f2,
host 2a87118e, and the **actual** public/private ABI d2053066. U14/U15 replacement
ABI versions are not substituted. `provider-matrix.json` includes full SHA values.
The exact libyuanshen SHA is 3dd8a20d; its relocation order and LIBC imports are
in `32-elf-comparison.json`. Its dynsym3 atfork import is the observed first gap;
G24 hilog line3276 at 20:35:55.798 confirms it, before exit1 at 20:35:56.182.
The earlier __errno error is retained as caught/continuing, not miscalled the
first fatal. `observed.txt` preserves original lines/timestamps.

Current com.miHoYo.Yuanshen is absent from both exact component selectors.
`first-slice.json` pins ANL lines60–76/447–475 and host source; native selection
must match in both. `flutter_domain.inc` lines22–48 supplies private-first search;
host n4-host.c lines263–291 supplies direct owner inheritance and lines345–358
publishes **the private path** of d205 GLOBAL. Caller RTLD_GLOBAL remains forbidden.
The public ABI has identical bytes but merely existing on disk or being shared
by SONAME does not make it visible. Under that successful native path, all three
core imports match d205's exact `@@LIBC` exports. The atfork implementation forwards
to real pthread_atfork; FD functions check bounds and use FD macros. This is not a
no-op replacement. Both atfork designs omit bionic DSO-unregister semantics.

The namespace branch also changes provider bytes:

| Core dependency | Current disk-resolved reference | Native private reference |
|---|---|---|
| libandroid.so | adc125f4 | ee2fb82c |
| libGLESv2.so | befb6ec7 (no GLESv3 DT_NEEDED) | 4b653941 (DT_NEEDED GLESv3) |
| libz.so | 3c025525 platform reference, actual game winner unknown | 50b9ab6a -> private shared_libz ab0820c6 |

Native directly inherits the runtime owner; private libandroid's runtime provider
is 94718e0d. Native also inherits system OpenSLES, whereas the old disk replay
finds the Android shim. **Do not use its audio missing rows as final native results.**
This difference is listed, not silently repaired in the counts. Source selection
is evidence of intended lookup, not actual game mapping or semantic equivalence.

## Known missing admission and remaining work

The native branch ignores the normal G18 shared list and uses its own. It omits
`libmediandk.so`; the current normal bridge permits it. Exact `libcri_vip_unity.so`
needs it directly and neither the app nor private directory supplies it. A plain
membership addition therefore has a newly uncovered loader edge. Review an
exact-game allowance using the existing mechanism before treating reuse as ready;
no allowance or implementation was made here.

Remaining static gaps include __assert2, strtoll_l/strtoull_l, LIBC_Q
android_get_device_api_level, thermal APIs, media-format APIs, audio IIDs and
__libc_init in the crash dumper. Their actual launch order/necessity is unknown.
The machine table retains each consumer, symbol, version, relocation offset,
section and every unresolved dependency. Weak imports are not fatal; NDK-name
regexes are **not** accepted as providers. The version-aware model uses exact
provider versions where VERDEF exists, historical OH unversioned-provider
semantics otherwise. Deep system objects are local reference files; no fresh
board binding is claimed. Two system image libraries are unlocated. GLOBAL
symbols can affect other namespaces in the same process: an exact package
predicate alone does not prove confinement. Other package selectors are expected
unchanged but require later negative controls for either common host build.

## Reuse, limits and delivery

This reuses U15 `replay_normal.py`'s relocation/closure method, correcting private
search priority, removing NDK regex exemptions and adding version comparison.
U15 fd-meet compat+exports moved0 is accepted; that route was not retried. U14,
U15 and Unity/native-cluster experience are references, not game-frame evidence.
The cx-seal single-symbol proposal is SHA-pinned in `first-slice.json`. Existing
d205 source/receipt history and host/ANL reproducibility are being audited by
cx-reentry-peer; no further historical investigation was done here. The leaf
has no built artifact or replay receipt. Neither route has a new reproducible
build claim in this report.

`scan.py` retains the original offline recipe and `.private/` retains all LLVM
argv/stdout/stderr/rc (large relocation stdout compressed losslessly). The first
Python hashlib.file_digest incompatibility failure is retained; the compatible
streaming hash correction then completed. `evidence-index.json` hashes these
originals and the exact G24 log/apply records; paths are sanitized aliases.
`libyuanshen-closure.json` is the full reference DT_NEEDED graph, explicitly not
namespace reachability. `command-index.json` indexes individual tool receipts.
No giant ELF dumps are in the landing list.

Run `python3 check.py --raw` from this directory to rehash originals and check
coverage/identity/count invariants. G16 contract/selector remain unchanged;
Rust execution is NOT_EXECUTED because this task forbids compilation. The small
checker validates this new evidence only, not runtime success. The outer loop
lands `landing-paths.txt`; no shared Git or board write is retried.
