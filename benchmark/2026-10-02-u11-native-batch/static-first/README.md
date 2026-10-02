# Static-first replay of the next-round native handoff

## Correction and boundary

The earlier comparison builds were not a namespace admission. In particular,
`libnativeloader` having no direct PLT open calls does not prove its sealed-loader
callback opens nothing, and an alias absent from the deployed generation has no
valid same-library string baseline. This replay does not waive either limitation.

The reference is the restored, signed U9 generation, not the unpromoted U10.1/T8
candidate. Outer ACK(90) 10:50:30 and ACK(80) 11:01:18 still identify U9 as the
deployed baseline; cc-wiki's 10:09 read-only check reports stock host `1d3b0881`.
This lane performs no device query. `deployed_whois.py` reports the signed U9 maps,
not a live attestation; receipt provenance explicitly preserves that distinction.

## Objects and results

| Object | Selected deployed identity | Candidate / reference | Direct open sites | Raw string result |
| --- | --- | --- | --- | --- |
| Host | runtime/appspawn-x `1d3b0881` | `67753f77` | 6 -> 8 | exit 1: 1 dropped, 15 added |
| NativeLoader | android/lib64/libnativeloader.so `fb9dc937` | `7f348fe5` | 0 -> 0 | exit 1: 0 dropped, 4 added |
| Private zlib alias | absent | donor `50b9ab6a` | donor 0; deployed unavailable | unavailable, not PASS |
| Existing zlib provider | android/lib64/libshared_libz.z.so `ab0820c6` | unchanged | 0 | identity control exit 0 |
| Android OpenSLES facade | android/lib64/libOpenSLES.so `5891f899` | unchanged, no admitted replacement | 0 | identity control exit 0 |
| OH OpenSLES owner | read-only /system/lib64 snapshot `05d8ac90` | structural/feature reference only | 0 | rejected direct-copy negative control exit 1: 2 dropped, 71 added |
| Child | runtime/libwestlake_android_child.z.so `dc73a28d` | unchanged context | 5 | no replacement |

Whois resolves both NativeLoader payload aliases to the same full `fb9dc937` SHA;
each corresponding board path appears in 168 signed process maps. Both zlib
provider aliases likewise have the same `ab0820c6` SHA. Explicit paths and full
hash assertions select every input; no candidate or deployed path is chosen by
a generation-name glob. The OpenSLES Android facade is never mapped in those
signed U9 maps; the system owner snapshot remains a separately labelled object.

### Host additions, removals, and namespace findings

- No deployed host site disappears. The two additions are
  `U10ShareResidentCompat@0xda38` and `@0xdb6c`, `dlopen_ns`,
  `libbionic_compat.so`, `0x6=NOW|NOLOAD`. They originate in the accepted r3
  lineage, not in the new exact-package zlib routing patch. The separately
  replayed `65cc3535` r3 reference already has eight sites.
- The original `main@0xc51c` default-namespace NOLOAD lookup remains at
  `main@0xc8fc`. Thus the raw scanner prints DEFAULT-NS in both versions; there
  is no *new* default-open site. Six total sites are not six `dlopen_ns` calls.
- Runtime, ABI, and system OpenSLES literal opens retain the same printed
  namespace `stack:frame slot [x29, #96]` and NOW|GLOBAL flags. Namespace setup's
  parameter-path open moves `0xcb2c -> 0xcf0c`; its namespace resolver changes
  from `param:x0` to `unknown:ldp x21, x13, [sp, #24]`. This is a static coverage
  gap, **not evidence that the namespace changed or stayed identical**.
- Scanning either host together with the unchanged child retains
  **MULTI-NS confirmed liboh_android_runtime.so**: host stack namespace versus
  child's `global:closure_namespace`. Bridge MULTI-NS remains possible.
  Child's default tail open remains `WLSCPL_OpenPreparedNamespace@0x33a8`.
  This batch does not solve single-owner publication or supersede N11h.

`results.json` matches sites by function/callee/ordinal, retaining old/new PCs
and all namespace/path/flag differences. Stack offsets and unresolved arguments
are not treated as global namespace identities. The upstream scanner is a linear
backward scan, not whole-program control-flow or indirect-callback analysis.

### Media and OpenSLES limitations

The media alias changes the loader table and callback flags, not a direct PLT
open site. Its source uses the existing sealed callback and requires NOLOAD for
the runtime owner; the zero-site listing cannot establish a unique resident
runtime. The raw four additions include `libstdc++.so`, `libmedia_jni.so`, the
runtime path, and the already documented `.rodata` switch-table fragment `..E.`.
No string allowance is used.

OpenSLES remains feature-blocked: Mindustry's PLAY callback/event mask is not
implemented by the true OH owner. Six other consumer profiles remain unknown;
there are zero proved beneficiaries for a new facade. Scanning the real OH ELF
and comparing it with the Android facade is explicitly a **rejected negative
control**, not an admitted candidate. Bitmap ColorSpace and libjnigraphics are
held outside this handoff. There are no JAR edits, so `deployed_class_diff.py
--frozen` is not applicable here; another lane's T8 work is not this batch.

## Receipts and replay

Run `python3 benchmark/2026-10-02-u11-native-batch/static-first/run.py` in the lane
checkout. `results.json` contains full input/tool hashes, command exit codes,
raw/display hashes, site differences and unavailable comparisons. Public
`evidence/` files substitute only workspace prefixes. The original unmodified
stdout/stderr are retained in `.artifacts/static-first/raw/` and appended to the
canonical board with no filtering of MULTI-NS, DEFAULT-NS, or string differences.

These are observational scans: open-site command exit 0 means the listing ran,
not that namespace safety passed. No `--strict` result, assembly gate, owner
proof, deployment authorization, or new point-lighting result is claimed.
Neither U10.1/T8 inputs nor native binaries are modified.
