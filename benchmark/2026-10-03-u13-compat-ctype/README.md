# U13 compat-v2: original Android legacy ctype pointer

## Correction first

McDonald already passed its private zlib wall on U12. Window4 PID31476 failed on `_ctype_`, not `libz`: [`evidence/mcdonalds-u12.txt`](evidence/mcdonalds-u12.txt), original hilog30959/30974/30988. Hostc2883376 therefore stays out; U12 host2a87118e remains byte-identical.

A globally deployed export is not relocation-scope proof: U12's pthread bridge already exports `_ctype_`, yet this consumer failed. This candidate adds the data symbol to the existing resident compat, without creating an owner, opening a library or changing namespace edges. **One conditional McDonald first-wall move, zero observed moves; next fatal and t20 unknown.**

## Exact source and ABI

- AOSP `android-14.0.0_r1`, bionic commit `e4df46f213d8d363017dce7ded5d1f2159614425`, TUNA sparse mirror supplied read-only by outer. All six original files, `SOURCE.txt` and `SHA256SUMS` are under [`inputs/aosp/`](inputs/aosp/). Local lookup lacked the original table; a2hlab read-only lookup timed out and sandbox denied hw248 SSH. No other-tag donor is represented as14r1.
- Unmodified original `ctype_.c` SHA8fc63bd8 is included by [`ctype_compat.c`](ctype_compat.c). Eight constants come from14r1 `bits/ctype_inlines.h` SHAe18789b4 and `openbsd-compat.h` aliases. The empty, explicitly local `inputs/shim/ctype.h` prevents unrelated OH header classifications; it is not an Android header substitute.
- `_ctype_` is a **GLOBAL OBJECT of8 bytes**, relocated to a private **LOCAL257-byte** `_C_ctype_`: EOF slot plus256 character entries. All257 ELF bytes equal the original parsed table. Digits have class4, not68; `A`65, printable space136, tab40, high bytes0.
- Realmc SHA b7efab75 imports `_ctype_@LIBC`, GLOB_DAT0xb8b3e8; PC0x7715e8 loads the pointer and0x7715f4 reads `base[byte+1]`. Exporting a bare257-byte array would violate that ABI. The new export remains unversioned like the existing compat; actual LIBC-version acceptance and resident scope require the real linker, not symbol-name normalization.

## Reproducibility and gates

Baseline b2be657c was reproduced **twice byte-for-byte before modification**, using the frozen compiler SHA6a5ec844 and all exact reviewed object files. Candidate **b8a87f6fe2902b1d1c9e8440714d32dbdfd05d75dc1a2993fd2624af91d15abc** was also built twice identically. [`build-receipt.json`](build-receipt.json), [`persistent-inventory.json`](persistent-inventory.json) and the real tee logs preserve compiler/linker/object/source provenance. No strip or binary patch follows the gates.

| Check | Result |
|---|---|
| ABI vs b2 | 54→55 exports, only `_ctype_` added; removal0/drift0/calls0 |
| Consumers | Same219 real ELF consumers, breaks0; exact list/hashes retained |
| Source/ELF table | pointer8/table257; all bytes matched |
| Open scan |2→2 opens, namespace edges0→0; existing DEFAULT-NS/UNRESOLVED retained |
| Raw strings vs b2 and deployed015aa |0 drop/1 add, exit1; one readelf printable projection of the original binary table, **not silently allowed** |
| N1/N2 full new-manifest check |U12 PASS; candidate REJECT pending rebinding: N1 53→55, N2 104→104;157 auto-identical candidates and the same2 full-gfx NOLOAD review sites |
| Registry |unchanged, no apply; every proposed approval is null |

Original outputs are in `evidence/`. `android_dlopen_ext`'s raw unknown-clobber string now points at **0x3b98** (b2:0x3a58, deployed:0x3758). The inherited two-call structure is unchanged, but raw signatures still require review. The deferred U13 gate-review package must bind this new manifest, not7615b424.

## Consumer limits and forecast

[`realmc-consumer.json`](realmc-consumer.json) records **221 strong versioned imports**, exact direct providers, factory libcfd3c, transitive provider choices and unresolved inventory dependencies. Factory libc+compat alone is not the complete app dependency graph: log, ALooper, zlib and additional bionic bridge exports belong to other providers. Direct-only gaps disappear when the reviewed runtime/zlib NEEDED providers are included; the available closure has **zero remaining strong-import gaps**, but its recorded inventory holes and namespace access remain unproved. Do not promote that to a complete dynamic-linking PASS or a specific next exception.

The current candidate addresses the missing `_ctype_` export in compat. It does not add `__errno`, `__sF`, fortify exports, routing, loader version nodes or a second owner; any later relocation/Java/rendering failure remains a separate wall. No static upper-bound importer count is reported as an unlock count.

## Separate disabled rebind and rollback

The previous U13 bundle473ba28d/manifest7615b424 remains untouched. New persistent package:

`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-compat-ctype/.artifacts/bundle-v2`

- Bundle **adf3705043472de8797a677d76c16b5976cb9c0be11364daa3bbd1b882b1698b**.
- Native manifest **c60d03460f14ec5bdff2031d56792adcc2985f948a8a0cf5189d1fa9cee7575e**.
- Only `payload/android/lib64/libbionic_compat.so` and `payload/route/libbionic_compat.so` change together to b8a87f6f. Runtime18763/policyb8be/host2a871 and all JAR/boot files remain unchanged.
- `rollout_ready=false`, no window authorization, execution disabled. Fresh production dry-runs and outer exact native/static approvals are still required; old PASS does not transfer.
- Roll back both aliases atomically to b2be657c using the untouched old bundle, or the entire approved U12 package when outer requires it; no executor is invoked here.

## Replay

Run from the retained lane checkout, not master with absent `.artifacts`:

```sh
python3 benchmark/2026-10-03-u13-compat-ctype/collect_sources.py
set -o pipefail
python3 benchmark/2026-10-03-u13-compat-ctype/build.py 2>&1 | tee build-new.log
python3 benchmark/2026-10-03-u13-compat-ctype/verify.py
python3 benchmark/2026-10-03-u13-compat-ctype/audit.py
python3 benchmark/2026-10-03-u13-compat-ctype/test_analysis.py
```

The landed tests compile the landed table source in a temporary directory and inspect admitted evidence; they do not require private `.artifacts`, APKs or remote access. Missing host compiler is explicitly skipped, not presented as native execution proof. The host test checks table/pointer semantics only, not OH relocation or UI.
