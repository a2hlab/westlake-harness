# Demo baseline: board choice and t3 preparation

The former shortcut “three boards are uniform, choose the one with the most
screenshots” is inadequate: signed U13 intentionally differs at libinstalls,
and historical shards cover different key sets. Fresh read-only evidence now
selects61b: correct per-board U13 fingerprints,93.12GiB free against4.91GiB
signed-superset estimate, existing reviewed installer51e1b525.

See **board-choice.md** for the evidence, scope and limitations. t1 manifest is
owned by cx-bms; this delivery completes only the board-choice part. See
**t3-commands.md** and **prepare_t3.py** for offline command preparation.
Generated plans are disabled; APK identities, final capacity, identity hooks,
first interactions and effective-state smoke binding are checked before t3.

No LOCK, deployment, installation, app launch, screenshot or remote write was
performed. Fresh disk fingerprints are verified; process-root identity and
loaded installation service are not freshly verified. No new lit claim.

Artifacts: results.json; read-only command receipt and raw outputs; signed
history key sets;128-package size inventory; Mac/VM offline preparation tests;
contract/lifecycle receipts. No screenshot/binary is synthesized or replaced.
