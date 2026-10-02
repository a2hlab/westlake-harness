# Toutiao wall③: dynamic exports, versions and relocation scope

## What was wrong; new rule

The premise that compat015aa3a6 exports all three requested symbols is false:
`__errno` is LOCAL (`0x330c`), `__cmsg_nxthdr` is absent, and only
`__system_property_read` is dynamically exported. A source version script is
not the deployed export table. Static imports are an exposure upper bound,
**not blocked-app or unlock counts**. U9 observed symbol errors must be tied to
the app PID and compared with the first termination before forecasting movement.

This deliverable is offline and `execution_enabled=false`. No device commands,
current bundle edits, namespace experiments or deployment were performed.

## Exact identities and provenance

`identity.json` pins the recorded U10.1/T8 rerun payload: compat015aa3a6,
host65cc3535 and policy0718f01e. Full hashes and raw tool receipts are included.
WHOIS defaults describe an older U9 generation; they are retained, not treated
as the current payload. Outer ACK(90) 15:24:19 recorded these three ELF deltas
from U9. This task is an archive audit, not a fresh live mapping assertion.

Compat50 exports are reproduced byte-for-byte twice from the accepted U10
object/link recipe. The old generated anonymous export map keeps `__errno`
local even though the baseline source map mentions it. No own LIBC version
definitions exist; the `1.0` node is a requirement on libbegetutil, not a
definition attached to our exports. Property/GNU symbols are index1/unversioned.

The factory OH libc reference is fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2.
It has no traceable build-source receipt. `oh61-dynlink-linux.c` e50b30f2,
recorded revision02dd8d, is **reading reference only, not same-source proof**.
The following conclusions are bounded behavior equivalences from the actual ELF:

| Binary witness | Actual behavior |
|---|---|
| decode_dyn80b78, test80c50, store80c88 | DF_1_GLOBAL sets dso+0x230; 88040 is prepare_lazy NOW filtering, not decode_dyn |
| relocation8cf78,8d024–8d0f0 | consumer verneed match records the LIBC hash; initial version-name points to empty byte1d51e |
| provider8d92c–8d940 → check8b20c | provider versym/verdef and request are passed to version matching |
| check8b220/8b224 →8b294–8b2a0 | absent provider version tables accept an empty requested version-name; a named dlvsym query is different |
| saved-scope80f50–81004 | syms_next traversal accepts is_global; otherwise requires relocating plus same/immediate-parent namespace |
| dlopen_impl866a8/867e4–8680c | RTLD_GLOBAL controls retention; otherwise added syms_next links are cleared |

Raw disassembly and version-name bytes are in `evidence/oh-libc-*`.
For these ordinary LIBC-hash relocations, lack of a LIBC version definition
alone is **not** evidence of rejection. Adding a version node is not the
minimal repair. Actual selected provider, query timing and binding remain unknown.

## All166 input/native surface

`consumers.json` contains all166 frozen APK identities and888 native members,
including current different-SHA sidecars. Same-SHA embedded/sidecar duplicates
are excluded; full member path and basename both account for multi-ABI APKs.
Only ELF64-AArch64 participates in the following exposure groups:

| Symbol | Static keys | Native-member witnesses | U9 app-PID error keys |
|---|---:|---:|---|
| __errno | 50 | 256 | ooniprobe, x |
| __cmsg_nxthdr | 19 | 26 | none |
| __system_property_read | 4 | 7 | none |
| __gnu_strerror_r | 14 | 24 | fd-fennec_fdroid, firefox |

The first-three-symbol union is50 keys. Every grouped undefined import requests
LIBC from libc.so (hash0x50d63). ELF32/non-AArch64/non-ELF members are retained
as uncovered/unknown, not clean; dynamically decrypted or downloaded libraries
are also outside coverage. Raw `readelf -V` and target-symbol excerpts are pinned
for each unique affected ELF. Static calls need not run or even load that library.

Toutiao's arm64 ttcrypto(f890c0ba) has one errno relocation, sscronet(38f0dd42)
one errno/one cmsg, metasec(c91fc2ee) one errno/two property relocations.
The supplied runtime occurrences19/4/4 are not unique ELF-import counts.
These libraries NEEDED libc.so, not compat. The complete NEEDED lists are in
the machine inventory. This does not prove their remaining closure is complete.

## Observation-calibrated prediction, not “beneficiaries”

`observations.json` independently scans all166 hilogs in the nine U9 signed
shards, pins each hash, filters matched lines by app-bound PID and invokes
`first_fatal.py`. `predictions.csv/json` covers all166 keys and prioritizes the
four actual error keys; all other static matches remain exposure-only.

| Key | U9 evidence (`hilog.txt` original line) | 4698 exports-only prediction; next wall |
|---|---|---|
| fd-fennec_fdroid | relocation19088; exception cause19103; source shard5cd original | GNU wall unchanged: GNU already exported, no scope change. After a separate proven scope fix, next fatal is unknown |
| firefox | relocation30971; exception cause30982; source shard61b remaining | same GNU wall unchanged; next fatal after successful GNU binding unknown |
| x | errno32245/32246 on TID2929; main_threw32788/root32789 on TID2781 | first fatal unchanged: TelephonyManager null cast; fixing errno cannot be called movement of this root |
| ooniprobe | errno19494; signed lit, no observed termination | negative control, not an unlock or first-fatal movement |

Full run paths, source SHA and numbered excerpts: `evidence/u9-*-hilog.txt`.
The forecast **“expected first fatal moved by4698” is empty**, not a prediction
that the candidate has no runtime effect. Fennec/Firefox have a caught Gecko
load exception and disappearance; the first-fatal tool cannot identify their
killing sender/root. Their observed “Directory separator should not appear”
retry messages follow failed native loading; they are not established future
independent fatal points. A scope-pair forecast may only claim a conditional
GNU **load-wall** movement until owner binding/termination is actually measured.
Toutiao has no requested-symbol error in these U9 logs; its native imports
are an additional conditional target, not an observed first-fatal unlock.

## Minimal candidates and namespace criterion

| Candidate | SHA prefix | Deliberate delta |
|---|---|---|
| exports-only | 4698c0a5 | old50 exports retained, only errno+cmsg added; NOW metadata retained |
| scope-global-reference | 6eaaf919 | same two exports, FLAGS_1 NOW→NOW\|GLOBAL |
| host-proposal | 044bcbc2 | exact r3 host; existing sealed resident query atd6c8 NOW\|NOLOAD→NOW\|NOLOAD\|GLOBAL |

`__errno` uses the existing real __errno_location implementation. The cmsg body
follows AOSP14r1 `__cmsg_nxthdr.cpp`; explicit Android LP64 message/header
structures are necessary because OH controllen has a different width. Header
layout reference is pinned NDK23, not falsely identified as an AOSP14 header.
The host-only fixture tests alignment, exact-end bounds and full64-bit length;
it is not an OH linker or runtime proof.

`evidence/current-policy.json` decodes actual0718 bytes: five system libraries
(including SoundPool) and seven shared sonames (including libstdc++). No stale
U10 JSON overlay is used as policy ground truth. Host r3 gives ordinary apps a
bridge edge and, conditional on the real resident lookup, a compat-owner edge;
Toutiao is not in either private-domain classifier. Its native DT_NEEDED calls
start in the configured app namespace, not automatically the compat owner.
Permission to inherit compat is not saved relocation-search membership.

The static proposal pairs DF_1_GLOBAL lookup eligibility with retention of the
already-resident sealed owner's symbol chain. No application-view NOLOAD,
default fresh fallback, repeated same-parent inherit, new owner or APK rewrite
is added. All namespace edges are exactly r3's; eight open sites remain.
The four r3 INHERIT-AFTER-OPEN may-path findings, DEFAULT-NS and possible
runtime MULTI-NS are unchanged and reproduced verbatim, not hidden/waived.

This pair is **unapproved, owner-oracle pending**. Global promotion affects the
binding eligibility of all52 compat exports, so successful errno lookup is not
enough to declare no regression. Do not rename compat to libc, load another
owner or add another inherit. An app whitelist alone cannot prove membership.

## Offline gates and future falsification

All three candidates have deployed_strings_diff0 (0 drops/0 additions),
abi_diff --calls0 (no removed exports, drift or changed callee sets).
Each compat ABI comparison supplies219 unique real affected ARM64 ELFs;
host supplies the actual0718 loader consumer. Consumer breaks0 checks removed
exports only, **not resolution of every app import**. FLAGS/call arguments are
checked separately by open_site_scan/readelf; call-set0 is not semantic identity.
Two repeats reproduce015a/65cc and every proposal byte-for-byte. Source recipes,
toolchain/input hashes, commands and persistent raw outputs are in both receipts
and `persistent-inventory.json`; large ELFs/objects stay under this worktree's
`.artifacts`, not public Git. Earlier wrong link-root attempt is retained as
`.artifacts/build-failed-link-root.txt`; it produced no accepted candidate.

Python8, Rust4 and four contract scenarios are run, not inferred from test names.
`evidence/validation-receipts.json` and `evidence/preflight.txt` contain results.
No JAR changed; deployed_class_diff does not apply. No N1/N2 admission of a new
generation manifest or window approval is claimed by this offline experiment.

Future authorized plan must bind exact deployed owner/build identities first:
**confirm** = sole resident compat mapping, sealed NOLOAD finds that owner,
actual failing relocations bind to its real implementations, errno warnings
disappear without a new owner; x TelephonyManager root may still remain.
**refute** = unavailable owner, unchanged symbol errors, new provider mapping,
version rejection or regression. Keep owner-unavailable distinct from success.
Independently control export-only, host-only and metadata-only vs the pair;
first termination, load-wall movement and screenshot t20 stay separate axes.

## Reproduction

From the worktree with the pinned persistent inputs:

```sh
python3 benchmark/2026-10-02-toutiao-bionic-scope/audit.py
python3 benchmark/2026-10-02-toutiao-bionic-scope/build.py
python3 benchmark/2026-10-02-toutiao-bionic-scope/build_host.py
python3 benchmark/2026-10-02-toutiao-bionic-scope/verify.py
python3 benchmark/2026-10-02-toutiao-bionic-scope/observations.py
python3 benchmark/2026-10-02-toutiao-bionic-scope/test_audit.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_bionic_scope
```
