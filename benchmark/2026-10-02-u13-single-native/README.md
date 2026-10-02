# U13: two SHA-bound native single-wall candidates

## Corrected assumptions first

The U12 host uses **zlib-route.h / U11ZlibRoot**, not the broader
missing-library-route.h implementation. Importing that broader implementation
would also change audio routing. This delivery changes only one package literal
in the actual U12 header. The host C source and resident-compat header are exact
unchanged copies.

McDonald is also **already selected into westlake_native by eebd ANL**:
app_native_loader.c:64,451,464 and flutter_domain.inc:22,30,42. Window5
hilog:30944 publishes its private-domain runtime, and :30947 identifies
westlake.anl.app.23897.3. U12 now contains the previously absent private zlib
alias/provider. Therefore this additional whitelist literal is **not a proven
incremental U12 gain**: on the selected path it prefixes the same directory
again. Predict conditional movement1 against window5, **incremental0 against
U12**, pending the actual U12 result. Do not count the same alias twice.

## Exact builds and single variables

| Role | Exact reproduced U12 baseline | Candidate, identical twice | Delta |
|---|---|---|---|
| policy | 2a6ec73fd87239ae90ba6464727649f5a4d73aab7588dda392df8803c2e76c4e | b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7 | one resident media alias; six system entries become seven |
| host | 2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e | c28833762f845c89e7cadf0e8a49b431259959c2e21b2b80b381de177443bdd3 | one McDonald package literal |

The policy reuses the already-reviewed native-missing-libraries mechanism:
libmedia_jni.so maps to /system/android/lib64/liboh_android_runtime.so;
SystemLoader sets RTLD_NOLOAD for this SONAME only; the verifier permits exactly
this tuple. SoundPool and mediandk remain, and all seven shared SONAMEs remain
unchanged. No media file or second runtime is introduced. The alias allows the
existing registered MediaPlayer natives to be reached; it is not a decoder.

Source lookup stopped at local exact U12 receipts and reviewed source. The
original Mac SDK compiler and reused objects/libraries were SHA-recorded.
This is not a substituted Linux compiler claim: both exact baseline ELF hashes
were reproduced with the actual U12 Mac recipe. Candidate source paths are
prefix-mapped to that recipe's original names to preserve __FILE__/debug identity.
Build stdout/stderr were streamed into persistent raw files at runtime. See
policy-build-receipt.json and host-build-receipt.json for every command, raw hash,
toolchain hash, reused input and source dependency.

Sources are in sources/{baseline,candidate}, with policy.patch and host.patch.
All 653 dependency contents are retained at
$WORKSPACES/westlake-harness-bms/benchmark/2026-10-02-u13-single-native/.artifacts/frozen-headers/
by content SHA; per-role header manifests are in the receipts. Large ELF files
remain at the exact persistent paths in payload-edit.json, not in Git.

## Static gates, without changing a board

Raw outputs are under evidence/. Open-site and strings checks ran against both
the exact U12 pieces and the signed U10.1T8 pieces. deployed-identity.json binds
the latter to all three boards' expected-run hashes. deployed_whois's map section
still reads U9 even with --generation; those raw U9 hits are not relabeled as
U10.1T8 mapping evidence.

- Policy: direct open sites0, namespace edges0, exports/calls/consumer breaks0.
  The sealed callback remains indirect; absence of direct sites does not prove
  the resident owner is available. Relative to U12, strings drop0/add2: only
  libmedia_jni.so and its exact runtime path. Relative to signed T8, add3 includes
  U12's existing mediandk path. These explicit additions need outer admission.
- Host: open sites8→8, edges17→17, INHERIT-REPEAT0→0. The four existing
  INHERIT-AFTER-OPEN syntactic may-paths stay four; DEFAULT-NS and possible runtime
  MULTI-NS remain raw, not waived as a single-copy proof. Calls/exports/child
  consumer breaks0. Relative to U12, strings drop0/add0: the McDonald literal
  already exists in other host branches. Relative to signed T8, drop2/add5 are
  the existing U12 source-path/private-route delta, not newly added behavior.
- Full two-piece audit: N1 findings53→53 and N2 findings104→104, structurally
  identical, zero new findings. The default registry accepts U12 but rejects
  the new manifest, as expected. registry-delta.json contains157 identical-match
  rows with existing evidence paths; preview reports157 identical/0 new.
  Replay using only this proposed registry passes. **Master registry was not
  modified; this is not final U13 admission.** U13 runtime/compat changes must
  be assembled and all gates freshly rebound by the outer owner.
- No JAR changed, so deployed_class_diff is not applicable.

## McDonald consumer audit

The 10 extracted sidecar hashes match the signed window5 record exactly.
librealmc.so SHA=b7efab7537ed532ecca1dca6fe18878f4f06f3bc78b9fba65a69ed53ba8f1e1c;
DT_NEEDED is liblog, libandroid, libz, libm, libdl, libc. The actual version table,
all221 strong undefined imports and exact provider hashes are recorded. Six
zlib imports (deflate, deflateEnd, deflateInit_, inflate, inflateEnd,
inflateInit_) are present in provider ab0820c6; alias50b9 points to it.

The U12 root/private ELF inventory plus exact factory libc fd3c4701 covers
all221 imports, with zero absent exports. The same holds with U13 VLC compat
b2be657c. This rules out an additional **globally absent export in that audited
inventory**, not an inaccessible owner, incompatible data ABI or wrong live
relocation scope. The private libandroid and inherited factory/bridge owners
are retained, not newly copied into another domain. Next fatal/t20 remain
unknown; do not infer that Realm initialization succeeds from this audit.

## Predictions, rollback and admission

Chessclock: conditional first-fatal movement1 beyond window5 MediaPlayer.clinit
manifest rejection (hilog:43043); same increment over U12 because U12 added
mediandk, not media_jni. Resident-only handle/JNI registration must hold.
McDonald: conditional window5 movement1, incremental U12 movement0 as explained
above. Both next fatal and t20 are unknown. No screenshot/lighting claim.

Each variable has an independent rollback in payload-edit.json: restore policy
2a6ec73f in both Android/route aliases together, or host2a87118e. Do not remove
the existing U12 private alias/provider, add a root libz or copy a libc. Both
candidate deltas are optional inputs for cx-t0; execution_enabled=false.
offline_precheck.json provides confirm/refute observations and requires a fresh
final assembled-manifest gate, outer review and signed rollback before LOCK.

## Reproduction and tests

From the original bms worktree, with the SHA-bound persistent U12 inputs:

```sh
python3 benchmark/2026-10-02-u13-single-native/build.py
python3 benchmark/2026-10-02-u13-single-native/audit.py
python3 benchmark/2026-10-02-u13-single-native/namespace_gates.py
python3 benchmark/2026-10-02-u13-single-native/report.py
python3 benchmark/2026-10-02-u13-single-native/test_analysis.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test u13_single_native
```

The six tests compile host fixtures from checked-in sources into temporary
directories; they require no .artifacts binaries. They assert preserved policy
entries, exact-tuple refusal, missing-resident refusal with NOLOAD, ordinary
loader behavior, package boundary/null refusals and honest consumer limits.
These fixtures are not OH execution or screenshot proof. landing-paths.txt and
preflight output accompany the delivery; no board or live bundle was touched.
