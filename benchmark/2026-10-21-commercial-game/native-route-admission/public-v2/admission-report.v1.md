# G28 independent offline admission review

**SOURCE_BOUND_UNSIGNED_NOT_ADMITTED.** The original G27 package was invalid at N1 because its profiles still named a historical package. Its unchanged N2 finding count did not establish current source binding. A separate G28 private copy now binds all 30 N1 profiles and both N2 source sets to independently hashed G26/G24 evidence. Original gates execute successfully as checks and still refuse admission: baseline **rc1, N1 55 + N2 104**; candidate **rc1, N1 55 + N2 104**; static **rc2, two ANL aliases REVIEW_REQUIRED**. No exceptions or signatures were supplied.

The exact private copy is `$WORKSPACES/westlake-harness-t37-peer/benchmark/2026-10-21-commercial-game/native-route-admission/.private/assembly-01`. `private-package-index.json` pins every file. `source-rebinding.json` records the 10 changed/added sidecar files, 30 profile relations and source/build evidence. The G27 `assembly-02` remains unchanged. There were no builds, device calls, full preflight, permission changes outside this private copy, registry edits, runtime edits, or deployment/first-start wrappers.

## Current identities and original gate results

| Side | Native package SHA256 (unchanged from G27) | New native input SHA256 | Gate result |
|---|---|---|---|
| Baseline | `10bb13d4a9b54b9aca31ff1bda331d0af9060af6ad4f619ef27ae07d4bd116cc` | `f70388b5fe616423a9f3e006ec0271bd4fb1f43aa937d01d75d79c7fef3ce300` | REJECT rc1; 159 findings, zero exceptions |
| Candidate | `cb9698b76c19df71161b93a8b2c2220412e1d2730d8f9f2d1af092481a2988e3` | `c9198abb28706c55ba253f23ff44dacfb248a3eda17f7579e326b7d878e8c676` | REJECT rc1; 159 findings, zero exceptions |

Bundle SHAs remain baseline `d7d66229124825163bb858bb7caad3ef2039d56d96a8d218f6f017227a52ae45` and candidate `3582e68959a5fe918f7bb2ee057b3582777a61a429e2b25a1b94ac2984235c91`. The private copy retains `rollout_ready=false`. Input SHA changes invalidate the earlier G27 issue IDs; use the newly executed reports, not substituted old IDs.

The original G27 reports are retained: both native rc3 with `historical profile does not bind candidate package: host`; U7 rc2 at static checks, before G1/G2. Their raw hashes and sanitized archives are distinct in `archive-index.json`. New original gate argv, timestamps, real rc, stdout and stderr are under `.private/gates-01/` and exported to `evidence/`. No failed output was overwritten.

## Source and artifact relations

G26 public manifest `5bccf92cf7565a858f27a65bdacf1f779cabbad9dcc71c7a8481302b3331bdf5` and every listed file were rehashed locally. Public host/ANL receipts, their complete source sets, and matching retained ELF outputs were checked. The user's accepted baseline/candidate/function regressions were consumed without rebuilding or rerunning them. The separately accepted remote build archive was not re-fetched.

| Relation | Baseline source SHA256 | Candidate source SHA256 |
|---|---|---|
| Host `candidate-stock-host.c`, copied to `native-checks/n4-host.c` | `8be12abcb99ccc5f7fbd01f31d04b41a0b47db83d0ceac7f6bfda872b34e7b90` | `ea50c2d052c9f53d653cb3691726304b54fc33494427d1326c5ad47113505c20` |
| ANL `app_native_loader.c` | `aa1cd7c09164f1e6eefb928e8bc856ecb4df3ce22f81842d6595911c5c1f1d06` | `946064aac445faff916d83d000f285c014bed3e6b5e23612884a73a085e52c41` |
| ANL `flutter_domain.inc` | `0117797953a738f248d13f9f8be04e76d6052f1e0f70cf0f0e5c88f16472c15b` | `7422698e38f40f0a26e583d602c8826f5d7c4fb47059e1c114b4d3d825fdd99f` |

Host ELF is `2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e` -> `ee5649f2778430e1c997f4bb2d4d4f42f53a46208b4a1b1bbaca185ddf401887`. ANL is `eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c` -> `640b3c87e2f0f86d31b7defbd8b892515636afa61dcbbab5030d422ec1fb7d86`. Policy is `b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7` -> `878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23` on both effective aliases.

Host profiles use the actual G26 side-specific host source and both required headers. Other profiles retain byte-identical artifact/source relations from G24's `n1-current-source-attestation.json` and exact side-specific scan manifests. Policy sources are independently compared with the corresponding G18 baseline/candidate files. Every profile records its original identity, current identity, source records and evidentiary basis. This is bounded build-attested source/DEX review, not universal source-to-binary equivalence.

N2 now seals both real ANL C and included domain source. Domain roots/search/permitted paths and unresolved app-path terms remain unchanged because those actual expressions remain in G26 source; source line locations were derived from each real file. Inheritance remains explicitly untraversed. No provider was invented to suppress `missing-dt-needed`; no namespace or scanner rule was relaxed.

## Exact G24 reuse boundaries

`target-matrix.json` independently compares all 319 targets against G24 and the G27 existing fresh readback. The original U7 pure planner was invoked without preflight/Board APIs and reproduced **319 baseline, 319 candidate, 5 logical changes, 35 planned writes, 30 same-SHA writes, zero additions**. `write-matrix.json` enumerates every planned operation. These are planned writes, not executed device writes.

G27 fresh evidence at 21:29:30 reports boot `a1d869b4-69a2-40a4-937e-4860f5b54239`, parent `4331`, birth `1279054`; both direct and parent-view 319 maps equal the restoration baseline. This is consumed existing evidence, not a new live observation or a future write-window identity check. Boat private restoration evidence and old `74e6` route remain unchanged.

Of the 319 candidate target hashes, **316 match G24**. Only host and the two ANL aliases differ; both policy aliases still contain the G24 `878c…` candidate. All 319 baseline hashes match G24's recovery map.

All 159 findings on each side have exact finding JSON counterparts in the historical G24 comparison. Their package/input/issue bindings are new. Baseline associated object hashes match. Candidate has **five changed-object finding rows**: three N1 rows bound to the changed host, and two N2 directory rows containing the changed ANL aliases. Additionally **all 104 candidate N2 rows must be reviewed in the context of the changed owner/config source**, even when their individual consumer/provider bytes match. The finding count is not evidence that the changed route behavior was covered.

Each side's N2 classes are 6 unknown effective paths, 16 missing DT_NEEDED edges, and 82 uncovered directories. `review-matrix.json` lists exact issue IDs, findings, package/input SHA, every associated object SHA, G24 counterparts, and source binding. Runtime/JNI, namespace, unresolved-path, provider-resolution, symbol-version and real-screen limitations remain. G24's 318 signatures were retired; none were copied.

## Unsigned material and remaining admission steps

`native-review.unsigned.json` contains 318 review items; `static-review.unsigned.json` contains the five original static rows, of which two need signature. They deliberately use review-only schemas, `signature=null` and no approval timestamp/reason. They are not loadable approval registries or static policies. The proposed signature role uses the corrected contract/RUNBOOK convention: `approved_by=outer(claude)` is the old protocol literal; `actual_reviewer=outer(codex)` names the real outer reviewer. No Claude-model review is claimed and no inner-lane signature is supplied.

Both ANL targets have exact static delta SHA `525ea342a3dc4c39c462b7e43570ab4daff469cdfc7572b14587b81c4de53072`: an additional shared-library literal ending in `:libmediandk.so`. The original scanner reports no added/removed open sites or namespace API-call delta. Host and policy static PASS results describe that scanner's bounded delta only; they do not prove unchanged host semantics.

The outer reviewer must decide each current native finding and both ANL static rows using the new source bindings. If approved, the existing static policy and bundle bindings must be assembled by the authorized owner; that changes bundle/plan identity and must be recorded before use. Current native issue IDs remain valid only while their exact package and inputs stay unchanged. The full original candidate preflight, including G1/G2, is still required; it was not run by this lane. Any actual window also needs the contract's fresh identity/lock checks and restoration procedure. Approval of these materials alone is not an apply authorization.

`rebind_source_inputs.py` follows G20 `rebind_n1.py` and the existing copy/schema method. It only makes a fresh local private source-evidence copy and calls the original pure U7 planner. `run_original_gates.py` invokes original main native/static gates and preserves their real failures. `inspect_admission.py` reconstructs review tables from those reports. `export_evidence.py` indexes the persistent exact private package and exports sanitized evidence. No deploy or first-start orchestration is introduced. G14/T38 remain stopped.
