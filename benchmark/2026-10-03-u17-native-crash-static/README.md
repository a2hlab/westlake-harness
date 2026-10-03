# U17 ③④ native-crash static analysis: fennec (libmozglue) + im-vector (librealm-jni) — shared bionic/musl sysconf mismatch

#90, offline, nothing deployed. cc-t3 (reassigned from cc-wiki). Both crashes independently disassembled on the SAME
binaries that crashed on-board (build-ids verified equal). Origin draft: cc-wiki's early U17 ③④ evidence; this is the
verified, landed version with the first-fatal key accounting.

## One-line root causes
- **④ fennec (DEFINITIVE)**: mozjemalloc init reads the page size via `sysconf(0x27)`; under our musl `0x27` is NOT
  `_SC_PAGESIZE` but `_SC_BC_STRING_MAX` → returns 1000 (not a power of two) → `MOZ_RELEASE_ASSERT(1<<gPageSize2Pow ==
  gPageSize)` fails → a deliberate `MOZ_CRASH` writes `*(NULL)` → SIGSEGV@0. (The `putenv`/`strdup` on the call stack is
  just the first malloc that triggers lazy init — NOT a bad pointer.)
- **③ im-vector / Realm (STRONG; last step inferred)**: Realm SlabAlloc sizes/attaches its `.realm` mmap sections using
  the page size from `sysconf(0x27)`/`sysconf(0x28)`; under musl those are wrong selectors → the translation table
  `m_translations` is never populated (NULL) → `nativeGetSharedRealm`'s first ref→address translation derefs NULL →
  SIGSEGV@0. The guarding `pthread_mutex_lock` SUCCEEDS and there are no robust/pshared mutexattr imports, so it is NOT a
  mutex/futex ABI crash.

## Shared root cause (both): bionic↔musl `sysconf` `_SC_*` numbering mismatch
Android NDK apps are compiled against bionic `_SC_*` values; our runtime's musl numbers them differently. The page-size
query is the fatal case:
| selector | bionic value | musl value | musl `sysconf(bionic#)` returns |
|---|---|---|---|
| `_SC_PAGESIZE` | 39 (0x27) | 30 | `_SC_BC_STRING_MAX` → **1000** (not power of two) |
| `_SC_PAGE_SIZE` | 40 (0x28) | 30 | a non-page-size selector (COLL_WEIGHTS / BC_*) |
| `_SC_NPROCESSORS_ONLN` | 97 (0x61) | 84 | wrong |
(musl numbering from OH musl `unistd.h`; the `[39]=_POSIX2_BC_STRING_MAX=1000` return from OH musl `src/conf/sysconf.c`,
per cc-wiki's hw248-verified note in evidence/sysconf-mismatch.txt.)

## Verified disassembly (this round, on the crashing binaries — build-ids match)
librealm-jni.so build-id `ea0a5d9080555279643882fd771d0f9af6bbfd6f`; libmozglue.so `6a348a8e315c3fc31d1de3509ef9f1cb7a905dea`
(both == the on-board faultlog libs and the local app-inputs copies). Full snippets in evidence/verified-disasm.txt.

**④ fennec libmozglue** (verified):
- `GeckoLoader_putenv` @0x90584: `ldr x8,[x8,#0x548]`=GetStringUTFChars → `blr x8` → `cbz x0,…`(null-checked) →
  `strdup@plt` @0x905b0 (+44) → `putenv@plt`. The strdup arg is a VALID non-null string (corrects the "bad pointer" theory).
- `#00` @0x77d44: `mov x8, xzr` (0x77d38) then `str x9,[x8]` with `w9=#0x33` (51) → deliberate `*(NULL)=51`.
- reason string @.rodata 0x454b2: `"MOZ_RELEASE_ASSERT(1ULL << gPageSize2Pow == gPageSize) (Page size is not a power of two)"`.
- `sysconf(#0x27=39)` at 5 sites (0x75834, 0x7fd30, 0x806f8, 0x84358, 0x8a778) — mozjemalloc/RELRO page math.

**③ im-vector librealm-jni** (verified):
- `#00` @0x7738e0: `ldr x27,[x0,#0x30]` (m_translations @ obj+0x30) … `lsr x23,x8,x25` (idx) … `ldr w8,[x27,x23,lsl #2]`
  = FAULT (x27 NULL).
- `#01` @0x65d238: `bl pthread_mutex_lock@plt` ; `cbnz w0, 0x65d268` (branch away on FAIL) — NOT taken (lock succeeded) ;
  falls through to `bl 0x7738b4` @0x65d258 (the translate call).
- `sysconf(#0x27=39)` @0x777e58, `sysconf(#0x28=40)` @0x38c5a0.
- dyn-syms: NO `pthread_mutexattr_setrobust` / `setpshared` imports → not a robust-mutex ABI crash.

## Fix: one libc-compat shim (high leverage, SAME class as the existing bionic compat)
Add a `sysconf()` wrapper in the already-NEEDED `libbionic_compat.so` that translates bionic `_SC_*` numbers to musl's
before delegating to musl `sysconf`: 39→30, 40→30, 96→83, 97→84, … (map the whole diverging range; both tables are fixed
and known). Scope to app-native callers (the runtime's own code already uses musl numbering). Not a stub, not "don't fix":
it is a translation shim. Confirm by fix-and-rerun (④ is statically definitive; ③'s garbage-page-size→NULL-table step is
the only inferred link).

## Estimated keys whose first-fatal this moves (honest, per the first-fatal cluster table 2026-10-03-u13-first-fatal-clusters)
The `sysconf` crash is the **next** wall, not the current first-fatal, for all four candidates — each is currently blocked
by an EARLIER native-link wall:
| key | lib | current first-fatal (cluster) | owner of that wall | after it: sysconf wall? |
|---|---|---|---|---|
| fd-fennec_fdroid | libmozglue | `__gnu_strerror_r` (C2a) | native_abi 7605812c (U14, owned) | YES → sysconf MOZ_CRASH |
| firefox | libmozglue | C2a native_abi | native_abi 7605812c (U14, owned) | YES (same mozglue family) |
| fd-im-vector-app | librealm-jni | `_ctype_` (C2b, bind_failed) | UNOWNED | YES → nativeGetSharedRealm NULL |
| mcdonalds | librealmc | `_ctype_` (C2b) | UNOWNED | YES (same Realm family) |

So the sysconf fix:
- **moves 2 keys** (fennec, firefox) once U14's native_abi 7605812c is on the board — their first-fatal becomes the
  mozjemalloc MOZ_CRASH, which this fix clears;
- **+2 more** (im-vector, mcdonalds) ONLY after the Realm `_ctype_` native-domain wall is also fixed (currently unowned).
Standalone, with today's unified state, its immediate first-fatal-move count is ~0 (the link walls dominate) — so it must
ship **paired** with the native-link fixes (native_abi for the mozglue family; a `_ctype_` provider for the Realm domain),
per the cluster accounting. Do NOT ship it as a solo wall expecting lit keys.

## On-board probe: NOT required to act
④ is statically definitive; the cheapest confirmation for both is to apply the sysconf remap and re-run. A minimal
read-only interposer probe (log `sysconf(name)→ret`, `mmap`/`ftruncate` results inside the appspawn-x child during
`nativeGetSharedRealm`) is only worth it if ③ does NOT clear after the sysconf fix — design in evidence/probe-design.txt.

## Files
- evidence/verified-disasm.txt — the raw llvm-objdump snippets I verified (build-id checks + the instructions above).
- evidence/sysconf-mismatch.txt, evidence/probe-design.txt — the bionic/musl table and the optional probe (from cc-wiki's
  draft, carried forward; the sysconf return values are hw248-source-verified there).
- results.json — keys/clusters/fix summary.
