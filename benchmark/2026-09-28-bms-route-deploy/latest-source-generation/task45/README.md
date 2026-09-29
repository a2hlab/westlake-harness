# B6 / task 45: recover the R155 primitive cache guard

The task-44 conclusion that four R155 exports were merely unused diagnostics
was too strong. Absence of external UND consumers says nothing about an inline
method's behavior inside ART. R155 `DexCache::GetResolvedType` contains a real
semantic guard, while the recovered AOSP14 r1 header returned the cached class
unchanged. No Java declaration mismatch was found: the failing overrides and
their parents have matching `Z` / `V` DEX signatures.

## Binary evidence and source reconstruction

[R155 disassembly](r155-getresolvedtype.disassembly.txt), from libart
`59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f`,
establishes the following control flow:

- `0x2dcd2c` loads the resolved-types array at `DexCache + 0x58`; the fallback
  at `0x2dcd90` reads the hashed cache at `+0x50`.
- `0x2dcd40: ldr w9, [x0, #0x68]`, followed by `tst w9, #0xffff` and
  `b.ne 0x2dce90`, keeps an already primitive cached class.
- `0x2dcdbc: ldrb w8, [x20]` and `0x2dcdc4: ldrb w8, [x20, #1]`
  accept the guard only for a nonempty, one-character descriptor.
- `ldaxrb` / `stlxrb` at `0x2dcdd8` / `0x2dcddc` implement the once-only flag.
  The literal is `[PRIMCLASS-GUARD] dropped poisoned DexCache slot for primitive descriptor '`.
- Both the already-logged branch and the logging branch reach `mov x0, xzr`
  (`0x2dce8c` / `0x2dce80`). This returns null, not the incompatible cached class.

The [source patch](../../../../bms/src/adapter/aosp_patches/art/runtime/mirror/dex_cache_primclass_guard.patch)
reconstructs that behavior in the recovered r1 header. It uses
`GetTypeDescriptor(GetTypeId(type_idx))`, the AOSP14 API, and an atomic
`logged_primclass_guard` with an error log. It does not physically clear the
cache slot: returning null lets `ClassLinker::ResolveType` enter `DoResolveType`.
The original R155 source is unavailable; this is a semantic reconstruction,
not a claim to have reproduced its source bytes. The [new disassembly](guard-getresolvedtype.disassembly.txt)
and dynamic symbols confirm that the guard and once-only variable were emitted.

## Java and image checks

[Class origins](class-origins.json) and [DEX excerpts](java-evidence/) identify
UserBinder, UserManagerProjectionProxy and HiLogOutputStream in non-BCP
`oh-adapter-runtime.jar`; Binder comes from `framework.jar` classes3.dex,
and OutputStream from `core-oj.jar`. The [three R155/B5 adapter class bodies](r155-b5-class-comparison.json)
are identical. [BCP strings](classpath-strings.json) show the same nine entries
in the same order. The older provider also has a five-entry DEX2OATBCP string;
this static difference does not demonstrate the cause of the observed failure.

The [R155 identity receipt](r155-identities.txt) lists runtime JAR `9161…`, but
does not list framework/boot identities. A separate historical deployment
receipt matches 38 of 40 Java/image entries in the live B5 inventory: the known
runtime JAR differs, and the root boot.art is absent from that receipt.
An evidence-recording Git commit is not proof of the compiler's source commit.
The real-work Java build probe reached the missing AOSP14 turbine header JARs;
per subsequent user instruction, Java rebuilding was paused.

[Layout comparison](layout-comparison.json) finds no mismatch in examined
ArtMethod/Class sizes or the critical Class/DexCache offsets. It does not prove
full ABI equivalence; R155 has no useful ART type DWARF, and its DexCache total
size was not established. [Image header checks](image-header-check.json) find
matching ART image version 108, OAT version 230, pointer size 8, and all nine
image-to-OAT checksums. These checksums do not bind images to a libart SHA or
encode complete C++ layout fingerprints.

## Host gates and deployment policy

All 246 ART translation units were rebuilt because this is an inline-header
change. [Provider comparison](provider-change-receipt.json) proves that only
libart changed among 27 libraries; the other 26 retain their task-44 SHA.
The source and build recipes are under [recipes](recipes/). The initial compile
used the wrong A14 descriptor overload, failed, and was corrected before a
fresh rebuild of all ART objects.

The sealed manifest, runtime provider, child and appspawn-x were regenerated.
The provider/child/host builds each pass two-build byte comparison and strict
linking. The finalized host is checked for both the new generation string and
the actual new child SHA. [Closure](closure.json), [closure negatives](closure-negatives.json),
and [sigchain symbols with four missing-export controls](sigchain-symbols.json)
are host evidence only. The consumer inventory remains useful for external
link requirements, but does not establish inline semantic equivalence.

Only locked board 5ea is used. Admission and child-loaded identities precede
HelloWorld, Wikipedia/null-check observation and ZigZag. Every failing candidate
is rolled back as a whole generation to the signed B5 baseline. No image/JAR
change is included in the guard trial. Per the latest instruction, the deferred
no-image experiment is attempted only if this guard trial still fails.

## Guard-only trial

Generation `d2c16c1d…`, host `07fe5f96…`, child `d0e6329f…`, ART `2d1074b8…`
and sigchain `6d5d5538…` passed live admission. Child 25244's mapped files and
hashes match the candidate. The raw log includes `WLCGATE:HSPM:PASS_IDENTITY`,
all A06/A02 causes zero, and `CHILD_A02` for HelloWorld.

Nevertheless, [HelloWorld's final screenshot](guard-trial/helloworld/final.jpeg)
is the desktop. The [log](guard-trial/helloworld/hilog-excerpt.txt) still reports
the same boolean/void-versus-Object LinkageErrors. No PRIMCLASS-GUARD log was
observed. This shows the restored guard is insufficient in this build; it does
not prove that guard absent from R155 was irrelevant. Wikipedia and candidate
ZigZag were not run after the first control failed. The full 36-mount generation
was rolled back, restoring B5 parent 27088. See [trial receipts](guard-trial/).

The previously authorized no-image experiment follows this failed trial:
the explicit image path is absent and `-Xnoimage-dex2oat` prevents image
compilation. It retains the guard ART and all other provider bytes. Host PASS
alone does not establish rendering or Java NPE delivery.

## Imageless trial and final state

Generation `473712e5…`, host `dd2fc4aa…`, child `693d7dea…` passed admission;
child 1816 mapped the same guard ART and musl sigchain. The startup marker
confirms the absent image and disabled image-dex2oat option. The runtime then
entered `ClassLinker::InitWithoutImage` and aborted at `CheckSystemClass`:

> InitWithoutImage: Class mismatch for Ljava/lang/String;. This is most likely the result of a broken build. Make sure that libcore and art projects match.

The [complete abort message](noimage-trial/string-mismatch-abort.txt) prints two
different String class objects and a 70-entry loaded vtable; the [fault stack](noimage-trial/candidate-helloworld/fault-stack.txt)
identifies SIGABRT in CheckSystemClass during Runtime::Init. This proves the
imageless path is available and was entered, not that this ART can initialize
against the supplied DEX cohort. It does not establish which historical patch
or libcore build fixes that disagreement. A new host dex2oat alone is therefore
not yet a demonstrated remedy: image creation also needs consistent ART and
boot classes. No assertion/check was disabled and no Java class was replaced.

The [timing excerpts](noimage-cold-timing.txt) show 1.172 s from desktop onClick
to abort (0.940 s from spawn). In the [B5 control](baseline-cold-timing.txt),
onClick to the first-frame log was 1.985 s, with own UI confirmed in screenshots.
Both launches cold-stopped the app first. These are single diagnostic samples,
not a performance benchmark; the failed candidate has no successful UI latency.

Both trials rolled back every one of their 36 bind mounts and verified baseline
file hashes. Final B5 parent is 3839, HelloWorld PID 4798 and ZigZag PID 5799;
both control runs had no new faults. The final [HelloWorld](noimage-trial/rollback-helloworld/final.jpeg)
and [ZigZag](noimage-trial/rollback-zigzag/final.jpeg) screenshots were inspected
and show their own UI. The 5ea lock is released. Candidate Wikipedia/NPE and
ZigZag remain unverified because the mandatory HelloWorld gate failed first.
SIGABRT in the imageless trial is not evidence of SIGSEGV-to-NPE conversion.

R2: verified source reconstruction, build/host controls, live identities,
specific failures and rollback; partially localized ART/libcore/image cohort
compatibility; unverified B6 Wikipedia rendering and repaired implicit NPEs.
The task remains **blocked**. The lifecycle preserves that result rather than
treating the B5 rollback screenshots as candidate regression acceptance.

Validation: [lifecycle](lifecycle.json) reports four pass and four fail: caller,
absent-artifact rejection, symbol coverage and identity pass; Wikipedia, candidate
HelloWorld/ZigZag regression, advancement beyond getTheme, and NPE retest fail.
[Known-answer tests](known-answer-tests.txt): 69 run, two skipped, no failures.
No spec was changed to alter these verdicts.
