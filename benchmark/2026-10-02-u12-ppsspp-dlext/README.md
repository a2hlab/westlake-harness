# PPSSPP dlext: relocation and real backend are separate unfinished walls

## Prior mistake and outcome

Actual015aa already exports android_dlopen_ext. Window5's failure is **app
relocation scope**, not an absent compat export. Supplying another duplicate
wrapper cannot repair it. The same namespace-constructor/saved-scope work as
Gecko must first prove binding to the sole resident compat owner.

No new native ELF is published here. **Standalone first-fatal movement0**;
PPSSPP1 remains a conditional target requiring both real app binding and a
verified extension backend. There is no new build/two-repeat/ABI/N1/N2 claim
for a nonexistent candidate. Rollback is a no-op; package and boards unchanged.

## Exact window5 and consumer evidence

PID26744 has successful resident compat queries at30637/30781/30859, then
libppsspp_jni android_dlopen_ext relocation error30860 and Java ULE30861;
exit255 at32947. Prior actual-private-domain accesses at30855/30857 name
westlake.anl.app.26744.3. Run/ELF SHA and original line numbers are in
`results.json` and numbered hilog excerpt. Consumer full SHA8956cbe5 is pinned.
Its NEEDED list excludes compat. It also imports missing __errno, strtoll_l
and strtoull_l from LIBC: fixing one symptom cannot prove complete relocation.
The VLC candidate can supply the two conversions later; __errno remains LOCAL
in015aa and requires its separately reviewed export change plus scope proof.

## Actual extension calls, not FORCE_LOAD

| Call PC | Nonnull extinfo flags | Required semantics |
|---|---|---|
| 10b3ef8 | 0x200 | USE_NAMESPACE; namespace field at40 |
| 10b405c | 0x210 | USE_NAMESPACE + USE_LIBRARY_FD; fd at28 |

FORCE_LOAD is0x40, not0x10; the older FORCE_LOAD label was incorrect. Exact
call-site disassembly preserves the namespace and FD stores. It establishes
consumer capability requirements, not proof those calls were reached before
the window5 JNI library relocation failure.

Actual015aa's373c wrapper checks the weak backend then forwards all args/LR.
Without it, nonzero extinfo flags go to the explicit refusal at3778 and set
ENOTSUP; plain dlopen is only the zero/null-extinfo branch at3774. Tests compile
the admitted unchanged wrapper and assert both actual0x200/0x210 cases remain
faithfully refused. The first host test failed due to Mach-O weak unresolved
symbol linkage; the original existing U10 test's `-Wl,-U` convention fixes the
fixture only, not the runtime. Failed output remains admitted separately.

## Source lookup and backend boundary

Local AOSP14 libdl.cpp:135–137 is admitted as the source of the public wrapper;
it only forwards to __loader_android_dlopen_ext. It is **not the linker
implementation**. Verified local source inputs contain no matching backend or
Android-namespace-to-OH mapping. Local factory OH ELF fd3c exports dlopen_ext
and dlopen_ns_ext but not __loader_android_dlopen_ext. Existence of those OH
functions does not prove Android opaque namespace identity, flag values or
FD-offset layout equivalent. A raw namespace pointer cast or ignoring extinfo
would falsely claim a real implementation.

The required local→a2hlab→hw248 read-only sequence is recorded: a2hlab hostname
unavailable, hw248 blocked by this sandbox. No successful remote source query
is claimed; a successful rerun also requires remote AOSP14_SOURCE_ROOT.
SSH identity/address are redacted in public evidence, raw output
SHA pinned under persistent `.artifacts`. The factory linker has no traceable
source receipt, so unrelated dynlink-linux source remains a reading reference.

Minimal future work: prove current consumer binding first; archive real namespace
identity/ownership mapping and OH extension ABI from actual fd3c behavior;
implement FD-aware namespace dispatch without a new owner; then exact-baseline
rebuild/static gates and real app binding oracle. This is not included in U12,
and scope/backend remain unfinished. No new frozen runtime inputs are invented.
The next exact fatal and t20 are unknown; a future U10-DLEXT refusal is a
refutation of full repair, not success.

## Static delivery

Explicit generation-scoped WHOIS, actual wrapper disassembly, direct-open scan
(2 sites/0 edges with DEFAULT-NS/UNRESOLVED retained) and self strings diff0/0
are baseline evidence only, not candidate proof. No shared table changes or
second inherit are made. Portable tests compile admitted source without any
ignored `.artifacts` dependency. Machine-readable handoff records the missing
prerequisites rather than authorizing a fake one-file implementation.

Backend enumeration pins102 package ELF `.so` aliases with0 matching backend
definitions, plus the exact factory libc. It is not a complete live system
mapping oracle. First preflight rejected a hardcoded remote source-root user
path in the active collector; it now requires remote AOSP14_SOURCE_ROOT rather
than a user home. The refusal is retained; final preflight34/0.
