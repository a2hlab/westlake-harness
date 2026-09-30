# Unified r17r feedback (offline; cross-profile)

Previous error: a late uninitialized-object exception can hide an earlier failed Application/provider bind. New rule: retain the first PID-attributed startup failure **and** the first explicit terminal marker. A caught bind exception does not prove process death. Tolerated errors in signed-lit apps never become blocking labels.

## Evidence and scope

- 66 keys; outer screenshot signature remains **21 lit**, from `lit_t20_by_screenshot`. No screenshot was re-adjudicated. The 23 cumulative signed apps are not this run’s denominator.
- Recounted from each `record.json.captured` and UID/name-matched process tables: **126 captures; 28 alive t5; 27 alive t20**. Three prelaunch keys have unknown process samples, not measured deaths: fd-seal, toutiao, subwaysurfers.
- Actual fingerprint **0aa9f6ecf29e**, v3c 668e4f7c / runtime 9e14bf20 / r17r dd4f0eae / installer 6aadb8b4 + 7048c7c5. The readback matches both frozen native projections except **JAR and libhwui** (be59260f instead of a578b949); board is 5cd instead of 5ea. Package name is outer attestation; file hashes are run-local measurements.
- All **104 v3 frozen files verified**, receipt SHA-256 `f9d4881a121b8bd36603835604e42bca7ab3c59a68f1735c04721ac82ebd143b`. **Zero same-profile scored samples.** Both frozen columns are descriptive comparisons; neither is selected as the r17r forecast.
- 63 clicked-after-freeze, APK-matched records pass descriptive gates. Three prelaunch records remain in the 66-row table, excluded from launch metrics. Input splits/dynamic code and profile changes between producer snapshots remain outside static proof.

## Lighting comparison

| Frozen column | Predicted lit | Actual-lit hits | False lit alerts | Actual lit not predicted lit | Precision | Recall | Strict binary correct |
|---|---:|---:|---:|---:|---:|---:|---:|
| r17o | 15 | 15 | 0 | 6 | 100.0% | 71.4% | 47/50 |
| r17p | 19 | 16 | 3 | 5 | 84.2% | 76.2% | 42/47 |

The strict binary projection compares only 亮 / 不变 against lit / not-lit; 推进 and unknown abstain. It is **not** four-class prediction accuracy. All-not-lit baselines on the same strict subsets are 32/50 and 29/47. A missed lit alert from 推进 is not a false promise of darkness. All-66 retrieval counts and per-key original labels are retained in `results.json` / `per-key.csv`.

## First walls and misses

First startup-failure family coverage is **23/33 hits, 10 misses**. Nine other unlit clicked apps have no diagnosed mechanism (six no explicit startup fatal, three generic getClass NPEs); their trace text remains visible and is not invented into a service root cause. This is family-level coverage: Flutter/GLES versus Flutter/libandroid can match a loader family while the exact library differs.
The separate first-terminal comparison is **21/26 family hits, 5 misses**. `actual_terminal_cause` preserves the later fatal after a caught bind failure; it is not substituted for the earlier failure. A first failure is observed sequencing evidence, not proof that correcting it alone lights the app.

| Unpredicted first startup family | Keys | Trace evidence |
|---|---|---|
| activity-theme-contract | vlc | [vlc](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/vlc/hilog.txt:48643) |
| app-native-namespace-dependency | fd-client | [fd-client](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/fd-client/hilog.txt:48831) |
| asset-font-fd-stub | fd-uhabits | [fd-uhabits](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/fd-uhabits/hilog.txt:37865) |
| dex-verifier-access | fd-immich | [fd-immich](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/fd-immich/hilog.txt:34575) |
| disk-cache-size-contract | fd-libretube | [fd-libretube](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/fd-libretube/hilog.txt:44769) |
| framework-audio-native-closure | opencamera, fd-plus | [opencamera](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/opencamera/hilog.txt:31019); [fd-plus](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/fd-plus/hilog.txt:38403) |
| haptics-capability-null-array | fd-reader | [fd-reader](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/fd-reader/hilog.txt:58727) |
| media-session-service-resolution | fd-musicplayer | [fd-musicplayer](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/fd-musicplayer/hilog.txt:23000) |
| sentry-provider-configuration | fd-im-vector-app | [fd-im-vector-app](/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-unified-r17r-5cd-sweep/runs/unified-r17r-5cd/5cd1e3dd00000000000000000923012c/fd-im-vector-app/hilog.txt:37819) |

**One new family has at least two missed keys:** framework audio native closure (OsmAnd + OpenCamera). It deliberately retains two independent submechanisms: SoundPool’s declared library and AudioProductStrategy JNI registration. No common repair is inferred. Namespace dependencies (11 apps, one miss) and activity-theme contracts (two apps, one miss) are partially covered existing families; all remaining new mechanisms have one observed app and remain in the backlog.

`rules_unified_r17r.py` adds exact framework API requirements and a method-inspector hook. `scan_unified_audio.py` scans external method references in every available exact-SHA base APK: **65 verified, one unknown; 25 conditional alerts; 2/2 observed audio first walls covered, 0 missed**. The other 23 references are latent/unconfirmed, not proven false positives. No startup reachability or missing implementation is claimed from a method ID. APK-local lookalikes and unrelated AudioAttributes.setUsage calls do not match. Static rows are generated without logs or outcome input; comparison occurs afterwards.

Both Noice keys and Wikipedia have first explicit native fatal `EGL_NO_SURFACE` in this exact run. Neither Noice key is relabeled audio based on another run. Their static audio references remain latent.

Installer scan: 34 static requirements across 66 keys; 32 launched requirements have permission read back as granted and are marked **permission-requirement-satisfied**. The other two requirements were prelaunch inputs; one further key has unknown input. All 63 launched apps have grant state 0. This is a permission-state check, not a claim that every subsequent ability launch succeeded.

## Run

From `benchmark/2026-09-29-static-wall-prediction`:

```sh
python3 extract_unified_failures.py
python3 scan_unified_audio.py
python3 score_unified_r17r.py
python3 -m unittest test_unified_r17r test_installer_background
```

13 tests pass (eight new, five existing). Known answers: OsmAnd SoundPool and OpenCamera legacy-stream-type path detected; an APK-defined lookalike and unrelated audio setter are not. PID attribution ignores another app’s fatal and tolerated EARLY-TF logs; bind and terminal markers remain distinct. None of these checks contacts a board.

Outputs: `per-key.csv/json` (all 66 predictions/outcomes/causes/gates), `first-failures.json` (source SHA + original hilog line numbers and both chains), `missed-walls.json`, `audio-static.json` (DEX SHA + method-ID offsets), `background-static.json`, `record-facts.json`, and `results.json`. `SHA256SUMS` pins report and code; `source-code-inputs.json` pins reused scanner/audit dependencies. Frozen predictions and outer evidence are read-only. R2: offline calibration only; no claim of newly verified UI or prospective gain.
