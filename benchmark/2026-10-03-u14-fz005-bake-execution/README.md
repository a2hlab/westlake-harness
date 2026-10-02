# U14 FZ-005 re-bake executed on hw248 (cx-bms plan 1d92c70aa4): run1/run2 both rc 0; 26/27 byte-identical, boot.art differs in 2 bytes inside the known identity-hash field 0x3e3b8

#90. Executed by cc-t3 for cx-bms, whose sandbox cannot reach hw248.
- **Plan:** `benchmark/2026-10-03-u14-jar-image-plan/` (the copy in `westlake-harness-bms` is identical to master's).
- **Change being baked:** the only BCP change is stubs 615b8bbe → 87cf65cc. Runtime 0349eb83 is kept beside the inputs
  in `runtime/` and is not in jars9.
- **No a2hlab.** Nothing was deployed to a board.
- This is **recorded, not approved**: G1/G2/RB/T4B and the paired receipt belong to cx-bms.

## Script amendment (outer-authorised 04:37, hw248 copy only)

**Why.** As shipped, the script stops at its machine guard: hw248's real `hostname -s` is `ecs-9f6c`, so it printed
"Wrong machine", rc 3, before any mkdir. The ssh user is root, so `$HOME=/root`, while the frozen tools and the U12 bake
root are in `$HW248_HOME` (hw248's lab home).

**The amendment** (verbatim diff: `evidence/planned-bake-amendment.diff`):

| | sha256 |
|---|---|
| before (`plan-original/planned-bake.sh`) | `36a0fff08fb988b897c9b457929767b601aeeee903f23c0febad4f5b1e26d96a` |
| after (`plan/planned-bake.sh`, the one both runs executed and logged) | `cd1393fcce31d7b597e8dd835ddfadae451a019d87a870556bd3213706bb7498` |

```diff
-[ "$(hostname -s)" = hw248 ] || { echo 'Wrong machine; never use a2hlab during window'; exit 3; }
+[ "$(hostname -s)" = ecs-9f6c ] || { echo 'Wrong machine; never use a2hlab during window'; exit 3; }
+export HOME=/home/alvin
 export U14_ROOT="$HOME/u14-bt-bake-0349-87cf-v1" U14_RUN="$RUN"
```

Every other guard ran unchanged and passed:
- `sha256sum -c`: dex2oat64 `ae865ddd…` OK, t5 driver `14b1f709…` OK;
- jars9: 9/9 OK against `plan/inputs/jars9.sha256`; 9 jars present;
- run directories and logs absent before each run;
- both runs used the same `$ROOT/work`;
- host libraries: run1 equals run2 (`cmp`);
- live tee of the compiler and the session.

## Runs (`evidence/exit-codes.txt`, `evidence/driver-summary.txt`)

| | run1 | run2 |
|---|---|---|
| window | 04:38:42 – 04:38:54 | 04:38:55 – 04:39:07 |
| dex2oat / tee | 0 / 0 | 0 / 0 |
| session tee / script | 0 / 0 | 0 / 0 |
| t5 | 6 | 6 |
| products | 27, none empty | 27, none empty |

t5 = 6 is the comparison against the U13 reference image. It must differ, because the stubs changed, and the script
accepts 0 or 6.

## Byte comparison run1 vs run2 (`evidence/image-sha256-run{1,2}.txt`, `evidence/boot-art-run-diff.txt`)

**26/27 are byte-identical.** The only exception is `boot.art`:

| | |
|---|---|
| size | equal (4644864) |
| bytes that differ | **2**: 0x3e3b9 and 0x3e3ba |
| the 8-byte field @0x3e3b8 | run1 `28ba664000000000`, run2 `284adf4000000000` |
| boot.art sha256 | run1 `0fd84774e60858770f486b67fff723e4c5550724cd505320eb5cd933e12e8e33`; run2 `0425a50d0f62aee677c8a8968e6ae207c99f46408f4df9e5dbbe55dbe15de883` |

The bytes sit inside the historical `[0x3e3b8,0x3e3c0)` interval. This is the same object-header identity-hash shape
DIGEST records for T8 and U12 (U12's receipt: "run2 differs only known boot.art nondeterministic field").

**The interval is not auto-approved for U14.** Per the plan README §4, cx-bms locates the object in this image and asks
for the paired identity.

The stubs images, which are the changed part:
- `boot-adapter-mainline-stubs.art` `51a99d35…`;
- `.oat` `f213ea07…`;
- `.vdex` `4db720aa…`.

The two runs are identical for all three.

## Where everything is

- **Mac:** `$WORKSPACES/westlake-inputs/generations/u14-bt-bake-0349-87cf-v1/` holds:
  - `run1/`, `run2/` (27 + 27);
  - `logs/`: `bake-run{1,2}.session.log`, `dex2oat-run{1,2}.log` and status json, `ldd`, hostlibs,
    `image-sha256-run{1,2}.txt`;
  - `plan/` (amended), `plan-original/`, `planned-bake-amendment.diff`;
  - `jars9/`, `runtime/`, `driver.log`, `boot-art-run-diff.txt`;
  - `SHA256SUMS` (131 files, `-c` all OK; copied as `evidence/SHA256SUMS`).
- **hw248:** the same root, `$HW248_HOME/u14-bt-bake-0349-87cf-v1`, is kept, plus `reference-u13/`.
