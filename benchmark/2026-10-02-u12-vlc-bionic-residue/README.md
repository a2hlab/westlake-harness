# VLC bionic residue: one compat ELF, four real APIs

## Prior mistake and rule

OH `_pthread_cleanup_*` and Android `__pthread_cleanup_*` have different LP64
record order despite both being24 bytes. Direct casts are wrong. Upstream's
TLS-only explicit-pop implementation also misses pthread_exit callbacks.
This candidate translates records and uses **the factory OH cleanup stack**;
it does not replace pthread_exit, add an owner or invent a successful no-op.

Export presence is not app relocation membership. Since the resident compat
scope remains unresolved, this **exports-only standalone U12 change predicts
0 proven first-fatal movements**. With a separately proved scope repair it
conditionally targets **VLC1**, not new lights. Fennec/Firefox/PPSSPP imports
are additional exposure; their current GNU/dlext walls are not counted here.

## Evidence and source order

Window5 VLC PID4317 first requests strtoll_l (hilog19447/19449/19450) then
exits1 at19606; retryPID4353 has strtoll_l and cleanup push failure
(24281/24283/24284), exit1 at24375. Exact run path/hash and consumer ELF
identities are retained. `libc++_shared` also requests strtoull_l; `libvlc`
requests both cleanup APIs. The factory libc exports strtold_l already, so
that similar name is not a new missing API.

Local source found first: AOSP14r1 stdlib_l.cpp:49/57 and pthread_exit.cpp:52–79
are SHA-verified snapshots. Integer conversion wrappers exactly delegate to
strtoll/strtoull and ignore locale like AOSP; end-pointer/base/ERANGE behavior
is retained. Android record layout is additionally pinned from NDK23, labeled
as a layout reference rather than falsely an AOSP14 header.

Actual factory libc fd3c4701 `_pthread_cleanup_push` at12de84 stores routine
at0, argument at8, previous at16; `_pop` at12dea0 restores previous before
executing the routine. pthread_exit12f270–12f288 drains that same stack before
TLS destructors at12f28c. The source provenance of factory libc remains unknown;
these are binary behavior statements, not an OH-version source claim.

## Implementation and limits

`vlc_bionic_residue.c` adds four functions. An Android record keeps the required
previous/routine/argument layout. A separate shadow record has the actual OH
layout and is registered with its real `_pthread_cleanup_push`. Explicit pop
removes the OH record; execute=0 suppresses the callback. OH thread exit invokes
the translation callback in proper mixed OH/Android LIFO order. The wrapper is
freed before invoking the user callback, avoiding leaks if the callback exits.

One heap shadow allocation is needed per Android push. **Allocation failure
aborts**, unlike allocation-free bionic; invalid non-LIFO pop also aborts rather
than fabricating success. Valid paired cleanup use is the supported contract.
Cancellation/C++ exception unwinding is not a new promise (AOSP itself has that
caveat). Host tests model exact OH push/pop/exit drain and use a real host
pthread_exit to trigger the drain; they are not execution on OH or owner proof.

## Identity and build

Deployed compat015aa3a6 is byte-reproduced twice from the accepted frozen link
objects before admitting the new overlay. Candidate full SHA is
**b2be657ca2c171dd786068e77be90d82ec3a50407df37b1ccbafef94a8db88a6**,
identical twice. Existing source30 files and two accepted overlays are verified
and snapshotted; old objects and exact toolchain/link providers are SHA-pinned
at persistent paths. Compiler6a5ec844 is the original OH clang15. New overlay
and resource/sysroot headers are admitted. The build script logs through runtime
tee; raw log/artifacts/object inputs remain persistent under `.artifacts`, not
git. `build-receipt.json` explains relinking rather than pretending a fresh
full engine/source rebuild. The initial header archival failure is preserved.

## Static gates and rollback

- ABI50→54, only four specified additions; removed/drift/calls0.
- Consumer breaks0 across219 actual ARM64 ELFs; this checks removed exports,
  **not all app import resolution**. GNU/scope remains a separate prerequisite.
- deployed_strings_diff0drop/0add, no allowlist used.
- open_site_scan2→2 direct opens, 0→0 namespace edges, no new opens.
  Existing android_dlopen_ext PCs move3758/3774→3a58/3a74; DEFAULT-NS and
  UNRESOLVED findings remain raw. The scanner's clobbered-register rendering
  is conservative, not proof that the old tail dispatch arguments changed.
- Full N1/N2 baselinePASS; candidateREJECT because the new manifest is not
  exception-approved. New source profile has0 findings, N2 unchanged103;
  no copied registry exception or package authorization is fabricated.

Replace only the same compat ELF at root and route aliases, without host/policy
or APK changes. Restore **both aliases to015aa3a6** on regression. cx-t0 must
not replace a combined compat candidate containing other accepted additions
with this older complete ELF: compose the source overlay/map additions and
rebuild once. No current draft or board was edited. Next exact fatal/t20 unknown.

First landing preflight rejected two full consumer dynsym outputs above the
size limit. The admitted files now explicitly contain numbered target-symbol
excerpts; complete raw outputs and SHA remain under persistent `.artifacts`.
`evidence/preflight-first.txt` retains the original refusal. Final preflight93/0.
