# U10.1T8 source reconciliation: do not land lane HEAD blindly

## Correction and rule

The old assumption was that branch-only source changes were the source of the current deployment, so copying either newer branch would restore provenance. The actual deployment is an **override-and-cached-object composition**. The matching loader source is on neither lane HEAD, the runtime uses four different source snapshots, and the native-loader source already on master is correct. Copying the b4 fallback would introduce a behavior not in deployed policy0718.

Rule: bind the actual board-pinned ELF first, then the archived output, build receipt, object set and source snapshot. Strings/symbol matches are corroboration, not a source-identity proof. A same-named platform library missing from the native package is not necessarily absent from the board.

This audit ran **zero native compilers/linkers and zero device operations**. It did not change U10.1T8 or any bundle. `results.json` enumerates **26 branch entries / 23 unique paths**, and `DECISIONS.md` provides every decision. Three paths have conflicting versions on bms-deploy and b4: hwui, app-native-loader and its host test.

## Selected production sources: nine paths

| Canonical target suffix | Selected snapshot / SHA prefix | Actual artifact and evidence |
|---|---|---|
| android-runtime/src/AndroidRuntime.cpp | N10b smoke-markers/src, `141791a7936e` | ac59 runtime, explicit N10b recipe override, AndroidRuntime.o `e7c5fd294372` |
| android-runtime/src/android_graphics_compat_shim.cpp | N2/src, `b94f69e4c68a` | ac59 cached object `40aa2f5fe597`, identical from N2 through N4 to N10b |
| android-runtime/src/android_media_AudioSystemCapabilities.cpp | N2/src, `31e0f98a8ca5` | ac59 cached object `5bbb0f004999`, identical N2/N4/N10b; also matches bms-deploy |
| android-runtime/src/android_view_SurfaceControl.cpp | N2/src, `391fd84f1980` | ac59 cached object `ca321964950b`, identical N2/N4/N10b; also matches bms-deploy |
| app-native-loader/src/app_native_loader.c | N3/flutter, `aa1cd7c09164` | archived N3 eebd62f2 equals both effective deployment aliases; N3 source manifest and DWARF point to this snapshot |
| stock_child_plugin/src/westlake_stock_host_main.c | accepted r3 snapshot, `507bf160dfae` | archived host65cc3535 equals deployed host; receipt pins source/header/reused objects |
| package-manager/jni/apk_installer.cpp | background-launch source archive, `45438280ccc1` | installer7048c7c5, exact source equals bms-deploy; immutable build archive + signed expected-per-board identity |
| package-manager/jni/launcher_activity.h | same installer archive, `ec4f44f9b29f` | same7048 archive, branch snapshot matches; native launcher-selection behavior belongs to installer, not libinstalls |
| package-manager/jni/oh_adapter_install_apk_c_entry.cpp | same installer archive, `a4cdaf259a80` | same7048 archive and typed C entry symbols; branch snapshot matches |

`results.json` records full source hashes, source commits where available, master preimage hashes and per-entry branch commits. The source copies under `sources/bms/src/...` are byte-exact, not rewritten portable substitutes. Four exact included dependencies accompany these nine production sources:

- Runtime `surface_session_identity.h`: N2 `ea57d26b4807`.
- ANL `flutter_domain.inc`: N3 `0117797953a7`.
- Host `resident-compat.h`: accepted r3 `e4f7321547d6`.
- Installer `apk_network_permissions.h`: background-launch archive `c68cfac4657c`.

Do not substitute the newer N12 zlib host, N11h owner host, N10 ANL or icon-decoding candidate. They are separate candidates, not U10.1T8 source reconciliation.

### Runtime object evidence

The authoritative recipe is `benchmark/2026-10-01-n10b-child/smoke-markers/build-runtime.py`, not the canonical stage2unity script. The receipt pins candidate and repeat runtime to `ac59dec077195bc7678c712505b0d802c56e07edea8d049be4a188d20485b7bf`. This audit hashes the existing candidate/repeat objects and checks them against that receipt; no rebuild occurs.

`evidence/runtime-object-selection.json` gives each object's full SHA and defined-function intersection with the actual linked runtime. Three TUs are exact copies of the authenticated N2 object cache. N2 `restore_cache.py` explicitly removes these changed objects, its source manifest pins the three snapshots, and the N2/N4/N10b object bytes remain identical. N10b intentionally replaces AndroidRuntime.o with its smoke-marker source. In contrast, bms-deploy's current AndroidRuntime and graphics shim are different bytes and must not be copied as the compiled source.

Existing artifact comparisons in `evidence/{runtime,host,anl,policy,installer}-strings.txt` are all exit0, zero drop/add and exact ELF SHA identity. This proves that the archived comparison artifact is the deployment, **not** that a newly relocated canonical source automatically rebuilds identical ELF. Source paths, basename, headers, compiler flags, reused objects and debug-prefix/cwd mappings still matter. Full rebuild reproduction is deliberately outside this read-only task.

### Platform installer is not libinstalls

`deployed_whois libapk_installer.so` reports none in this native package; its U9 app maps also never mapped the installer. Those are tool coverage limits, not board absence. `bundle/expected-per-board.json` independently pins `/system/lib64/libapk_installer.so` and `/system/lib64/platformsdk/libapk_installer.so` to **7048c7c5 on all three boards**. The archived installer bytes and stripped build output match that full hash; six signed identity entries are frozen in `evidence/special-artifact-pins.json`.

The libbms front-end remains6aadb8b4. `libinstalls.z.so`2c9a5294 versus51e1b525 is the separate already-reviewed unification plan and is not modified here. Its Toutiao payload exception is not a reason to choose a different `apk_installer.cpp`. Likewise the later malformed-icon fallback is not present in7048 and is not silently added to its source.

## Files deliberately not landed

All 26 rows have evidence; the remaining **16 branch entries** are not production-source updates (10 branch entries select nine unique production paths):

- **Both hwui variants:** deployed `be59260f93b3debe1ad64cc8e7b6b0575e5be04794b46f8eb876436d1ebc9b74` has no reproducible frozen source closure, as already adjudicated. bms-deploy and b4 retry predicates differ; neither receives a provenance waiver. Both remain `UNKNOWN-NO-LAND`.
- **compile_sigchain_muslcompat.sh:** Android copy42062f49 and route copy6d5d5538 are different actual ELFs. This branch's one-line script change does not prove the build source for both copies. `UNKNOWN-NO-LAND`; source recovery needs the matching per-copy receipt, not a guessed compiler.
- **stage2unity runtime script:** actual N10b recipe/object override is separately pinned. The canonical lane script is not the used build recipe; do not overwrite newer master build hardening or silently turn cached-object replay into a full rebuild.
- **Three host-test/mock entries:** tests are not compiled into production eebd. Neither branch test version can be selected by its ELF; retain pending adaptation to the authenticated N3 loader rather than landing the newest test by chronology.
- **child_main_after_stock.cpp:** N10b deployed childdc73's receipt compiles `sealed_child_provider_loader.c`, not the legacy C++ entry. The older U9 input receipt listing this CPP is not proof it executes or identifies the current provider owner's compiled source. Selection remains `UNKNOWN-NO-LAND`; this is not a claim that every other provider artifact was proved to exclude the CPP. Do not land the branch's CM-BIGSTACK implementation by inference.
- **Six stock_child_plugin metadata/scripts other than main:** ROUTE_A_INPUTS, SOURCE_CLOSURE, container builder, input generator, identity env and verifier describe the historical baseline. Current host is the r3 override plus authenticated reused objects. The old generated metadata does not close provenance for the new ELF, so none is copied as a complete U10.1T8 recipe.
- **r45-dynamic-roots/SHA256SUMS:** historical bridge22df3988/runtime7e1fd94e are not effective bridge84695d62/runtimeac59dec0. Leave the frozen registry untouched.
- **b4 native_loader.cpp:** `KEEP-MASTER`. The exact0718 policy source is `cdd53c08...`, already in master and in the outer's frozen U10.1 policy repro tree. b4 `13f2628c...` adds implicit `LD_LIBRARY_PATH` behavior absent from that deployed source. Do not reintroduce it or the rejected0048/621c policy baseline.

Every residue's branch-versus-master textual evidence is separately stored as `evidence/residue-NN.patch`; these are diagnostic differences, **not approved application patches**. Only `selected-sources.patch` is the selected source patch. Unknown, historical and test rows are absent from its target list.

## Landing: two explicit stages

1. Normal `landing-paths.txt` admits the benchmark, exact source snapshots, tests and specs using `land.py --preflight`. It does **not** authorize copying any bms/src path: that tool's allowed prefixes do not include bms/src.
2. After source review, the outer applies `selected-sources.patch` to master, or copies precisely `source-landing-paths.txt` from the corresponding `sources/` snapshot. **13 paths total**: nine production and four included dependencies. The audit ran only `git apply --check`, exit0; it did not apply or stage the patch. Check each master preimage SHA before application and each selected full SHA afterwards. If a preimage changed, stop and reconcile; never overwrite blindly.

This is a source-alignment proposal, not a new deployable generation. Existing immutable source/object archives and recipes remain required. No claim is made that hwui, bridge, sigchain or the complete historical generator is now source-reproducible. Before a future candidate build, persist its exact source/header/toolchain/object closure and build logs, then compare against actual deployed ELF with strings/ABI/calls/consumer and N1/N2 as required by that candidate task.

## Replay

`python3 benchmark/2026-10-02-bms-source-reconcile/audit.py` reads the existing local deployment/archives only and exports evidence. Its admitted unit tests use only this directory's small frozen files, with no external worktree, `.artifacts` or binary dependency:

```
python3 benchmark/2026-10-02-bms-source-reconcile/test_audit.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test bms_source_reconcile
```
