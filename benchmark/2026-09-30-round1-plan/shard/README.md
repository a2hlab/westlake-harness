# U1 three-board sharding and facts merge

The previous run does **not** record complete per-app start times. Costs therefore use adjacent `finished_at` intervals in its ordered, same-board/same-boot `summary.json`, including setup/inter-app overhead. The first key (Wikipedia) and three prelaunch failures (Seal, Toutiao, SubwaySurfers) use the median measured interval; no file mtimes or invented zero-cost jobs. APK-mismatched history is ignored. These are scheduling estimates, not actual U1 results.

[`u1-v1/shards.json`](u1-v1/shards.json) pins the 66-key cohort and historical source; `costs.csv` explains each estimate. Longest-processing-time assignment, with 22-key capacities, yields:

| Keys file | Board | Keys | Estimated seconds |
|---|---|---:|---:|
| [keys-A-5ea.txt](u1-v1/keys-A-5ea.txt) | 5ea34a45…1123012c | 22 | 1176.253 |
| [keys-B-5cd.txt](u1-v1/keys-B-5cd.txt) | 5cd1e3dd…923012c | 22 | 1153.702 |
| [keys-C-61b.txt](u1-v1/keys-C-61b.txt) | 61b06572…324012c | 22 | 1148.449 |

Estimated spread: **27.804 s**, about 2.4%; equal board speed assumed. The batch runner accepts comma-separated `--keys` and retains its original phase order: these files specify membership, not a required execution ordering. This tool does not launch apps, contact a board or take a lock.

From this directory, generate a new version with:

```sh
python3 shard_plan.py --history /absolute/previous/run/serial --out NEW_PLAN
python3 -m unittest test_shard
```

Optional `--keys FILE` accepts a JSON list of key records/strings or one key per line; default is the immutable 66-key forecast. `--expected-count` defaults to 66. Never overwrite a generated plan.

Merge completed or partial U1 shards:

```sh
python3 merge_facts.py --plan u1-v1/shards.json   --shard A-5ea=/absolute/U1-A/serial   --shard B-5cd=/absolute/U1-B/serial   --shard C-61b=/absolute/U1-C/serial   --expected-fingerprint /absolute/accepted-U1/runtime-fingerprint.txt   --out NEW_MERGE
```

Omit an unavailable `--shard`; all its keys remain **unknown**. `source-facts/` preserves supplied facts verbatim. The new `facts.txt` / `results.json` recount `record.json.screenshots[].captured` and UID/name process-table rows, excluding named same-UID helpers. Capture flags are counts, not proof that screenshot bytes still exist; no lighting label is inferred. Missing tables, UID, captures or records remain unknown. `observed_totals` are measured lower bounds; any incomplete full-cohort total is null. The original source total is never trusted instead of recounting.

Wrong shard/key, duplicate record, APK/serial/boot mismatch, conflicting profiles or frozen violations make the merge invalid (exit 1). Missing shards remain partial (exit 0). All present fingerprints must agree; even three identical profiles do not prove U1 without the accepted release fingerprint and zero-violation FROZEN readbacks. Missing FROZEN metadata does not suppress counts but blocks exact U1 scoring. An omitted source facts file also cannot supply a frozen-check receipt. Per-app profile sampling remains limited to producer metadata.

**19 tests pass**: balanced/disjoint allocation, timing fallback, identity mismatch, missing shard/table/flags, same-UID helpers, corrupted record, mixed/unbound profiles, duplicate keys, unfinished runs and frozen violations. A historical one-board recount independently recovers 126 captures and 28/27 t5/t20 alive, with three unknown process samples (`historical-recount.json`); this is not U1. The zero-run CLI smoke gives 66 unknowns and null full totals (`no-runs-smoke/`), not a zero-success sweep.
