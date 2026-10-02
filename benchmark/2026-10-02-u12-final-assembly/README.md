# U12 final offline bundle: exact donors, pending outer admissions

The native-only draft was not a deployable U12: it lacked the paired Java/image layer, private zlib, and approvals for new files. The final candidate now contains those reviewed members and remains **unarmed**. Mac and VM production runs both pass the effective JAR frozen-class checks, read-barrier/T4b/G1/G2 image checks, and composed frozen checks. Both production executor dry-runs correctly return **rc2**: three new-native admissions, the final native exceptions, and one exact host open-site delta await outer registration. No board command or lock was used.

## Exact final object

- Persistent package: `$WORKSPACES/westlake-inputs/generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle`.
- Native manifest: `2a3fac8153e080f509cd0949bc521e5e9d81ec37937c312689fb1fec2b1494df`.
- Bundle: `bf6c0fb67d76f1f1d54725738b78f58d24483ceeac66087e2e801d74d1b650ee`.
- Signed base: U10.1T8 bundle `190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736`.
- Independent fresh assembly reproduces **both SHA identities exactly** (`reproduction-result.json`). The initial copy-helper naming error is retained as failed evidence; no half output was reused.

| Member | Final SHA prefix | Source / decision |
|---|---|---|
| libicu_jni |1e206531| cc-wiki reviewed deployed-era 63-export zero-init build; `benchmark/2026-10-02-u12-icu-zeroinit/` |
| root libmediandk |8fc0752d| cx-bms reviewed typed unsupported codec provider; ZigZag private110d unchanged |
| libnativeloader, both aliases |2a6ec73f| media root policy, SoundPool retained; private-zlib changes no policy name |
| host |2a87118e| exact private-zlib donor, master8eaedb546d; r3 resident-compat/INET preserved |
| private libz alias |50b9ab6a| copied r109c original, real-work be16148da9ae7bb89c62e81e144ed0bceb5c4669 |
| private libshared_libz.z |ab0820c6| original reviewed deployed bytes copied; historical build provenance unknown |
| runtime JAR |0482c9b1| U12 r2 donor,10 exact added classes, no effective class drop/reshape |
| stubs JAR |615b8bbe|265 original effective classes unchanged, Predicate added; no android.net additions |
|27 boot images| run1 | exact FZ-005 bake products paired with own dex2oat log b7a17337 and session935cf0f1 |

The stubs and all27 images are one stopped-parent transaction. The eight other boot JARs retain their signed hashes, including framework2257b835. The nine actual bake inputs and27 outputs are checked before copy and bound by `receipts/u12-paired-build.json`; the actual log SHA is checked against the persistent file. Run2's different boot.art is not mixed into run1. `N11h-r2` and compat-relocation are deferred to U13. Childdc73a28d, libart59e1bb45, compat015aa3a6, the generation identifier and provider owner stay unchanged. No runtime identity bypass is introduced.

Private-zlib donor alters only host plus two new files in `westlake_native`; it has no policy member. `policy-composition.json` therefore records **no policy collision**; the media policy is retained byte-for-byte. No root libz alias is added. Both private files and new root mediandk require their own exact target/SHA/final-manifest admission rows. `new-native-admissions-draft.json` contains three proposals, not registry writes.

## Real gates and review queue

| Gate | Mac | VM |
|---|---|---|
| Actual DEX read / LLVM tools |PASS|PASS|
| Runtime / stubs vs effective5ae3dd29 /2f365a75, frozen |PASS / PASS|PASS / PASS|
| rb / T4b / G1 / G2 |PASS / PASS / PASS / PASS|PASS / PASS / PASS / PASS|
| Native frozen + full three-board identity frozen checks |0 violations|0 violations|
| N1 findings |53 raw rejects, all identical|53 raw rejects, all identical|
| N2 findings |104 raw rejects:103 identical+1 new|104 raw rejects:103 identical+1 new|
| Production executor dry-run |rc2 / refusal|rc2 / refusal|

`auto_approve_exceptions.py` ran **without --apply** against the signed final U10.1T8 report:156 identical,1 genuinely new. `registry-delta-draft.json` holds the156 proposals; `needs-outer-review.json` holds the new N2 `77b7a8bff2b4…`: private `libshared_libz.z.so -> libc.so`, searched private path only, inheritance deliberately not traversed. The existing103 N2 rows are unchanged. Neither inherited runtime libc visibility nor BurgerKing lighting is claimed proven.

Host exact static delta: candidate2a87118e / deployed65cc3535 / `f42549141b489e5053081c44f6cb00be30c86edf20a688f3dc8f6e3a57d095c0`. It reports the same existing open expressed as `param:x0` versus `stack:sp+24`; named namespace API call sets and literal sets are unchanged. **This remains REVIEW_REQUIRED**, with raw signatures in `host-open-delta-review.json`; the assembler does not self-declare it harmless. Final ABI exports/signatures show0 drift; host calls add only U11ZlibRoot. ICU has12 call-set differences (zero-init memset, C++ implementation and diagnostic differences); the reviewed artifact is copied, not advertised byte-identical to the old ICU. ABI reports contain no supplied host-export consumer set. Actual mmkv crc32 coverage is the donor's separate consumer check.

The first ABI helper run hit old NDK nm's unsupported `just-symbols` format. Failed outputs are retained. Actual installed OH LLVM15 nm, also invoked through the VM `mac` proxy, then produces0 export/signature drift. Namespace production scanners retain their established tools. New member self-strings comparisons prove identity only, never a nonexistent deployed baseline. Large incidental OAT string diffs from an early overbroad supplemental scan are archived outside git; image gates are their authoritative checks.

## Disabled Stage A plans

`plan-{5ea,5cd,61b}.json` partition166 unique keys as55/55/56. Signed baseline116 lit keys are prioritized37/38/41. Each window is45 minutes with no new key after35; unmeasured keys remain unknown and continuation uses the same bytes. Lottery keys use the frozen k/n registry; a single white is inconclusive. The required comparison is `pair_sheet --reference benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference --signoff benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json`. This lane reports no lighting count.

Every `before_unlock` unconditionally rolls the journal back to **U10.1T8**, verifies318 assertions /316 unique paths, parent+child views and single ART, runs fresh HW/ZZ restoration smoke, and verifies final identities again. No signoff can retain a Stage A overlay. OrganicMaps cleanup uses the production transaction's cold_stop fallback. A restoration failure propagates and board_run keeps the lock. Unit tests verify rollback→identity→smoke→final order and failure propagation.

Candidate identities are321 assertions /319 paths. Conventional batch RUNTIME includes124 files:5ea/5cd `2d68dbfeae64`,61b `bba1d36df76e`; BOOTIMAGE36 files `ee927db88a67` on all three. Private zlib is covered by complete identity assertions and child view probes, outside the conventional root/route fingerprint globs. Installer service hashes stay per-board; no foundation restart or libinstalls alignment is included. Recovery fingerprints are5ea/5cd `f3b604c94df4`,61b `d6848fa2c989`, BOOTIMAGE `e3806b65a079`.

Plans have execution_enabled=false and a refusing offline_precheck, so even a direct runner call cannot reach LOCK. `dispatch.py` checks admission and real VM DEX/LLVM readiness, orb/HDC/shared bind before invoking master board_run --detach. Its real infra path is intentionally not exercised offline. `admission-template.json` is not an approval. Enabling requires outer registry/static review, current actual Mac+VM production gates, coherent bundle/composition arming, updated SHA bindings in all plans, and an exact outer `admission.json`; no enabling action was performed.

The prediction table references oc-t4's admitted CSV. Owner/double-copy columns are U13 context and are explicitly not U12 gain claims. API advancement, snapshots and unchanged lighting remain unverified until Stage A and outer pair-sheet review.

## Verification and provenance

Mac and VM each run5 focused checks;3 agent-spec selectors PASS. All commands and reports are under this directory. `persistent-native-provenance.json` identifies the copied73-header/source closure and4 original compile/link runtime logs in the versioned persistent generation folder. Java/images and ICU/media donor receipts remain at their versioned persistent inputs. `raw-evidence.json` maps exact original reports to public copies normalized only for workspace/home prefixes. No large ELF/JAR/image is committed.
