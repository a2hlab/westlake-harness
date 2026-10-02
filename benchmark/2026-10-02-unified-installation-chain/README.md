# Unified-state installation-chain assertions

The promoted state is **U10.1T8**, not the prior U9. A generation name or native manifest does not establish installation-service equality. The existing six-alias fingerprint integration is retained; this delivery adds an exact per-path expected-identity assertion and archives fresh signed promotion observations.

## Actual signed observations

`comparison.csv` contains **18 rows: six aliases on each of three boards**, projected from the signed 318 identity tables and compared to each fresh Stage B `installation-chain.json`. All aliases match the signed state on their own board. Cross-board comparison differs at exactly these two paths:

- `/system/lib64/libinstalls.z.so`
- `/system/lib64/platformsdk/libinstalls.z.so`

Both paths are `2c9a5294` on 5ea/5cd and `51e1b525` on 61b. libbms (`6aadb8b4`) and libapk_installer (`7048c7c5`) match across all aliases and boards. Full SHA256 values and exact paths are in `unified-state.json`.

| Board | Runtime fingerprint | Boot fingerprint | Installation chain |
|---|---|---|---|
| 5ea | f3b604c94df4 / 123 files | e3806b65a079 / 36 files | libinstalls 2c9a5294 |
| 5cd | f3b604c94df4 / 123 files | e3806b65a079 / 36 files | libinstalls 2c9a5294 |
| 61b | d6848fa2c989 / 123 files | e3806b65a079 / 36 files | libinstalls 51e1b525 |

The runtime difference is intentional visibility of the service difference, not a JAR-only difference. 312 core assertions plus six installation aliases (two overlap existing paths) yield **318 assertions / 316 unique paths**. Both `sweep_bind_deploy.FINGERPRINT_PATHS` and the master batch include all six aliases exactly once. The archived signed per-board assertions are unchanged.

## Actual loader identity

Fresh promotion receipts observed each board's foundation mapping libbms and libapk_installer. Their `/proc/<pid>/root` hashes agree with disk, and mapped/process-root inode checks pass. **libinstalls was not mapped by an observed service in these control receipts: its actual loader identity is unknown on all three boards.** The on-demand `installs` service was absent. No service is started just to fill this gap.

The collector already searches exact `foundation`, `installs`, `installd`, `bms`, `bundlemgr` names, captures maps and checks SHA plus inode for any of the three installer libraries found. These checks remain strict; deleted or stale mappings reject. A future authorized clean-install batch will retain its own real service observations, without rewriting these historical unknowns.

## Tool addition

`installation_chain.compare_expected(expected, receipt)` requires **exactly all six paths and full SHA256s**, emits one comparison row per alias, and rejects missing/different disk bytes or observed stale-loader mismatches. Loader verification is a distinct `loaded_verdict`; matching disk bytes do not turn an absent loader into verified.

The standalone collector accepts `--expected`; `--receipt` checks archived observations offline and does not construct a Board. Example:

```sh
python3 scripts/lab/installation_chain.py \
  --serial 61b0657200000000000000000324012c --lane cx-t0 \
  --expected benchmark/2026-10-02-unified-installation-chain/evidence/61b-expected-services.json \
  --receipt benchmark/2026-10-02-unified-installation-chain/evidence/61b-installation-chain.json \
  --out /tmp/installation-assertion-61b
```

`tests.txt`: nine tests pass, including every alias required, full-hash validation, one-alias drift, actual mapped-inode mismatch and absent loaders as unknown. No board command, library replacement, foundation restart or persistent generation mutation was performed for this report.

## Pending alignment

The installation chain is **not unified**. Keep this per-board exception visible. The earlier approved alignment proposal `benchmark/2026-10-01-installation-chain-identity/README.md` remains a daytime, user-present service operation; it is not executed here. Any alignment must recover the **current U10.1T8** bundle (190afedd, U11i JAR, effective T8 images), not its historical U9 recovery recipe, verify both aliases and the actually loaded service library, and update fingerprints only after new real receipts and outer approval.
