# U13 Stage A window2: signed per-board effective baselines

Window1 refused deployment on 61b because its common reference asserted the 5ea/5cd installation-service bytes. Window2 uses the outer-approved metadata-only 61b reference. The installation services and every runtime artifact remain unchanged by that rebind. Before locking, each executor preparation was compared with the independent full signed baseline and candidate path maps; all four actual Mac/VM production runs passed. Screenshot verdicts remain with the outer reviewer.

## Admission and execution

Authorization `c811f1a154` binds 5ea/5cd to unarmed `91272eaf` on `190afedd`, and 61b to unarmed `8861a11a` on effective baseline `c0adc4a9`. Arming changed only `rollout_ready` and `rollout_blocker`. The armed SHA values are `2abe4a49` and `0a31ad35`; their complete values are in [results.json](results.json). Native manifest `85aef68e` and inputs `c40faa79` are identical across boards. The 61b installation-service reference retains `51e1b525` at both paths; service-action count is zero.

Each real production gate used the master implementation, production tool PATH, fresh output, its actual effective baseline, and the signed per-board authorization. All four returned rc0/deployable=true: N1 55 excepted / 0 rejected, N2 104 excepted / 0 rejected, static PASS, G1/G2 true, RB/T4b zero errors, and frozen composed violations zero. Receipts are under [evidence/production](evidence/production).

Three detached windows started at 04:34:28. Candidate activation smoke passed and verified 321 assertions over 319 unique paths on each board. The 35-minute new-key cutoff and unconditional finish were retained. To ensure the authorized six auxiliary captures were reached, they ran once after the first regular group, followed by the remaining regular groups: Fitness six on 5ea, a six-key group on 5cd, and the first movers group on 61b. Regular shots remain t5/t20; auxiliary shots remain t20/t45/t90. This scheduling change is implemented in `../window2-observe.py` and tested in `test_window2.py`.

| Board | Finished regular observations | Unique regular keys | Remaining observations | Finish time from lock |
| --- | ---: | ---: | ---: | ---: |
| 5ea | 17 | 12 | 27 | 42.90 min |
| 5cd | 17 | 17 | 19 | 42.78 min |
| 61b | 9 | 9 | 47 | 42.49 min |

The six Fitness trials are independent single-key shards. Every remaining key is explicitly unknown due to the new-key cutoff. Full measured/remaining lists are in [coverage.json](coverage.json); auxiliary captures do not enter the regular regression denominator. No lit count or regression verdict is inferred from foreground status or process lifetime.

## Selftests and long waits

[Selftest schema2 results](selftest-summary.json) retain each shard's separate `selftest_error`, `badtag`, `probe_error`, and unknown counts. All three error classes are zero. Unknown runs are 2/2/5 on 5ea/5cd/61b and are not PASS. The 61b unknowns include three regular process observations and its two auxiliaries. All six Fitness trials have zero errors and zero unknowns.

All six auxiliary attempts have terminal records. Frequent-habits failed before launch with `exact desktop icon absent across searched pages`, therefore has no captured images or bind evidence. The other five have t20/t45/t90 captures. [longwait-readout.json](longwait-readout.json) records exact bundle-derived target PIDs, bind-return evidence and captured paths. Toutiao has a bind-return OK line. No explicit target-process terminal line was established by the conservative parser for these captures; missing terminal evidence is unknown. Its first exception candidates include caught B8 library-load errors, which are not claimed as first fatal exceptions. Routine registered JNI names and sigchain noise are excluded from terminal classification. Full logs remain available in the raw archive.

## Restoration and infrastructure

All runners completed `before_unlock` with rc0. Each finish unconditionally restored U10.1T8, passed recovery HelloWorld/ZigZag smoke, and verified all 318 assertions over 316 unique paths with empty `diff` and `absent`. Independent held checks returned rc1/empty on all boards. [Final recovery receipt](evidence/production/window2/final-recovery-receipt.json) records durations, unchanged boot IDs and checks.

Restored runtime fingerprints are `f3b604c94df4` on 5ea/5cd and `d6848fa2c989` on 61b; boot fingerprint is `e3806b65a079` on all three. The runtime difference is the already-signed installation-service divergence. No service restart or alignment occurred.

Gate work raised vmgr RSS above 3 GiB. OrbStack was preventively reopened before locking, and the VM boot ID and vmgr PID were verified unchanged. Final pre-lock RSS was 2,793,536 KiB with orb latency 0.122 s; after-window RSS was 2,443,632 KiB with orb latency 0.164 s. No OrbStack restart occurred during the locked windows. Raw and normalized health receipts document the sequence.

## Evidence and reproduction

- Verbatim per-leaf `run_facts.py` outputs were posted to the board. Normalized public copies are in [evidence/facts](evidence/facts). An initial invocation at the runner container returned zero keys and is excluded from results; those invalid receipts are preserved only in the raw archive.
- Actual snapshot bytes and records are in `evidence/{5ea,5cd,61b}/`. Contact sheets are [5ea](sheets/5ea-t20.jpeg), [5cd](sheets/5cd-t20.jpeg), and [61b](sheets/61b-t20.jpeg); matching order files distinguish candidate and recovery controls.
- [public-evidence-index.json](public-evidence-index.json) binds normalized text to raw source SHA values and records byte-identical image copies. Paths are normalized, not observations.
- Immutable raw evidence is at `$WORKSPACES/westlake-inputs/generations/u13-stageA-window2-20261003`. [raw-inventory-index.json](raw-inventory-index.json) binds 122,867 files (2,596,657,777 bytes) through 164 SHA-indexed chunks stored in that archive's `inventory/`. No raw logs, faults, images, or binaries were dropped.
- `export_evidence.py` is offline only; `make_raw_inventory.py` inventories the persistent archive. `python3 benchmark/2026-10-03-u13-stage-a-plan/window2/test_window2.py` checks board-specific authority, W1 exclusion, Fitness six, 61b 56 unique planned keys, unconditional 318 restoration, and once-only auxiliary scheduling.

These are observation-window receipts. No retention, new window, or promotion is authorized by this delivery.
