# The bridge double copy is in every lit app too — it does not explain the white windows

**What was wrong.** Since the N11 series the white-window cluster (no observed termination, 20 keys on the U10.1T8
candidate base) was attributed to the "double copy" of `liboh_adapter_bridge.so` / `liboh_android_runtime.so`, and
N11h / N11h-r2 were planned with the white keys as their predicted movers. Nobody had counted the copies in the
*lit* apps. Counting them on the same runs shows the double copy is universal: lit apps carry it exactly as the white
ones do. It cannot be the discriminator, so "N11h-r2 lights the white windows" has no evidence behind it.

## Evidence (U10.1T8 stage-A runs, all six board-level run directories, outer 2026-10-02 19:55)

`scripts/lab/n11h_readout.py --run <run> --json` on every stage-A run (window 1 r2, 2, 3, 4, 5, 5-5ea-r2), maps at
t5, grouped by the outer-signed U10.1T8 verdict (`benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json`) and the
candidate cluster table (`benchmark/2026-10-02-candidate-first-fatal-clusters/clusters.json`, cluster 0 = white):

| group | bridge copies | runtime copies | AssetManager JniAbort | keys |
|---|---|---|---|---|
| lit | 2 | 2 | no | 85 |
| lit | 2 | 1 | no | 30 |
| lit | no maps | | no | 1 (fd-reader, interrupted) |
| white cluster | 2 | 2 | no | 16 |
| white cluster | 2 | 1 | no | 1 (termux) |
| white cluster | no maps | | no | 2 (toutiao, frequent-habits) |
| other unlit | no maps (died before t5) | | **yes** | **7** |
| other unlit | no maps | | no | 24 |
| unsigned smoke keys (helloworld, zigzag; lit) | 2 | 2 | no | 2 |

- **115 of 115 lit keys with maps have two bridge copies**; 85 also have two runtime copies. 17 of 17 white keys with
  maps look the same. There is no copy-count difference between lit and white.
- The **AssetManager `AAssetManager_fromJava` → `GetLongField` → `JniAbort`** signature appears in 7 keys and in **no**
  lit or white key. That is the only failure on these runs with a mechanism that plausibly needs one runtime copy
  (a field/class cached in one copy read from the other); it is the cluster N11h-r2 should be predicted against.

`per-key.csv` has every key, its group, copy counts, AssetManager flag and the run directory; `counts.txt` is the raw
stdout of `tabulate.py`.

## Rule set this time

A suspected cause is only a cause if it **separates** the failing keys from the passing ones on the same runs.
Before predicting movers for a fix, count the suspected condition in the lit keys too. N11h, N11h-r2 and the
"17 white keys behind the double copy" estimate all skipped this one table.

## Reproduce

```sh
for r in <the six stage-A board-level run dirs>; do
  python3 scripts/lab/n11h_readout.py --run "$r" --out <tmp>/$(basename "$r") --json
done
python3 benchmark/2026-10-02-double-copy-universality/tabulate.py \
  benchmark/2026-10-02-double-copy-universality/per-key.csv <tmp>/*/n11h-readout.json
```
