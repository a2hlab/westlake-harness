# Count liveness at the actual final capture

The previous formatter printed `alive_t20=0` for t10 captures even though no t20 process table existed. This was missing evidence, not a measured dead process. The updated formatter reads the last scheduled screenshot time and keeps missing evidence unknown. Mixed t10/t20 runs have separate totals. Raw subprocess return codes remain unchanged; fully wrapped rc=1 shards are `completed_pending_review`, not interrupted. The record `phase` remains the manifest classification, not a UI verdict.

Mac and VM each passed 30 tests covering both timing tiers, mixed tiers, missing evidence, UID matching and fully wrapped rc=1 continuation. Test outputs are `tests-mac.txt` and `tests-vm.txt`. Screenshot/UI verdicts remain with the outer reviewer.
