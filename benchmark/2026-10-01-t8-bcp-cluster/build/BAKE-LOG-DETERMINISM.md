# T8 effective bake — execution log + determinism check (cx-t0 paired-receipt request)

cx-t0's U11 combine needs the **original execution log** of the T8 effective bake (rc=0 stdout + SHA).
The first bake ran via a background ssh whose stdout landed in a Mac task file, not persisted on hw248, so
there was no log under `/home/alvin/t8-cc-wiki`. This re-runs the bake with a tee'd log and byte-compares
the re-run output against the archived output to decide whether the log faithfully certifies the artifacts.

## Method — same-path bake, then rename (avoids the dex2oat path-embedding trap)
dex2oat embeds the full output path in `boot.oat`'s `dex2oat-cmdline` header (seen in the rb gate). Baking
straight into a new dir `out-eff-rerun` would make `boot.oat` differ **only** in that embedded string —
a false "non-determinism" the outer already documented (ACK(97) 11:12). So the re-run bakes into the SAME
path `out-eff` (embedded string stays `out-eff`), then the fresh dir is renamed to `out-eff-rerun` and the
original restored to `out-eff`. The byte comparison is therefore valid: both embed `out-eff`.

```
cp -a out-eff out-eff-orig
bash bake_eff.sh 2>&1 | tee logs/bake_eff-rerun.log     # OUT=out-eff, same embedded path
mv out-eff out-eff-rerun ; mv out-eff-orig out-eff       # out-eff = original, out-eff-rerun = fresh
```

## Result — rc=0 both; compiled code fully deterministic; boot.art 1–3 bytes vary (KNOWN benign)
| bake | rc | 27-file compare (original vs re-run) |
|---|---|---|
| candidate `bake_eff.sh` | **0** (files=27 zero=0) | **26/27 byte-identical**; `boot.art` differs **3 bytes @ offsets 254906–254908** |
| reference `bake_ref_eff.sh` | **0** (files=27 zero=0) | **26/27 byte-identical**; `boot.art` differs **1 byte @ offset 254907** |

- `boot.oat` + all 24 per-jar `boot-<jar>.{art,oat,vdex}` + `boot.vdex`: **0 differing bytes** — compiled
  code and per-segment images are fully deterministic run-to-run.
- The only variation is **1–3 bytes inside `boot.art` at offset ~254906**, which is exactly the known ART
  boot-image heap non-determinism the outer recorded in **ACK(97) 11:12 / T7D-REPRO-BACKTRACE-001**
  ("boot.art 差 … 254906 附近,和 PendingFuture backtrace 字段"). It is **not** caused by the T8 patches and
  is **not** in any compiled-code/segment output. `cmp -l` evidence: `receipt/bake-logs/determinism-cmp.txt`.

## Logs (persisted)
- hw248: `/home/alvin/t8-cc-wiki/logs/{bake_eff-rerun.log, bake_ref_eff-rerun.log}`
- repo + archive copies: `build/bake_eff-rerun.log` `build/bake_ref_eff-rerun.log` `build/determinism-cmp.txt`,
  and `$WORKSPACES/westlake-inputs/generations/t8-rebake-effective/receipt/bake-logs/`
- SHA256: `bake_eff-rerun.log` `853ad83340feee86e76536def41c0148464f28e78d524a6513d22da924ebec03`;
  `bake_ref_eff-rerun.log` `29b53a02a38c228bcce612eac1b09c4dd77cf3939483368481879356f3c0f7ca`

## Decision (outer) — re-run set is canonical
Outer chose **(B)**: the re-run outputs **`out-eff-rerun`** (boot.art `ab88cf388d95…`, boot.oat `4ba08485…`,
boot.vdex `23c1f5b0…`) are the **canonical T8 image**, byte-paired with `logs/bake_eff-rerun.log`
(`853ad833…`). cx-t0 fetches `hw248:/home/alvin/t8-cc-wiki/out-eff-rerun`. The Mac archive `image/` and
`receipt/image-sha256.txt` are updated to this canonical set (boot.art `ab88cf38`). The original first bake
`out-eff` (boot.art `d5b43805`) is left intact on hw248 for provenance.
All four gates (rb/t4b/G1/G2) hold for the canonical set unchanged — they read `boot.oat`/`boot.vdex`
(byte-identical to the first bake) and the `boot.art` header (identical); the 3-byte diff is only the
`254906` heap field, which no gate reads.

## Follow-up — `--force-determinism` tested and REJECTED (does not help, changes the oat)
Added `--force-determinism` to the same `dex2oat64` and baked **twice** at the original path (same
backup/rename flow), to see if it makes `boot.art` reproducible:
- **boot.art STILL non-deterministic**: fd-bake-1 `077b01ba` vs fd-bake-2 `fc17f006`, **2 bytes differ at
  offset 254906–254907** — the same field, unchanged by the flag.
- **boot.oat CHANGED**: fd oat differs from the canonical non-flag oat by **1,861,040 bytes (~17% of the
  10.9 MB oat)** — the flag alters compiled output.
- It also did **not** force single-threaded (`threads: 32`). The flag was confirmed present in the baked
  oat cmdline (not a no-op), rc=0 both.
- **Conclusion**: `--force-determinism` on this proven dex2oat64 neither achieves determinism nor is
  output-neutral, so it is **not** adopted as a default (it would change every image's compiled code,
  invalidate the canonical set, and require a full re-gate). Correct practice: pair the execution log with
  the **exact** re-run artifacts (done). Logs: `build/bake_eff_fd-{1,2}.log`.
