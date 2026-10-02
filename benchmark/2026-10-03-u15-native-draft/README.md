# U15 native-only draft — disabled, NSD/image pair pending

## Evidence first

Three accepted objects are composed into **four** U14 payload paths, with no
additions/deletions. Host and both ANL aliases move together. The two U14 content
bundles remain unchanged: common `9b42ddc6`, 61b `f5898447`; this does not claim
either was promoted. Board-local libinstalls identities remain common `2c9a5294`
and 61b `51e1b525`, at both service paths.

| Member | U14 content SHA prefix | U15 SHA prefix |
| --- | --- | --- |
| `android/lib64/liboh_android_runtime.so` | `18763dd4` | `94c31177` |
| `runtime/appspawn-x` | `341c1260` | `9e3ad72e` |
| `android/lib64/libapp_native_loader.so` | `eebd62f2` | `b96a8991` |
| `route/libapp_native_loader.so` | `eebd62f2` | `b96a8991` |

Full hashes and persistent donor paths are in `composition.json` and
`donor-receipt.json`. Both builds of each object were SHA-checked; this lane
**did not rebuild** them. Donor code, patches, recipes and historical build
evidence are hash-bound in `source-snapshots.json`. Full donor closures/logs
remain at `westlake-inputs/generations/u15-{runtime-m3,jitsi-native-domain}-v1/`.

Native manifest:
`3f60490bf5b102814e004d77c21c549cfeea7bff9fe42a5f721f49389dfa73eb`.
Native gate inputs:
`8ebe1114615048089d9dac115482aa61fc0cc0d231841b3e8e664635b9d0dfed`.
Persistent partial package:
`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-native-draft/.artifacts/native-only/`.
There is **no bundle descriptor or bundle SHA**. No deployment/production
executor can consume this as a completed U15 bundle.

## Source correction and atomic routing

The first source check rejected an incorrect assumption: the donor's
`inputs/candidate-stock-host.c` is **builder input**, before the recipe patches.
The actual final compiled host source is the persistent release's
`u15jitsi-stock-host.c`, SHA
`63e2d25a6c383cd886b57b3b0220da03b6f0139bbbfba208a7165b272cc17217`.
N1 is bound to this final source, not the unpatched input. The failed check ran
before creating the partial directory; no half-built package was selected.

Both `native_cluster_path()` lists now contain the same **14** entries, including
`org.jitsi.meet` once. The host also includes `/org.jitsi.meet/` in `needs_runtime`.
This preserves the donor's intended resident-runtime publication. Updating only
ANL or host would not enable the native-private branch; the package ships neither
alone. The ANL root and route copies are identical, with both inventory/live
hashes updated. N2's namespace owner is rebound to **b96a8991**, and the actual
ANL source/include is retained alongside the host source.

The ordinary open-site delta does not see package-list growth. Empty namespace
delta **does not mean routing behavior is unchanged**; the bare package literals
appear in the raw strings comparison and are separately checked in
`route-lists.json`. Static membership is not live relocation or single-owner
maps proof.

## Fresh Mac gates against U14 content

Raw output, exact commands and raw/portable evidence hashes are recorded in
`report-summary.json`; only workspace/home paths are normalized for publication.
`deployed_whois` output is kept, but its historical deployment observations are
not used to assert U14 promotion. Each comparison uses an explicitly selected,
SHA-checked U14 member, never a same-name glob.

- Baseline native gate: **PASS**, N1 **99 excepted**, N2 **105 excepted**.
- Candidate native gate: raw **REJECT**, N1 **99 rejected**, N2 **105 rejected**,
  **0 errors**. None has the candidate's new binding in the active table.
- Semantic comparison: **204 auto-identical previews**, **0 new N1 / 0 new N2**.
  `registry-delta.json` is **not applied**. Final BCP/manifest identities will
  change again; do not treat these draft rows as final binding or approval.
- `check_frozen --package` on the native-only inventory: **exit0**. This does not
  attest new U15 images or new NSD BCP classes.

| Object | Open sites U14 → U15 | NEEDED | Export drift / consumer breaks | Call-set differences |
| --- | --- | --- | --- | --- |
| Runtime | 197 → 197 | unchanged | 0 / 0 | **1** |
| Host | 8 → 8 | unchanged | 0 / 0 | **0** |
| ANL | 0 → 0 | unchanged | 0 / 0 | **0** |

All three have **0 export additions/removals**, **0 signature drift**, and **0
breaks** against the pinned **219** native consumers. Those intersections do not
prove the consumers' live namespaces can resolve each provider.

The runtime's sole changed call set is `android::jni_eglCreateWindowSurface`:
add direct `ANativeWindow_fromSurface` and `HiLogPrint`, remove `dlsym` and
`fwrite`. This is the accepted M3 change, not an ABI-only assertion of identical
behavior. Host/ANL list/body edits may leave call sets unchanged.

All three production-schema deltas have empty added/removed sites, namespace
API changes and namespace literal changes; common delta hash
`a79aabf880b7689eec5ff785be683d4574fe58eca55ae4f0a39f3efba100d339`.
`static-deltas.json` includes the complete four-field schema used by production,
plus every namespace edge and raw DEFAULT-NS/MULTI-NS finding. No allowance or
outer signature is invented.

Strings remain raw **exit1** with no allow list:

- Runtime: **4 dropped / 5 added**, including removal of the failed string-based
  converter lookup, new M3 HiLog literal and raw read-only-data fragments.
- Host: **4 dropped / 6 added**, including source-path changes, the Mindustry IID
  check change, `org.jitsi.meet` and `/org.jitsi.meet/`, and pointer-text fragments.
- ANL: **0 dropped / 1 added**, exactly `org.jitsi.meet`.

Review exact raw strings; do not silently discard data fragments or apply a
generic path/string allowance. Full bundle `generation_static_checks` remains
pending because this partial package deliberately has no bundle descriptor.

## BCP, images and transaction hold

The native inventory retains **U14** framework `3e106350`, stubs `87cf65cc` and
non-BCP runtime JAR `0349eb83`. The separately arrived framework `9e55e286` is
**not installed here**. The new NSD stubs donor is unknown at this snapshot.

`rebake-hold.json` explicitly supersedes the previous **framework-only** execution
intent: wait for NSD, then bind both changed BCP inputs and bake the full **27**
group once, with two reproducibility runs. Do not execute the older U15 plan
first. Neither the U14 pair nor its boot.art exception covers the new pair.
Final native/JAR/source profiles, boot image receipt, manifest/inputs and
exceptions must be rebound after the exact new stubs and images arrive.

Common and 61b transaction bases remain **null parameters**, distinct from the
content base. A later finalizer must use signed full per-board expected state,
preserve the installer identities, and not borrow old `reference/runtime` files
as promotion evidence. Fresh image/RB/T4b/G1/G2 and Mac/VM production gates are
**not run**, rather than inherited from U14.

Conditional donor first-wall targets are M3 **3**, Mindustry **1**, Meet **1**;
**observed movement here is 0**. Meet's next RN/Hermes/WebRTC wall is unknown;
the unused JSC library is not counted as a Hermes-path failure. No lit or
single-owner result is inferred from the native replay.

## Handoff

`landing-paths.txt` includes reports, portable source/recipe snapshots and cold
tests, never ELF files or private native-gate closures. Tests run without
`.artifacts` or other worktrees; Rust selectors bridge the Python tests. The
outer reviewer lands the `documentation.json` root-document snippets, not the
accumulated root documents. No git writes, push, active-registry apply, VM,
native build, bake or board operation is performed by this task.
