# Latest-source route-A generation (task 39, blocked before deployment)

The task-35 diagnosis incorrectly treated the missing `libartbased.so` log as a
required debug dependency. The inspected release `libart.so` needs
`libartbase.so`, not `libartbased.so`. The release library's `CheckLoadedBuild`
constructor probes **both** names with `RTLD_NOW | RTLD_NOLOAD` (6). It exits
when neither name is visible, and would also reject a visible debug variant.
Adding a debug library is not the repair.

Evidence: `libart.so.elf.txt`, `libartbase.so.elf.txt`, and
`check-loaded-build.disassembly.txt`. `check-loaded-build-source.txt` contains
supporting AOSP16 source, explicitly not the byte-exact source of the inspected
v12 binary. The v12 `libartbase.so` is byte-identical to R155
(`75c0f18372207ea54cd735b86eae7f0e0797e026136c0d07050520b8199f85b1`).
The precise namespace failure remains to be verified; static NEEDED closure
cannot prove dynamic `dlopen` visibility.

## Route and source inputs

The bounded R155 search did not recover a source receipt that rebuilds the
active child `0976dee8` and host `1f6cf53b` byte-for-byte. `real-work`'s R155
activation imports `historical-success-cohort`; its r150 source has the V2
loader. Consequently this task continues with the authorized whole-generation
route. The latest adapter source is fixed at `00.Workspace`
`cd5b3293596cc9d9f324743d6d904c5135954076`.

The frozen v12 input has prebuilt AOSP14 providers, not ART source. The supplied
hw248 `l03a15` provider source is the APK installer/parser. Full ART source found
so far is AOSP16, with oat 259 or 265; the signed board boot-framework image is
the previously verified oat 230 image. Source selection and matching dex2oat
input remain pending. No AOSP16/14/230 compatibility is claimed.

## Host evidence collected so far

- Latest-source TGR compiled in local dockbuild:
  `1e6b2f2d55d99608477e7d7f3dbbcf78fe7d789f4d1c3ffd82ce45016729df80`.
- `bridge-probe8.txt`: first bridge compilation unit succeeds. The compiler is
  the recovered clang-15 and musl SDK from task 35. This is not a linked library.
- `bridge-all1.txt`, `bridge-all2.txt`: 39/54 and 43/54 compilation units; errors
  are preserved. The missing Ninja template (from the recipe's frozen
  `oh61-v7-b2133b5b` source) accounts for absent include paths and M133 defines.
  `bridge-all3.txt` through `bridge-all5.txt` use a fresh object directory
  after recovery and finish at **54/54 compiled**. `bridge-objects.json` records
  object identities. No bridge link or native-runtime build has passed.
- `audit_closure.py`: requires explicit generation members and walks every
  NEEDED edge, including a separately pinned platform pool. It checks SHA,
  architecture and SONAME. `closure-audit.json` rejects the current incomplete
  set: **31 missing out of 32 required members**. The required list is a minimum
  inventory of the former generation's roles, not a fixed limit on new members.
- `closure-negatives.json`: positive explicit-pool control passes; omitted
  member, undeclared dependency, wrong platform SHA and wrong SONAME all fail.
  These are host gate checks, not live generation validation.

`run_bridge_probe.sh` is a compile-only harness. Its partial object files must
not be promoted to a product generation. A production build still needs the
same-source ART/providers, native roots, pinned OH platform pool, strict link,
manifest regeneration, identity admission and boot-image compatibility proof.

## Board boundary

`board-baseline.txt` is read-only evidence for 5ea. No task-39 board write,
installation, process launch, mount, or candidate activation has occurred.
No new screenshots, fixed NPE result, Wikipedia UI, or regression pass is
claimed. The signed B5 baseline remains the rollback target.

## Contract status

The caller and absence/mismatch negative control remain testable. The six
new-generation runtime/coverage scenarios cannot pass without a complete
candidate. See `results.json` and the fresh lifecycle result. Previous baseline
UI or symbol checks against the old ART are not promoted as new-generation proof.

Validation: 69 repository known-answer tests, 0 failures and 2 skips. B6
lifecycle: 2 pass (caller, absent-artifact negative), 6 fail (Wikipedia,
regression, advancement, NPE retest, identity, new-ART symbol coverage),
0 skips and 0 pending review. Final read-only boot ID and six SHA values match
the initial B5 baseline exactly (`board-final.txt`).
