# U9 approved rollout

The earlier bundle was deliberately not deployable until J10g signoff. This revision records the outer-loop signoff, sets the bundle rollout-ready and passes the real production dry-run.

- U9 is U8 plus accepted N10b native and J10g `238ffc14`. N11b and the unapproved installer candidate are excluded.
- Expected runtime/boot fingerprints are `a8cb9a5a45a6 / 4db882a81732`. The executor verifies 312 identities; final readback adds four unchanged frozen installer aliases.
- The ten-marker smoke specification covers N10b and J10d/e/f/g. ART/JVM must each have one load-address instance; bridge/runtime retain exactly two, matching the accepted U8 state.
- The full planned corpus contains 166 unique keys: 66 original and 100 corpus-v2, partitioned 56/55/55. HelloWorld/ZigZag controls are additional. `keys-*` preserve the plan; unfinished keys are recorded separately rather than counted as observations.

## Window adjustment

The initial 5ea deployment plus ten-marker smoke took about 17 minutes. The outer loop rejected extending the 45-minute board window (ACK(80), 18:33:43) and instead approved partial sweeps: complete the current key, publish actual facts, obtain outer t20 review, strictly verify the U9 identities, and retain U9 only after that review. Remaining keys move to subsequent windows. A missing smoke marker or identity mismatch still causes U8 recovery.

The finish hook requires an explicit `partial_retention.outer_read_confirmed=true` for incomplete-shard retention. That flag is not inferred from survival or `foreground_unconfirmed`. Without confirmation, incomplete facts cannot retain the candidate. Three offline tests cover this boundary, final identity verification, and a smoke failure that remains fatal even with partial-review approval.

Raw command logs and screenshot originals stay under `boards/`. Compact receipts, facts and screenshot indices are copied to `evidence/` for landing; originals are never deleted. A successful deployment is not a screenshot signoff, which belongs to the outer reviewer.
