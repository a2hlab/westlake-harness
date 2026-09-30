# U7 provisional shard scoring

## Corrected assumptions

An alive process is not a lit app; `child_hilog=0` does not establish missing app logs. All five non-alive 5ea keys still have package/PID-bound retained hilog. Direct review of 22 original t20 images shows **15 own UI, 2 white, 5 launcher**. These are analyst observations, not outer acceptance.

Frozen CSV `fa92c5b964fed2976ba66d82fb703672241435a294c8d9286a7c9192ebab9007` and all **149** pins remain unchanged. Runtime **119** files, boot **36** files and all **22** package/APK/external-sidecar/metadata identities match.

## Evidence and results

[PRELIMINARY.md](PRELIMINARY.md) and [results.json](results.json): first wall **18 hit / 4 unknown**; checkpoint **21 not applicable / 1 unknown**; t20 **22 unknown pending outer signoff**. Analyst-only t20 preview **21 hit / 1 unknown**, never an accepted score. No scored false-positive or missed wall in this shard; unknown walls are not successes.

[SELECTION.json](SELECTION.json) selects only the completed first 5ea run. The remaining 44 keys are unselected, not scored failures. [Prepared evidence](evidence/5ea-prepared.json) pins records, hilog, screenshots, runtime inventories, the available failed prelaunch summary and first clicked attempt. `first_fatal.py` selects raw target-PID termination and its causal root within click-to-t20 bounds. Noise annotates surrounding context only; compact context count/hash does not hide a root. [Analyst reviews](evidence/5ea-review.json) bind each original image and observation SHA; outer signoffs are null.

Raw root: `$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/`. Relative paths/hashes are retained; logs and image binaries are not duplicated here.

| Key | PID | Terminal / root hilog lines | Cause |
|---|---|---|---|
| burgerking | 2922 | 45572 / 45398 | System.exit after libNitroMmkv/libmmkv -> libz failure |
| fd-api | 23369 | 37113 / 37171 | AppCompat theme |
| fd-breezyweather | 25312 | 73120 / 73135 | getClass null |
| fd-client | 32602 | 55892 / 55907 | accountManager null |

`realm-libz` is the frozen family label, not a claim the failing library is Realm. Fennec disappears without a recovered fatal root. White AppManager/app remain unknown first walls; no SceneBoard inference is made. A provisional `none` wall requires own UI, complete bound execution and no observed terminal, not mere silence.

Burger King's INPUT-merged checkpoint stays unknown: matching staged APK and zero sidecars do not satisfy the frozen **installed APK readback** criterion. Retained `bms_batch.py` skips native assembly/readback for empty sidecars (early return near L214, installed base.apk check near L223; staged APK check near L778). No `installed-apk.sha256` receipt exists. This is not a checkpoint failure either. Antennapod is visibly lit but its frozen flaky flag remains.

## Offline replay and formal handoff

```sh
python3 benchmark/2026-10-01-u7-scoring/intake.py > /tmp/u7-prepared.json
cmp /tmp/u7-prepared.json benchmark/2026-10-01-u7-scoring/evidence/5ea-prepared.json
python3 benchmark/2026-10-01-u7-scoring/test_score.py -v
python3 benchmark/2026-10-01-u7-scoring/scoring.py --verify
```

`--formal` rejects this delivery. The current intake intentionally accepts a completed 22-key summary only. Formal work needs audited 5cd 16+6 resume and 61b selection, all 66 unique keys including input-blocked/no-image receipts, independent positive checkpoint evidence and hash-bound outer screenshot decisions. Do not feed partial/resume summaries into this collector or infer positive crossings from UI. Keep this preliminary snapshot intact when adding the formal result.

See `validation.json` and `landing-paths.txt`. No board commands, input mutation, forecast edits or push. Root README/DIGEST handoff is one task line each; exclude other dirty/staged deliveries. Git index denial requires outer scoped commit.
