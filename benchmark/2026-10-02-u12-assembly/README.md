# U12 partial native composition and disabled Stage-A observation plans

The previous signed package cannot be treated as a ready U12 composition merely by carrying its approval rows forward. This draft changes four effective native paths; every approval must be rebound to the new manifest. Production static admission also refuses a new root library without a deployed comparison. Those refusals are preserved, not bypassed. No device command, lock, native build, exception registration, or approval was performed here.

## Exact current result

| Item | Result |
|---|---|
| Signed base | U10.1T8 bundle `190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736`; native manifest `4db327033870b597248a7188ab7f007e1979dafbb330edc58a4f052b6a086e00` |
| Partial draft bundle | `b249c08b1afa986e2e26e4a38fbd0d8ee543a20fec5d3d90f5aa26ffaaf1c038` |
| Partial native manifest | `6d908fd953defe9ee9f1032573ba4aa1279254cd0aa0ca13c6ff1708944a65a1` |
| N1/N2, both Mac and VM | Raw REJECT: 53 N1 + 103 N2 need exact-manifest admission; zero input errors |
| Non-writing approval preview | All 156 findings match approved base: 53 N1 + 103 N2; genuinely new N1=0, N2=0 |
| G1/G2, both Mac and VM | PASS / PASS, unchanged signed T8 effective BCP and images |
| Frozen, both surfaces | rc=0, zero violations |
| Changed-native static comparisons | ICU and both policy aliases PASS; new root mediandk REJECT: no deployed baseline |
| Actual production executor dry-run | rc=2, device_io=false; stopped at the new-member static gate |
| Plans | 55/55/56 disjoint keys, union166; signed lit keys37/38/41=116; all execution_enabled=false |
| Deployment status | DRAFT_INCOMPLETE, rollout_ready=false; no window was opened |

The persistent draft is `$WORKSPACES/westlake-inputs/generations/u12-native-draft-icu1e206531-media8fc0752d-policy2a6ec73f-v4/bundle/`. Failed preparation directories v1–v3 were preserved. The v1 alias guard caught an accidental attempt to change ZigZag's private mediandk identity; the completed v4 changes only the four explicit target paths. The v3 reference guard required rebasing image-gate reference files to the effective promoted T8 BCP rather than the old underlying U9 view. No binaries were rebuilt.

## Reviewed members and actual final checks

- ICU: `libicu_jni.so=1e206531ad5994b7d3fe332a050d53163a8ab5cf954b9314d748d7ff2ae8ae8f`, reviewed ICU72 deployed-ABI zero-init candidate from `benchmark/2026-10-02-u12-icu-zeroinit/results.json` (`icu72_deployed_era`). Read-only VM input was copied into `$WORKSPACES/westlake-inputs/generations/u12-icu-1e206531.so`, full SHA verified. Only `/system/android/lib64/libicu_jni.so` changes. Actual ELF: 63 exports, zero added/removed; 160 undefined symbols; SONAME unchanged. Export agreement does not establish board behavior.
- Media: `libmediandk.so=8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58`, donor `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-02-u12-mediandk/.artifacts/libmediandk-build1.so`. Add only `/system/android/lib64/libmediandk.so`; preserve ZigZag private `110d02fc…`. Actual ELF: 52 exports, SONAME libmediandk.so, NEEDED libc.so only, no RPATH/RUNPATH, no open sites. The implementation returns typed unsupported codec results, not working codec output.
- Policy: `2a6ec73fd87239ae90ba6464727649f5a4d73aab7588dda392df8803c2e76c4e`, donor `.artifacts/policy/candidate1/libnativeloader-candidate.so`. Replace both Android and route-a aliases together. `policy-source.diff` proves exactly the trusted system table 5→6 and one mediandk root row; libsoundpool is retained. Actual ELF: seven exports, zero added/removed. The loader source is unchanged; candidate header and native scan sidecars are pinned to the reviewed source snapshot.

`artifact-checks.json` records final ELF checks. `exception-classification.json` compares semantic findings with `benchmark/2026-10-02-u10-1-t8-rerun/approved-native-gate.json` using the repository's identical-finding rule; `exception-preview.txt` is the real CLI stdout without `--apply`. N2's 103 findings cover the existing private-domain manifest and are byte-for-byte semantically identical after volatile fields are excluded. This is not a proof of symbol versions or inherited domains; the new mediandk root's actual ELF tags are recorded separately. No registry delta has been applied.

## Pending slots and admission

N11h-r2, runtime `0482c9b1`, removal of android.net from stubs, the paired rebaked 27-image group, combined U12 predictions, final smoke probes, and outer admission remain explicit slots. The late cc-t3 Java delivery is not silently incorporated into this native-only draft. Existing U11i/T8 JARs and images are carriers whose bytes remain unchanged; their passing image gates are not evidence for the future U12 rebake.

The prediction reference is `$WORKSPACES/westlake-harness/benchmark/2026-10-02-u12-prediction-table/u12-predictions.csv` with pending SHA. No gain count is inferred. N11h-r2 also remains pending rather than reusing the already-refuted host candidate.

A final composition must rerun the production gates and bind approvals to its final SHA. The new-native static refusal needs an explicit reviewed admission mechanism; this draft does not weaken the checker or use an old private ZigZag file as a fictitious deployed root baseline. A classified identical finding is not a currently registered PASS.

## Disabled Stage-A plan semantics

`plan-5ea.json`, `plan-5cd.json`, and `plan-61b.json` assign every signed key exactly once, using the audited board ownership in the prior 166-key baseline. Lit original/CV2 shards precede unlit shards. The runner must use master bms_batch, reinstall, hilog20, shots5,20, focus-check, detached sessions, and a fresh output directory. Windows are45min with35min new-key cutoff; unmeasured keys remain unknown and may continue only with the same final SHA after outer review.

The regression criterion is **zero confirmed regressions among the 116 outer-signed U10.1T8 bright keys**, with `knowledge/gates/flaky-keys.json` SHA pinned. Flaky attribution needs at least3 same-board trials per side and screenshot numerator/denominator. A single white sample does not stop a board as a confirmed regression. A single ZigZag smoke crash preserves evidence and finishes the baseline; any retry is a fresh authorized window. Process alive or READY is insufficient lighting evidence.

`recovery-u101t8.json` is copied from the signed pre-U12 `expected-run.json`: **318 assertions /316 unique paths** for each board. Unconditional finish restores the exact journal-owned native/boot/JAR layers, uses automatic receipt-owned cold_stop for residual Android children, verifies318 with diff/absent empty, runs HW/ZZ recovery smoke and t20 screenshots, and checks final identities/fingerprints before releasing the lock. Failed finish retains the lock. It restores U10.1T8, never U9; no installation service is swapped.

| Board | Signed restore runtime123 | Native-only draft runtime124 preview | Restore and draft BOOT36 |
|---|---|---|---|
| 5ea | f3b604c94df4 | c29c4b415fe5 | e3806b65a079 |
| 5cd | f3b604c94df4 | c29c4b415fe5 | e3806b65a079 |
| 61b | d6848fa2c989 | 58090b2982a7 | e3806b65a079 |

The six installation-chain aliases are included when computing these per-board fingerprints. The preview has319 assertions /317 paths because of the root addition; final U12 identities must be recomputed after filling the pending layers. These are offline calculated previews, not board readbacks.

The pending `offline_precheck.result` also makes the current production board_run refuse before LOCK (it does not enforce execution_enabled by itself). `draft_guard.py` rejects both hook slots before any device import, including attempts to flip execution_enabled alone. They are deliberate design placeholders, not a production apply/finish implementation. Final reviewed transactional hooks, live smoke specification and pre-lock dispatcher binding must replace those slots. This prevents an incomplete draft from being accidentally run by board_run.

## Real offline execution and validation

`offline_gates.py` exercised Mac and VM production PATH with actual dexdump against classes.dex and real LLVM/readelf commands. VM used the shared `.vm-tools` and writable `.vm-tmp`, with LAB_HOME explicitly set for oatdump_remote. The first VM image check had an unset LAB_HOME and correctly failed G2; the complete retry passed G1/G2. Native and static refusal results are unchanged. `gates/{mac,vm}/` preserves both reports and actual executor rc2 output; raw unsanitized originals and their hashes are held outside the public repository as recorded in `raw-evidence.json`.

```sh
source "$WORKSPACES/westlake-inputs/env-mac.sh"
export PATH="$HOME/Library/Android/sdk/build-tools/37.0.0:$PATH"
python3 benchmark/2026-10-02-u12-assembly/offline_gates.py --surface mac
python3 scripts/lab/auto_approve_exceptions.py \
  --candidate benchmark/2026-10-02-u12-assembly/gates/mac/native-gate.json \
  --baseline benchmark/2026-10-02-u10-1-t8-rerun/approved-native-gate.json
python3 benchmark/2026-10-02-u12-assembly/test_assembly.py
agent-spec lifecycle specs/u12-assembly/t1-draft.spec.md --code tools/spec-checks --layers lint,test
```

The equivalent VM run prepends the same shared production tools and scratch before invoking `offline_gates.py --surface vm`. No HDC/device preflight is run in this offline task; orb/HDC/bind readiness and a fresh real-VM full production PASS are mandatory in the future dispatcher before LOCK.

The two known-answer tests cover exact member hashes, both policy aliases, unchanged private media, both real gate reports, approval classification,166 disjoint keys,116 protected lit verdicts, per-board installation-chain fingerprint differences,318 restoration, and negative draft-enabling attempts. Contract scenarios assert honest draft completion and refused deployment, not candidate board success.
