# libinstalls prediction on the signed U10.1T8 166-key baseline

**Do not count an already-cleared install wall as a new current first-fatal gain.** The signed selection uses 61b for both Seal and Toutiao, where source-built `51e1b525` already accepts their exact reviewed payloads. Aligning the old boards therefore predicts **0 current signed first-fatal keys moved and 0 extra lit keys**. No executable alignment plan or board window is produced by this task.

This is the narrowed step-4 task. Source/provenance, ELF comparisons, loader analysis and the alignment plan belong to the already-reviewed donor `benchmark/2026-10-02-libinstalls-unification/` (cx-bms); none is reimplemented here. All work is offline.

## Actual scope and exact source boundary

`results.json` pins the complete signed baseline and donor `evidence/source.diff` by SHA256. That diff changes selected-ABI ELF validation only for four exact bundle/ABI/name/payload-SHA tuples in **two packages**: three ZIP-data files of `com.junkfood.seal`, and ARM32 `libcvt.so` packaged in the arm64 selection of `com.ss.android.article.news`. CRC, regular-file, UID/GID, mode and default checking remain. The other 164 baseline packages do not match that allow table. No new runtime API or namespace behavior is implied.

The audit reads **172 actual stage-A attempts, covering exactly 166 keys**, across windows 1–5. It retains retries and the original failed Toutiao attempt rather than erasing them with the successful retest. Recovery/smoke runs and other candidates are excluded. Every included run's archived fingerprint pins host `65cc3535` and runtime JAR `5ae3dd29`; its installer receipt pins both libinstalls aliases to the same full SHA. Disk/service receipts are historical observed versions, not a claim of current loader verification. Original reports continue to mark an unobserved libinstalls loader as unknown.

| Observation selection | 5ea / old 2c9a5294 | 5cd / old 2c9a5294 | 61b / new 51e1b525 |
|---|---|---|---|
| All 172 stage-A attempts | 55 accepted, 1 rejected | 60 accepted, 0 rejected | 56 accepted, 0 rejected |
| Audit per-key selection, 166 | 55 accepted, 0 rejected | 55 accepted, 0 rejected | 56 accepted, 0 rejected |

Return code is not install verdict: the failed Toutiao `bm install` returned 0 but printed `code:9568260`. This row remains in `attempts.json`. `selected166.json` chooses each key's latest completed accepted attempt as an explicit audit selection (not an invented outer run-ID selection) and separately preserves the signed outer verdict, raw receipt identities and a scoped runtime termination result. It does not invent new screenshot verdicts. `predictions.csv` contains one row per signed key.

## Direct behavior contrast, with its limits

- **Toutiao**: old 5ea window1 rejects extraction at `installd_operator.cpp:3222`; the same APK `a1112a0c` installs in 61b window5 with a logged reviewed `libcvt.so` exception. Its signed result is alive white, with startup walls 1/2 gone, rather than a libinstalls install failure. This is **one historically blocked key** in these stage-A attempts, not one unresolved current signed key.
- **Seal**: the final signed 61b attempt installs APK `7070a3d4`; its install log records all three exact ZIP-data exceptions and the outer verdict is lit. Earlier U9 failed old-board attempts, already documented by cx-bms, justify Seal as a portability target; there is **no failed Seal install in these U10.1T8 stage-A runs**.
- **Unrelated failure**: `cv2-com-frequent-habits` has record status `app_failed` but terminal install success. It is not a tuple target and is not reclassified as an installation-service wall.

Thus two packages have a known **old-board fresh-install portability benefit** (Seal and Toutiao), only Toutiao shows a rejected attempt in this baseline's raw history, and **neither has a current canonical libinstalls first fatal**. These are three different metrics. There is no predicted extra lighting count.

## Runtime first-fatal comparison

The existing `scripts/lab/first_fatal.py` target-PID/TID logic and `cluster_first_cause.py` are reused on every selected key. For a captured t20, the termination search is cut off at its capture time; later cleanup is not promoted into an app's first fatal. Missing logs, vanished processes without an observed cause and no observed termination remain explicit limitations. `selected166.json` retains the scanner status, target PIDs, raw source hashes, terminal/root event and cutoff; `predictions.csv` carries the compact cause/frame. No absent event is declared proof that an app is healthy.

| Selected board | No observed termination | Java cause | Signal | Disappearance, cause unknown |
|---|---|---|---|---|
| 5ea, 55 keys | 42 | 7 | 3 | 3 |
| 5cd, 55 keys | 46 | 5 | 3 | 1 |
| 61b, 56 keys | 47 | 5 | 2 | 2 |

These counts describe **different shards**, not the same 166 APKs paired under both libraries. They cannot establish an installer-induced runtime difference or statistical equivalence. The demonstrated difference is narrowly the exact extraction exceptions; the current unresolved Java/signal/disappearance walls are outside that behavior change. No additional systematic runtime first-fatal difference can be attributed to libinstalls from these observations.

## Prediction and next action

- Current signed first-fatal keys expected to move: **0**.
- Stage-A historical extraction-failure keys that would be rescued on an old board: **1, Toutiao**.
- Known old-board portability packages including earlier signed evidence: **2, Seal and Toutiao**.
- Predicted extra lit keys: **0**; Toutiao's later white/render wall is not solved by extraction acceptance.
- New alignment window/plan: **none**. The existing cx-bms disabled alignment proposal is a separate installation-chain consistency task and is not activated by this report.

## Reproduce and known answers

```sh
python3 benchmark/2026-10-02-libinstalls-prediction/analyze.py
python3 benchmark/2026-10-02-libinstalls-prediction/test_analysis.py
```

Raw runs stay in the existing worktree directories referenced by SHA in the two evidence tables. Four known-answer tests enforce complete signed166 coverage, a real return-code-0 install failure, identical Toutiao inputs across versions, Seal's three acceptance lines, the unrelated install-success/launch-failure case, and the zero-current/one-historical/two-portability distinction. No native build, board command, lock or deployment occurred.
