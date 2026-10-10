# CANTOPEN impact inventory — 128 demo packages

## Evidence first

**Counting exception mentions or screenshot `suspect` classifications as first-fatal blockers was too broad.** The selected 5cd records contain CANTOPEN for **37/89** measured keys, including **25/26** screenshot-triage suspects. A stricter PID/TID-bound termination analysis identifies **18 measured keys** whose first observed fatal is CANTOPEN. The other **19 exception-positive keys** are not promoted to this confirmed first-fatal group: their logs show a different first terminal, no observed terminal, or disappearance without a linked cause.

All **128 APKs / 200 DEX members** were actually scanned with the existing Mac SDK `dexdump -d -n`, against the manifest APK SHA. Among the **39 unmeasured** keys, **23** reference Room, SQLiteOpenHelper or openOrCreateDatabase instructions. These are **conditional static first-fatal candidates**, not 23 proven startup deaths. The remaining **16** have no such managed call reference and remain unknown (native/dynamic database use is outside this scan).

**Summary row: measured first-fatal CANTOPEN = 18; unmeasured conditional prediction = 23; combined conditional candidate bound = 41; unmeasured startup deaths proved = 0.** See `../summary.csv` for the one-row machine-readable summary. This is not a UI verdict or a count of apps guaranteed to unlock.

## Deliverables and sources

- `../impact.csv`: 128 package rows, exactly the requested seven columns.
- `../summary.json`: measured and forecast counts and explicit key lists, including the 19 exception-positive non-confirmed keys.
- `../impact-evidence.json`: per-key APK/record/hilog SHA, verified target PIDs, exact exception source lines, first-fatal chain and static call-site samples. JSON event `message` is retained without duplicating the full formatted `text` field; the original hilog is pinned.
- `../evidence/collect-static-initial.txt`: original full static execution output. `../evidence/collect.txt`: fresh termination reclassification using that unchanged tool/APK-bound static cache. No historical PASS is substituted for a missing scan.
- `../evidence/dexdump-completeness.{json,txt}`: independent header class_defs_size versus retained stdout class-descriptor count and SHA checks for all 200 members.
- `../evidence/impact-tests.txt`: known answers for main-thread kill confirmation, background nonfatal errors, different PID exclusion, earlier other terminal, standard main_threw and separated static forecasts.

Measured input: `$WORKSPACES/westlake-harness-tools-inventory/benchmark/2026-10-10-5cd-demo-regression/resume-organicmaps/compare-observed-89/comparison.json`. Record paths are resolved against that source worktree and through observed-89 aliases to the actual completed-full-round/continuation records, not by a fresh recursive glob. Package, key, serial, APK SHA and finished_at are checked. The manifest is `$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/demo-manifest.json`, with install=false aliases excluded (128 installed packages).

The complete dexdump stdout is retained as gzip, stderr verbatim, under `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-10-el2-cantopen/.artifacts/dexdump/`. Large raw outputs and the intermediate full evidence are not listed for Git landing. Every member's exit and uncompressed stdout SHA are in the small evidence file. Six examples per static family are retained, with total call/definition counters; bundled class definitions alone do not count as a call reference.

Fresh audit output: `apks=128 dex_members=200 class_defs_header=779346 class_defs_stdout=779346 complete=true`, exit0. These class counts are summed across APKs, not unique shared classes. Known answers: `Ran 8 tests in 0.008s / OK`. The membership check, compilation and all collection/audit steps exit0. User-paths: 18 files, 0 violations. Landing preflight: 18 files, 0 too large, 0 user-path hits, 0 data home paths (`../evidence/checks-impact.txt`, `user-paths-impact.txt`, `preflight-impact.txt`).

## Counting rules

1. Reuse the existing `scripts/lab/first_fatal.py` to load recorded package launch bindings/process snapshots, verify diagnostic hilog hashes where pinned, and analyze the earliest observed terminal. Restrict counts to these app PIDs and execution lines; class-linker registration dumps and another app's log are excluded.
2. `cantopen_count_5cd` counts execution-line mentions of `SQLiteCantOpenDatabaseException`, including repeated logs and Caused-by lines, **not** unique database-open attempts. Evidence separately counts paths under this package's `/data/app/el2/100/base/<pkg>/` (including databases and no_backup).
3. The existing detector deliberately excludes W-ROOM-SURVIVE. This report adds only its explicit `UNCAUGHT ... main=true` **plus** a same-PID/TID kill-preservation marker within three seconds. Background kept-alive notices and an unconfirmed UNCAUGHT marker do not suffice.
4. Choose the first terminal, not the last exception. A causal chain stops at another independent terminal/UNCAUGHT block, even within the existing detector's two-second context window. Require CANTOPEN in this bounded chain plus a verified own-package el2 path in the app log.
5. `suspect_5cd` is the comparator's semantic.class=suspect, not an outer screenshot verdict. Semantic same_class cannot erase a failed launch PID; a retained foreground PID and a newly failed launch PID may coexist (ShaderEditor is an example). This report does not infer that every package process died or that a screenshot regressed.
6. `static_sqlite` lists actual DEX invoke targets in the three requested families. Whole-DEX calls include bundled library code, possibly unused or reached only later; no startup reachability claim is made. A dynamic class name or native SQLite implementation can evade this managed scan.

| predicted_blocked | Meaning |
|---|---|
| y | Measured first observed terminal causally linked to CANTOPEN |
| n | That first-fatal condition is not evidenced in this selected measured log; **not** a safety/UI PASS |
| unknown | Measured disappearance/PID scope without a linked termination cause |
| possible-static | Unmeasured key with managed SQLite-family invoke references; conditional startup-risk forecast |
| unknown-no-dex-reference | Unmeasured key with no requested managed call reference; absence is not proof of safety |

The summary uses only measured `y` and separately counts `possible-static`. It does not automatically exempt, fix, sign or relaunch any key. No board/HDC/SSH/VM/locks/deployment were used. cc-t3's root-cause README/results in the parent directory are left unchanged.

## Reproduction

```sh
python3 benchmark/2026-10-10-el2-cantopen/collect_impact.py --workers 2
python3 benchmark/2026-10-10-el2-cantopen/audit_dexdump.py
python3 -m unittest discover -s benchmark/2026-10-10-el2-cantopen -p 'test_*.py' -v
```

`--reuse-static` only reuses the explicitly saved tool-SHA/APK-SHA-bound static extraction, while rereading actual measured logs. It refuses a changed tool, APK or key inventory. The final evidence lists all underlying source hashes; the completeness audit checks the retained raw output, not a claimed class count.
