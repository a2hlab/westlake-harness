# U13 final assembly: disabled bundle v3

The old transfer rule incorrectly expected stable N1 issue IDs after replacing a JAR included in the native inventory. Two other admission mismatches were found by the fresh report: the reviewed compat delta omitted empty namespace fields included by production hashing, and the final JAR removes the defective anonymous `GcmDefaultNonce$2` class relative to the actual U12 JAR. All three were reported before transferring approvals; outer explicitly amended the conditions. **Fresh Mac and VM production gates now pass for the exact final package. It remains unarmed: outer Phase A authorization is still required.**

## Frozen composition

| Item | SHA256 |
|---|---|
| Final bundle | `bd83d846bc6c3a47a1a8e6431051d874d0cdd30db0687b3338ddd0f3fc61141d` |
| Native manifest | `85aef68eafbde98e6ac885264fe36f2f1e357618abf1d455de6ca15c0996cee6` |
| Native inputs | `c40faa79d197f023dbe47a62ae186d5eb5671f9b8f4a448924098fdd5f02f185` |
| Runtime JAR, both copies | `bbc3f530190fe98e2979dc4059379f8a0259d1f6ab243830347ca875cdb62f9b` |
| Runtime | `18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae` |
| Compat, root and route aliases | `b8a87f6fe2902b1d1c9e8440714d32dbdfd05d75dc1a2993fd2624af91d15abc` |
| Policy, root and route aliases | `b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7` |
| Retained U12 host | `2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e` |

Persistent package: `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-final-assembly/.artifacts/bundle-v3`. Large binaries remain outside the landing list. `prepare.py` replaces both `framework/oh-adapter-runtime.jar` and `native/payload/android/framework/oh-adapter-runtime.jar`, updates the payload/effective-target hashes, and regenerates native scan/input bindings. No native ELF or boot-group byte changes relative to bundle v2; host `c2883376` is excluded. The final bundle retains `rollout_ready=false` and no window authorization. Previous bundles are not overwritten.

`composition.json` retains all three per-board expected inventories (319 targets each), including their installer difference; runtime fingerprints are `821de739cf81` for5ea/5cd and `452447a4a0ba` for61b, boot fingerprint `ee927db88a67` on all three. These are planned hashes, not a board observation. Actual Phase A baseline/recovery remains cx-t0's independently reviewed U10.1T8 plan; this assembly does not change that plan or promote U12.

## Exact approval transfer

Authority: master `benchmark/2026-10-03-u13-gate-review/outer-approval.json`, including its three addenda; local immutable copy `evidence/outer-approval-final.json`.

- Bridge NOLOAD: `b8e9f93b57e743d0402e9e31461b0b094d52d1aeb2559a7dc3289462e7a8dcb3` → `58ca33ba0db39dce7607e86d25259a27f9b0a53d4aed80aa921716bb3e40dfd7`.
- EGL NOLOAD: `c839a571ad9e81b7d2acfd0ee2da442527b02290e7a15c8a24cd53e1ec7416ed` → `9c9e31d2fe7ee373fa3e1d3e428fafd2d2e3bb85ee0965c4ca1309546503a910`.
- Only `issue_id`, `disposition`, and attached `exception` metadata are excluded from comparison. Profile, function, namespace, library, expression, source, line, text, kind and reason are identical. All159 final IDs remain bound to the exact manifest and inputs. Approval rows belong in the binding registry, not inside the package whose own hash they bind.
- Production delta `ab8d10e396a0288b9fa6195b517ad272616d0e0ba2efd350955c94c7f007a866` replaces void `2cd13b3d...`. The only schema difference is inclusion of empty namespace API/literal changes; no field is stripped from production reports. Both compat aliases share the same paired hashes and approved delta.
- Strings review retains exactly one `_C_ctype_` binary-table ADDED row, zero DROPPED and no new row. Source table and data-pointer proof remain in the prior reviewed ctype package; no extra native modification was made here.
- JAR allowance permits **only** `Ladapter/core/GcmDefaultNonce$2;` to drop for `bbc3f530` versus `0482c9b1`; ten added descriptors are individually traced to the already accepted Java-walls2 and telephony-v2 sources in `jar-additions-review.json`. No package-prefix wildcard or broad drop/reshape allowance is used. Outer separately approved these ten additions.

`registry-delta.json` contains157 exact U12 rebindings plus2 signed N1 rows and old→new mappings. Outer landed those159 rows in master `9165d342aa`; the lane did not write the master registry. Fresh candidate static report and independently bound N1/N2 reports pass. Resident availability, namespace correctness at runtime, first-frame rendering and any lit count remain unproven by these static exceptions.

## Fresh production status

`gates/mac.json` and `gates/vm.json` are the latest actual results, not historical gate receipts. Outer ran the same replay script in its accessible environment at02:17–02:21: Mac Darwin/arm64 and VM Linux/x86_64 each return0 for actual DEX read, production executor, active-registry native gate, read-barrier, T4b and package frozen checks, with zero composed frozen violations. Both executor plans have G1/G2 and static PASS, candidate native tickets bound to `85aef68e/c40faa79`, `device_io=false`, `gates_passed=true`, and `deployable=false`. `production-receipts.json` verifies exact identities and every original command-output SHA, and archives both actual transaction plans and outer replay logs.

Earlier lane-local production attempts returned2 at image G2 (G1 PASS but empty candidate/reference probe); its separate SSH probe returned255 (`Operation not permitted`) and Orb timed out after60seconds with124. Those attempts were not counted as success. The later real outer runs on the **same final SHA**, not a previous bundle, resolve the missing-access evidence; no historical result is borrowed.

Earlier failed attempts are retained: first Mac helper invocation lacked `dexdump` on PATH (fixed by trusted SDK discovery); the second T4b invocation reused an output name and was correctly refused (fixed by fresh timestamped paths). Neither failure is hidden or counted as a pass. No image exemption, tool monkeypatch, borrowed historical PASS, board import, lock or deployment was used.

To obtain real fresh results in an environment with the lab/VM access, execute from Mac:

```bash
bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-final-assembly/replay-production.sh" mac
bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-final-assembly/replay-production.sh" vm
```

The wrapper resolves `LAB_HOME` from the pinned source provenance unless explicitly supplied. The VM path performs only DEX/LLVM/read-only image/native/frozen checks; no build is launched. Output timestamps prevent stitching interrupted runs. Future production failure or unknown results block Stage A; these successful offline results are not window authorization. cx-t0 may open a window only after outer signs the final package and its fresh production results.

## Delivery and validation

Sources, contracts, machine-readable reports, final manifests, composition, approval mapping and normalized raw outputs are enumerated in `landing-paths.txt`. Original unnormalized command outputs and their SHA256 are retained under the persistent lane `.artifacts/raw`; public copies normalize only workspace/home paths. Full transaction-plan JSON is serialized compactly to stay below the1MiB landing limit; no fields are dropped, and original plan bytes/SHA remain in persistent artifacts and the receipt. Tests read landed reports/manifests only, so no private artifact, APK or external worktree is required for the regression selector. `results.json` distinguishes static approval, actual production receipts and pending window authority. Preflight output is retained verbatim; no commit or push is made by this lane.
