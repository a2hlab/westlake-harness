# v3 paired prospective forecast: r17o / r17p

The v2 forecast overestimated what clearing an early wall would achieve: exact 30/45 (66.7%) was below the always-unchanged baseline 32/45 (71.1%). This forecast uses the accepted B10 feedback, distinguishes conditional references from executed startup paths, and leaves EGL as **runtime-only**. A wrapper source change is a hypothesis about future frames, not static proof of lighting.

**Final freeze: 2026-09-30 05:22:23.255216 +08:00.** No upcoming full-sweep outcomes or r17p validation outcomes were read. Fourteen prior r17o targeted cases were already disclosed on the board; those keys carry a separate exposure stratum. Prior r17o checks were already on-board, so this is a forecast before the *next full sweep*, not a claim of being before the first r17o trial.

| Variant | Own UI (亮) | Named progress (推进) | Same named wall (不变) | Unknown |
|---|---:|---:|---:|---:|
| r17o | 15 | 5 | 37 | 9 |
| r17p | 19 | 8 | 30 | 9 |

The table is for these 66 keys, not the campaign's cumulative lighting total. `freezes/v3/predictions.csv` has the requested two JAR columns; each row includes its reference wall, positive checkpoint, reason, B10 classification and prior evidence. `freezes/v3/variants/{r17o,r17p}/` contains the corresponding flat scoring inputs. Old v2 freezes/backtests and the B10 feedback matrix are unchanged.

## Exact profiles

Both columns are limited to **5ea34a4500000000000000001123012c**:

- Package: `668e4f7c74bfe635c57ca7133e1373acb0c675959d5953a20708e70293d27107`.
- libhwui override: `a578b94933cfac4a8fa79116abf145435248df7bce315b9c8eedf41eccb793c6`.
- libbms: `6aadb8b4ca9ad7d1dbaf6d99ca70f4603e3e7a2ec152fb60aee49137751afbf9`.
- libapk_installer: `7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18`.
- r17o: `cd06eecf816a97cb344c8c57f5eb70be1431775fd832cbc0f8d46c92f74f021d`.
- r17p: `a0ed5c4fedd952762256a24ab7801deb3ad6e696a0204853ce5000316336d173`.

`evidence/build-result-*.json` matches the local JAR bytes. Their only listed Java source difference is WindowSessionProxy (`evidence/jar-source-delta.json`). Matching r17o committed text and r17p source snapshots are included; the baseline package receipt is pinned too. Next2/next3, later AudioSystem/ANL/native replacements or a different JAR are outside these profiles.

The B7 source rewrites the boot provider array before bind (`evidence/B7BindFixes.java:30`, implementation at line 333); this addresses the *lookup* problem rather than assuming an app-JAR definition becomes boot-visible. The r17p wrapper replaces the IWindow argument while preserving its binder, drops delegate `resized` callbacks and keeps its separate degenerate-layout recovery (`evidence/WindowSessionProxy.java:90`, 226, 261). Required callback suppression, window ownership and first-frame presentation remain runtime risks.

## Interpretation

- r17o Droidify/Calendar/Tasks UI predictions reuse disclosed small-batch evidence. Calendar/Tasks come from another board; transfer to this exact 5ea profile is still a prediction.
- The r17p AppManager, two Noice keys and K9 UI predictions are **low-confidence visual hypotheses**. Wikipedia/NewPipe/AntennaPod predict only the named surface checkpoint; a provider fix or an EGL pointer alone does not establish own content.
- K9 has conflicting earlier observations (r17j database page, r17o blank), so r17o abstains. Its installer-selected database Activity is not evidence of a permission-caused secondary launch.
- Files supplied in an app namespace, unresolved callbacks and tolerated provider failures do not become successful execution by inference. Untargeted JNI/native/service walls remain or stay unknown. Seal/Toutiao prelaunch rejection and Subway identity failure are reported separately from post-click accuracy.
- `不变` means the row's *frozen named reference wall*, which can be from accepted v2 or the disclosed r17o targeted baseline. It does not mean merely “not lit”. A later distinct wall without positive progress evidence remains unknown.

## Verification and future backtest

```sh
python3 benchmark/2026-09-30-r17op-prospective/test_forecast.py
agent-spec lifecycle specs/bms-background-start/t3-r17op.spec.md --code tools/spec-checks
```

Four Python tests and both contract scenarios pass. The tests check all 66 CSV/JSON rows, prior hashes, each variant projection, the hwui override, wrong JAR/APK/profile and early-click rejection, abstentions, and survival not implying UI. The completeness check rejected an unpublished 05:21:10 seal because three prelaunch keys lacked PID-log artifacts. That draft is retained under `rejected/`; the final freeze adds their already-accepted record/continuation evidence without changing prediction CSV values. Only `freezes/v3/` is authoritative.

After a completed run, supply per-key screenshot/log adjudications using the frozen `prior_wall` and `progress_checkpoint` strings, then run:

```sh
python3 benchmark/2026-09-30-r17op-prospective/score.py \
  --variant r17o \
  --run /ABSOLUTE/COMPLETED/RUN/5ea34a4500000000000000001123012c \
  --installer-readback /ABSOLUTE/installer-readback.txt \
  --observations /ABSOLUTE/adjudications.json \
  --out /ABSOLUTE/new-backtest.json
```

Use `--variant r17p` only for the matching actual JAR. Multiple `--run` arguments support continuation segments; every adjudication then names `source_run`. Select the first completed attempt and retain duplicate/control records separately. Each observation supplies `key`, `lit` plus its verified `screenshot_evidence`, `advance` plus `progress_evidence`/exact checkpoint, and `same_wall` plus `wall_evidence`/exact reference wall. Unknown evidence stays unknown. Identity, permissions, captures and process counts are taken from the run records, not those supplied outcome labels.

The scorer reuses the audited v2 gates: facts first-line fingerprint must match runtime-fingerprint.txt, including actual JAR and hwui hashes; installer shell/foundation readback and boot must match; original APK, launcher, grant and sidecar facts are checked per record; `clicked_at` must be strictly after the final freeze. Run-start projection is not proof of every resident mapping; sampled per-app disagreements are exclusions. Extra native replacements fail the expected projection. Scoring code itself is hash-pinned.

Report exact four-class and minimum-promise scores, confusion, abstention/coverage and the always-unchanged baseline on the same denominator, by actual JAR and exposure. **Never select the better-scoring column after seeing outcomes.** Missing or unrun columns remain pending. Future lighting requires image adjudication; no future runtime/lighting result is claimed here.

CSV SHA-256: `7c51cf1b271681c44f9f54047d0c5572f4fb27df15857e03079c3b38d9fcffd5`.

Final receipt SHA-256: `f9d4881a121b8bd36603835604e42bca7ab3c59a68f1735c04721ac82ebd143b`.

R2: verified offline identities, frozen artifacts and scoring tests; partially source-informed forecast; unverified next-sweep runtime outcomes. No board I/O or git metadata writes. Outer loop commits the handoff.
