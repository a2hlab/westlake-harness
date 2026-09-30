# Four offline slots for the next 66-key sweep

Previous tooling assumed three execution boards. This is a **four-slot plan**, balanced with the existing LPT implementation and J3 serial completion intervals. The current whitelist has only three OH boards; **D remains unassigned** until a fourth OH board is registered and provisioned. The Android reference is excluded. No device or app was started.

| Slot | Keys | Estimated seconds | Assignment |
|---|---:|---:|---|
| A-5ea | 17 | 882.430 | Existing OH board |
| B-5cd | 17 | 862.549 | Existing OH board |
| C-61b | 16 | 823.059 | Existing OH board |
| D-fourth | 16 | 822.638 | Pending fourth OH serial |

The four `keys-*.txt` files form a disjoint 66-key cover. [shards.json](shards.json) contains each APK SHA, timing samples and source SHA, slot identity, and key-file SHA; [costs.csv](costs.csv) is the compact cost table. Durations assume equal-speed boards and include serial setup/overhead. Failed/unmeasured samples use the cohort median. These are estimates, not measured four-board runtime. Subway uses the explicit current `ffd32287…` input revision; no historical frozen prediction was changed.

From repo root, with archived J3 runs under WORKSPACES/westlake-harness:

```sh
python3 benchmark/2026-09-30-round1-plan/shard/make_four_shards.py --out /tmp/four-shards-fresh
# Once a fourth OH board is registered, create a fresh plan with its full serial:
python3 benchmark/2026-09-30-round1-plan/shard/make_four_shards.py --fourth-serial "$FOURTH_SERIAL" --out /tmp/four-shards-bound
```

The generator rejects duplicate, unregistered and Android serials; it does not change the whitelist. Keys files can feed the existing batch command's `--keys` argument as a comma-separated string (for example `--keys "$(paste -sd, keys-A-5ea.txt)"`); the window owner chooses the actual output directory and board after replay preflight. This handoff does not authorize a batch run. The old three-shard merge_facts.py is unchanged and rejects four-shard plans; a four-run merger is outside this dispatch.

The new generator reuses `shard/shard_plan.py::historical_costs` and `balance` without changing old shard receipts. Tests: 17 replay/four-slot tests plus 19 existing shard regression tests pass. The parent replay receipt records hashes and provenance. No screenshots or alive counts exist for this planned sweep.
