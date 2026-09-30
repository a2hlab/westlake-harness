# U6 scoring and termination-first triage

## Completed measured scoring

See [SCORING.md](SCORING.md) and `SCORING.json`: first wall **39 hit / 5 false positive / 22 unknown**; checkpoints **5 hit / 14 unknown / 47 not applicable**; t20 **46 hit / 1 false positive / 19 unknown**. Six changed-sidecar keys remain unknown on all axes under the outer-confirmed strict freeze. Screenshots use outer ACK95 04:36:43, not an inferred alive/UI label.

The actual four-shard layout has no `index-*.json`; use the read-only adapter:

```sh
python3 benchmark/2026-10-01-u6-scoring/measured.py "$U6_ROOT" \
  --review benchmark/2026-10-01-u6-scoring/REVIEW.json > /tmp/u6-rescore.json
python3 benchmark/2026-10-01-u6-scoring/test_measured.py
```

`measured.py` binds 22/22/16/6 completed summary records to their exact `record.json`, rejects duplicates/extras, and reuses the strict scorer. `review_u6.py` materializes manually reviewed, line-pinned decisions; it is not an automatic causal classifier. `SCORING-VALIDATION.json` is the measured-phase validation receipt. `results.json` and `validation.json` retain the earlier preparation checkpoint and its historical hashes.

## What was wrong

The 17-entry noise registry omitted the optional B8 HTML compatibility loader probe **during manual selection**. Mining did not lose its PID and it did not miss the threshold: **24 distinct lit packages, 28 occurrences**, including Aegis PID30814/TID30837 at hilog L19751 and Anki PID11263/TID11286 at L25999. The live registry now has **18** entries. `evidence/benign-v1.json` preserves the previous registry bytes, matching the historical INVESTIGATE cohort pin; its old replay is not rewritten. AdapterIIM was already entry 002.

An independent error was treating the first exception after noise subtraction as the first fatal cause. Earlier Datadog/AppLovin/provider exceptions can be caught. **First find termination in the target PID, then trace its cause.** Noise only trims context; it never selects a termination or deletes a terminal/causal chain.

## Known answers, checked against raw runs

| Run | Termination | Linked cause |
|---|---|---|
| N5 LocalSend | signal 11, L39057, PID16312/TID16353 | fault-thread frame L39695 `ANativeWindow_getFormat+60` |
| J6 reader | main_threw L57611, PID3015/TID3038 | monitor-enter NPE; first frame L57613 `getVibratorIds` |
| T7c Wikipedia | System.exit L80745, PID16250/TID16275 | tagsoup Parser/XMLReader ICCE; not earlier SSLSockets or the suppressed coroutine diagnostic |
| merged BurgerKing | System.exit L57393, PID4702/TID4728 | L57324 libNitroMmkv → libmmkv → missing libz.so; not earlier Datadog |
| merged McDonalds | main_threw L57551, PID2233/TID2277 | SplashActivity and L57566 DataSourceModuleProvider null; signo42 L36581 is not terminal |

`evidence/first-fatal/*.json` contains original line numbers, raw excerpts, source record/log hashes, PID bindings and independently specified expected answers. `collect_fatal_fixtures.py` recreates excerpts from `WORKSPACES` without modifying source runs. LocalSend has no captured standalone cppcrash: its fallback is the **DfxFaultLogger report embedded in hilog**, explicitly bound by report PID, fault TID and timestamp. Reporter PID16378 is not an app PID; only its bound crash report is used, never arbitrary foreign-process rendering logs.

## Terminal-first CLI

```sh
python3 scripts/lab/first_fatal.py "$KEY_RUN_DIR"
```

- Reads record/UID-matched t5/t20 process snapshots and package launch bindings. Does not execute device commands.
- Detects main_threw, FATAL EXCEPTION, invoked uncaught handler, System.exit and known fatal signals. Signals **42/35/4 are never terminal**. A stack reference to `System.exit` is not a call event. Class-linker dumps are excluded.
- Java: follow the emitted `Caused by` chain, or the same PID/TID immediately preceding exception block within two seconds. An intervening ordinary operation breaks adjacency. Suppressed exception branches are not the primary cause. W-ROOM-SURVIVE uncaught notices alone are not terminal: its background handler can survive; actual System.exit remains decisive.
- Native: prefer PID/TID/time-bound `faultlogs` crash frames, falling back to a bound DfxFaultLogger report. Missing or ambiguous stacks stay unknown. This identifies a crash site, not the origin of memory corruption.
- t5-present or package-launch-bound PID absent from the valid t20 snapshot is separately reported as process disappearance with unknown cause; this also covers death before t5. Post-cleanup absence is not used. This fallback has snapshot/binding references, not an invented terminal hilog line.
- The explicit CLI invocation authorizes baseline noise for **context trimming only**, including other generations. Its cause and termination are computed from raw evidence before trimming. The U6 scoring adapter separately restricts projected baseline noise to exact frozen runtime/boot inventories.

## U5 structure rehearsal (not U6 measurements)

```sh
python3 benchmark/2026-10-01-u6-scoring/score.py \
  --source "$WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-10-01-u5-sweep" \
  --mode rehearsal > /tmp/u6-rehearsal.json
```

All **66** indexed keys are read; three have no timed launch/log/t20. The rehearsal deliberately reports all 66 as U6 candidate mismatches, and seven as changed U6 input identities. Empty-sidecar `native_assembly.status=not_needed` is valid; a null installation receipt is not. See `results.json` for actual run counts and hashes. No U6 accuracy or lighting claim is made from this rehearsal.

## Actual scoring after complete U6 and outer screenshot signoff

The immutable reference remains `../2026-10-01-u6-prospective/PREDICTIONS.csv`, SHA256 **b9a414ed0b70134e2b9dbd54be91dd843e130c5d3020acf905577e17ef419746**. All 25 freeze pins are checked. No U7 file changes are required.

```sh
python3 benchmark/2026-10-01-u6-scoring/score.py --source "$U6_ROOT" --mode u6 > /tmp/u6-prepared.json
python3 benchmark/2026-10-01-u6-scoring/score.py --source "$U6_ROOT" --mode u6 --template > /tmp/u6-review.json
```

The source adapter expects `index-*.json` with `serial`, `boot_id`, and `selected[{key,record,record_sha256}]`; selected records live under `runs/<run>/<serial>/<key>/record.json`. It discovers every timed attempt there and refuses selecting a retry. Missing/duplicate keys, changed log/record/image hashes, or malformed fingerprints reject. Runtime and boot inventories must match all **119+36** frozen files; APK plus sidecars and their installation receipt are checked per key. Input changes remain non-comparable, never silently rewritten in the freeze.

Complete the review template using the prepared raw terminal/causal evidence and **outer-reviewed t20 images**:

- Top-level `complete=true`, `outer_signoff` names the actual signed board entry; `prepared_sha256` must remain exact. It is an auditable reviewer reference, not cryptographic authentication.
- Per key `first_wall`: `{id, lines, rationale}`, or null. A fatal-wall claim must cite the selected termination line, not merely an earlier exception. `none` needs positive execution evidence and cannot coexist with an observed terminal. Unresolved/nonfatal startup stalls stay unknown unless separately reviewed with evidence.
- `checkpoints`: `[{fix_id, outcome: "crossed" | "old-wall-reproduced", lines, rationale}]`. Use actual execution, never missing-error inference. IDs must occur in that frozen row.
- `t20`: `{sha256, visual: "own-ui" | "not-own-ui" | "white" | "black" | "desktop" | "crash", description}`, or null. Never infer UI from process survival or first-frame callbacks. `not-own-ui` preserves an outer negative label without inventing a finer visual category.
- Missing PID/log/capture timing prevents causal scoring; input/candidate/installation mismatch makes all axes unknown. Prelaunch input rejections without a timed first attempt currently remain unknown, explicitly rather than inventing a PID-backed causal score.

```sh
python3 benchmark/2026-10-01-u6-scoring/score.py --source "$U6_ROOT" --mode u6 --review /tmp/u6-review.json > /tmp/u6-SCORING.json
```

The command **re-reads original evidence** before scoring, rejects unsigned/stale reviews and any rehearsal-as-U6 attempt, and delegates to unchanged frozen `forecast.score_reviewed`. **First wall / checkpoints / t20 have separate counts**. Conflicting checkpoint evidence and single-attempt flaky t20 stay unknown. A shifted first wall does not prove every checkpoint or own UI. Native termination/root evidence is a review aid; the script does not automatically map causal text to frozen wall IDs.

## Validation and landing

Run `test_score.py`, `test_first_fatal.py`, `test_measured.py`, the old INVESTIGATE tests and Rust `--test u6_scoring`; current measured receipts and both master-overlay gate exit codes are in `SCORING-VALIDATION.json`. `validation.json` retains the historical prep checkpoint. `landing-paths.txt` lists only this delivery. Root README/DIGEST changes are one-line extractions, not whole-file copies from the dirty lane. The full source-run replay independently verifies the recorded identities before applying the signed observations.
