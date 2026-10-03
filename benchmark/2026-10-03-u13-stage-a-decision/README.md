# U13 stage A: outer decision — 122/122 lit, 0 process-selftest failures, stage B authorised

**Verdict.** Over four observation windows (2026-10-03 03:07–08:37, three boards), every one of the 122
U13-reference-lit keys was measured lit (24 + 33 + 49 + 16 distinct keys), 0 confirmed regressions. The
process crypto self-test, the gate that U12 failed (154/174 runs), has **0 selftest_error / 0 badtag /
0 probe_error in all 219 U13 runner records**, also when every hilog is rescanned for failure lines from *any*
pid. `promotion_hook_u13.retention_reason` returns `None` for 5ea, 5cd and 61b. Stage B (promotion) is authorised
to cx-t0 under the conditions in `outer-stage-a-*.json` → `stage_B`.

| | value |
|---|---|
| reference-lit keys measured / lit | 122 / 122 (window1 24, window2 33, window3 49, window4 16) |
| lottery k/n | fd-fitness 6/7 (window1 died before t5, window2 6/6), wikipedia 6/6 |
| gains over the reference | fd-noice 6/6, fd-uhabits 6/6, noice 1/1 (61b), moodcairns 1/1 (61b) |
| U13 runner records (shards + activation smokes) | 219: 180 PASS, 39 unknown, 0 REJECT |
| failure-class probe lines, any pid | 0 |
| outer explanations | 41 (record, pid) rows, one per hook issue |
| report SHA (bound in both decisions) | `0488fa09e049e9729889da429e65d3ad6275ffd89206a7924105b298923b419b` |
| bundles | common 91272eaf (5ea, 5cd), 61b 8861a11a; native manifest 85aef68e |

## What a naive aggregate gets wrong

`process_selftest.py <run tree>` over the executor's whole stage-A tree reports 649 records, 30 REJECT,
439 unknown, `passed: false`. Almost none of that is U13:

- **28 REJECT = recovery smokes.** After every window the board is rolled back to U10.1T8 and helloworld /
  zigzag are run; U10.1T8 carries the old process-wide AEAD defect, so *helloworld itself* logs
  `selftest AEADBadTagException`. These records are U10.1T8, not U13 (73 recovery records in total).
- **2 REJECT = known-answer fixtures** (`evidence/known-answer/`: U12 selftest_error, U10.1T8 badtag).
- **223 window evidence copies** of runner records (same run ids, no hilog → "incomplete" unknowns),
  **51 contact-index symlinks** to records already counted, **81 executor state records**
  (apply/baseline/rollback/final; no app run).

The decision binds exactly `window*/u13-A*/<board>/runner/**/record.json` (219) — `build_decision.py`
refuses any non-runner record it cannot put in one of those classes.

## The 39 unknowns (41 hook issues), each from the record's own files

The probe fires right after `[B43-BIND] handleBindApplication returned OK` (seen in every PASS run), so
"silent" has a checkable meaning: the process never finished bind, or nothing ran.

| class | rows | evidence |
|---|---|---|
| activation-smoke icon-locator step | 13 | `smoke/probe/record.json`: no key, no BMS uid, no hilog by design — not an app run |
| launcher miss (`status: app_failed`) | 3 | desktop icon not found, app never launched (frequent-habits ×2 — lit only via `aa start`; minesweeper window3, re-run lit + PASS in window4) |
| bound, `validateAead=OK`, then gone | 14 | the OK line is in the hilog (line number in the row); the pid is absent by number from every `processes-t*.txt` |
| never finished bind | 7 | `ensureBindApplication FAILED` + first `Caused by:` (immich, mcdonalds ×2 androidx.startup; libretube createApplication; fd-plus `android.bluetooth.le.ScanCallback`; im-vector Realm dlopen_ns) or died before bind (fennec) |
| pid at capture | 4 | x 9779 / organicmaps 24291 spawned < 2 s before the hilog dump, still pre-bind; organicmaps 24377 / 24407 in `processes-t20` with 0 hilog lines (spawned after the dump) |

Independently of `process_selftest`'s pid filter (it only reads pids found in the process tables), every
U13 hilog was scanned for failure-class `[WL-KS-PROBE]` lines from any pid: 0. A process that hit badtag and
died before t5 would have been invisible to the tool; there is none.

## Rules this sets

1. **Aggregate only the candidate's own runner records.** Recovery smokes run on the restoration baseline;
   counting them would veto U13 for the U10.1T8 defect it fixes. List every exclusion by class.
2. **Normalise before binding a report SHA.** `process_selftest.run_row` builds `processes` from a `set`
   of pids; its order follows Python's per-process hash seed, so the same records gave different bytes on
   two runs. The builder orders processes by pid; `--check-only` reproduced the SHA in three fresh processes.
3. **Rescan for failures from any pid** when a tool filters by pid.

## Files

- `build_decision.py` — rebuilds the aggregate, explanations and decisions; `--check-only` compares; runs the hook for all three boards.
- `selftest-u13-stage-a.json` — schema-2 aggregate (219 runs).
- `selftest-explanations-{common,61b}.json` — 41 rows each, bound to bundle / manifest / report SHA.
- `outer-stage-a-{common,61b}.json` — signed decisions, `promotion_authorized: true`, stage-B conditions.
- `test_decision.py` — both bundles pass; wrong bundle, one dropped explanation, changed report bytes, one
  injected badtag and 121/122 measured each reject.
