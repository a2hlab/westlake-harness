# Task 44: ART bridge restored; admitted cohort fails Java class linking

Task 41 incorrectly treated the missing ART C bridge as an unavailable provider
interface. The real-work recipe explicitly compiles `art_abort_message_bridge.cpp`
into ART. Restoring that source fixes strict linking. The corrected cohort now
passes live identity admission, but **HelloWorld fails before UI with a Java
primitive-return-type LinkageError**. B6 is blocked, with zero new lit apps.
Both live trials were completely rolled back and B5 controls were re-observed.

## Source correction and bounded export decision

The source comes unchanged from real-work commit
`be16148da9ae7bb89c62e81e144ed0bceb5c4669`,
`src/adapter/framework/appspawn-x/src/art_abort_message_bridge.cpp`.
Its build recipe `build/inner/cross_compile_arm64.sh` includes this translation
unit in the libart source list. AOSP14 r1 `runtime/runtime_common.cc:373` already
implements `art::GetFaultMessageForAbortLogging`; no stub was needed. See
[bridge source](abort-bridge-source.cpp.txt) and
[ART implementation excerpt](runtime-common-source.txt).

The original 245 ART objects were retained, the bridge object was compiled anew,
and ART was strictly relinked. Recompiling the bridge and relinking a second time
produced identical ART bytes: `073a54cba5abab4b97ab73b763012a9bf1ff6740dd19a9993e930d4bd8a8f7b2`.
**Only ART changed among the original 26 provider outputs**; the additional
OpenJDK JVM output also stayed unchanged. The changed build source list and bridge
are included in this commit. See [provider receipt](provider-change-receipt.json).

R155's other four absent exports are three methods and one guard, not four
missing runtime implementations:

| Export | R155 kind | Source and disposition |
| --- | --- | --- |
| `ClassLinker::ResolveType(TypeIndex, ArtMethod*)` | weak function, 116 bytes | Actual r1 inline method remains in `class_linker-inl.h:140`; no forced export |
| `DexCache::GetResolvedType(TypeIndex)` | weak function, 476 bytes | Actual r1 inline method remains in `mirror/dex_cache-inl.h:163`; no forced export |
| `ClassLinker::DumpBootObjectFields(const char*)` | global function, 2404 bytes | R155 diagnostic source unavailable; not recreated |
| `GetResolvedType::logged_primclass_guard` | weak object, 1 byte | R155 diagnostic source unavailable; not recreated |

Under the user's explicit ruling, absent diagnostic exports without consumers
are documented rather than replaced with stubs. The normal inline methods are
not classified as diagnostics. [Inline source excerpts](inline-sources.txt) and
[consumer audit](consumer-audit.json) preserve the distinction.

The board inventory covered **2,760 files** under `/system/android/lib64` and
`/system/lib64`. A positive-controlled `strings` search for the four names or
`libart.so` selected **12 board ELFs**, including ART itself, runtime provider,
child, OpenJDK JVM, nativehelper, unwindstack and DFX base. Those plus **34
candidate ELFs** have **zero UND references** to the four exports. This is a
static reference/name audit, not proof against every conceivable dynamically
constructed lookup. An initial `grep -a -l` zero-hit result was discarded because
it failed the known-ART positive control; it was not used as evidence.

## Host construction and checks

ART/providers and native roots retain the previous AOSP14/OH6.1 builds; only
ART's additional bridge and real-work startup components are new. Native roots
still derive from latest00 `cd5b3293596cc9d9f324743d6d904c5135954076`; startup sources
come from real-work be16148da. This is an explicit mixed source provenance, not a
claim that the latest00 unfinished Android entry is usable.

The real-work build flow regenerates source/route input ledgers, sealed manifest,
runtime provider, child plugin, and host pin. Provider bytes are checked before
and after. Provider/child/host strict links reproduce over two runs, and both
child target ABI and stock host ABI checks pass. The wrapper runs from its root
so prefix-mapped DWARF resolves during ABI verification. The SDK's dlns ABI header
is force-included in C compilation only, not assembly. Identity checks remain
active. [Recipes](recipes/) preserve the extracted build flow and migration diffs.

The composite [generation receipt](generation-verification.json) covers these
strict links and ABI checks. It does **not** claim that the latest00 full-generation
verifier was rerun against real-work. The previously authorized tuple-receipt
waiver remains historical provenance, not a new waiver of an identity check.

- [NEEDED closure](closure.json): 34 required, 338 reachable libraries,
  3,024 edges; zero unresolved edges/errors.
- [Closure negatives](closure-negatives.json): four original mutations and the
  false absent-SONAME declaration all rejected.
- [Sigchain symbol coverage](sigchain-symbols.json): all four new ART imports
  covered; each single-export removal rejected.
- [Host ABI](host-abi.json) and [child ABI](child-target-verification.json): PASS.

## Two live trials on 5ea

Only `5ea34a4500000000000000001123012c` was written, under cx-t0's board lock.
Boot ID remained `56e521b3-858f-4fbf-8e35-daec29525c93`.

| Trial | Generation | Result | Rollback |
| --- | --- | --- | --- |
| 1 | `f40ecb2fe5e0bdc3a561b0446984c0bad1bbbaad2b6c39654b5f2ab03f3541e8` | HelloWorld child 27232 exit 210; exact adapter bridge admission failed | All 36 mounts restored; HelloWorld 30514 and ZigZag 31511 visually normal |
| 2 | `4af23ed33ae898666dd7d76f4c9bd3fee3ac74320d58d8edd67a9574e9fabb11` | Identity and `CHILD_A02` pass; HelloWorld child 5337 exit 1 with LinkageError | All 36 mounts restored; HelloWorld 12126 and ZigZag 13149 visually normal |

**Trial 1 was our migration error:** overlaying real-work restored its historical
`r45_adapter_identity.env`, while the deployed native roots were the new ones.
The old bridge/runtime pins dc662222/72c9e172 did not match actual 1ca2848d/3da73f63.
The admission guard correctly refused them after VM initialization. We rolled
back completely, verified both B5 screenshots, then regenerated with actual
SHA and Build-ID pins. The wrapper now checks those pins before generation.
[Correction receipt](dynamic-root-pin-correction.json) and [trial 1](trial1/)
retain this failed run; no validation was disabled.

**Trial 2** captures raw `A06_ADMISSION_CAUSE:0`, HSPM identity success,
`A06_PREPARE_CAUSE:0`, A02 precondition/handoff/receipt success and `CHILD_A02`.
No `LOAD_ERROR` or `FAIL_SEALED_PROVIDER` occurs. The child's actual `/proc` proof
contains the following identities, with new ART and sigchain mapped at the new
route directory:

| Artifact | SHA-256 |
| --- | --- |
| host | `8125006b52601f293458e6ab4281ea044430ae634b3b45cffb13db8c22750073` |
| child | `c2952931a27b056957dab18272ac78b80f5d2d7f99e79e48ab2bd4e079106598` |
| ART | `073a54cba5abab4b97ab73b763012a9bf1ff6740dd19a9993e930d4bd8a8f7b2` |
| sigchain | `6d5d5538ff45c057208186f5cb74b9b5c2402d693aa2756a99327fd4b9f8c400` |

See [actual child hashes](trial2/helloworld/child-proof-5337.late-sha256),
[maps](trial2/helloworld/child-proof-5337.late-maps), and
[line-numbered hilog excerpt](trial2/helloworld/hilog-excerpt.txt).

The terminal error is `AppSpawnXInit.initChild -> UserManagerProjectionProxy.install`:
`UserBinder.onTransact` resolves a boolean return type while superclass Binder
resolves Object. An earlier `HiLogOutputStream.write` error similarly compares
void with superclass OutputStream's Object. Child exits 1. This localizes the
new wall to Java class linking during child initialization; the deeper primitive
resolution/boot-cohort cause is **not yet proven**. Neither omitted diagnostics
nor boot-image incompatibility is established as the cause. The boot-framework
OAT remained version 230 and unchanged. VM creation alone is not semantic boot
compatibility evidence.

The [candidate final screenshot](trial2/helloworld/final.jpeg) is the OH desktop.
Wikipedia, repaired implicit-null behavior, and candidate ZigZag were **not run**
after the HelloWorld control failed. Historical `null_check_mode=sigsegv` is
explicitly labeled as old evidence in [results](../results.json).

## Final restoration and verification

[Deployment receipt](deployment.json) records the complete second rollback and
restored parent 7245. All 36 original mount targets were hash-checked by the
rollback flow. [Final B5 identity](trial2/rollback-identity.txt) retains host
1f6cf53b, child 0976dee8, B5 JAR 250958dc, framework 3e106350 and boot-framework
0ff275fa. The board lock was released after regression observations.

Final screenshots, viewed by cx-t0 and submitted for outer review:

- [B5 HelloWorld](trial2/rollback-helloworld/final.jpeg): Hello World UI, lifecycle
  CREATED/RESUMED and action buttons.
- [B5 ZigZag](trial2/rollback-zigzag/final.jpeg): ZIGZAG title and TAP TO PLAY.
- [Rollback records](trial2/rollback-results.json): both app processes present,
  no newly created fault files.

Known-answer tests: **69 run, 2 skipped, 0 failures**. Fresh B6 lifecycle and
explain are stored one directory up. The absent-artifact negative verifier had
incorrectly assumed every real candidate failed admission; it now independently
rejects absent/mismatched synthetic fixtures even when the real candidate passes.
No spec was changed, and failed functional acceptance remains failed.

R2: **verified** source correction, provider retention, strict reproducibility,
ABI/closure/negative checks, live identity proof, observed Java failure and full
rollback; **partially** new VM/Java startup reached but semantic compatibility
fails; **unverified** Wikipedia UI, repaired NPE conversion, candidate ZigZag and
the deeper cause of primitive return-type mismatch. This is not a policy block.

Raw VM runs: `~/a2hlab/board/b6-44-helloworld-5ea-r{1,2}` and
`~/a2hlab/board/b6-44-rollback-5ea-r{1,2}`. Full binaries/build logs remain under
`bms/src/.work/b6-task44` and `bms/src/.work/b6-real-work`; they are not committed.
Recipes are archival reproductions for those staging layouts, not standalone
fetch-and-build scripts: restore their named frozen inputs first, place retained
startup scripts at the b6-real-work staging root, set `B6_REPO_ROOT` for the ART
wrapper, and invoke through dockbuild. The consumer scanner runs in the VM with
`B6_HDC` set to the shared hdc wrapper. It is read-only.

Fresh lifecycle: **4 pass / 4 fail**, 0 skip, 0 pending review.

- `b6_wikipedia_lit`: **fail**.
- `b6_caller_identified`: **pass**.
- `b6_no_regression_helloworld_zigzag`: **fail**.
- `b6_next_wall_recorded`: **fail**.
- `b6_fix_absent_detected`: **pass**.
- `b6_null_check_mode_recorded`: **fail**.
- `b6_generation_passes_identity_gate`: **pass**.
- `b6_sigchain_exports_cover_libart_imports`: **pass**.

Published text copies normalize local path prefixes and trailing whitespace;
raw VM logs and maps remain at the run paths above. The bridge source retains
its original AOSP16 comment verbatim; this experiment linked its implementation
against AOSP14 r1, not AOSP16 ART.
