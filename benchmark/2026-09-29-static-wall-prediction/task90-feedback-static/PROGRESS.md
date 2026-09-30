# Queue progress

- 2026-09-29 23:55 +0800: took the next authorized queue item immediately after task90 scan ACK. Existing complete r15c was evaluated against unchanged v4-r2, not against outcome-informed task90.
- 2026-09-30 00:00: added read-only full-batch evaluator with freeze hash, 66-key/completion gates and explicit partial diagnostics. Separate APK mismatch, unknown and nonfatal exclusions.
- Scanned all 32 available pinned APKs for seven missing requirement families using the existing startup graph. Wrote 224 rows and 66 merged predictions. No board access, source/APK writes or git metadata operations.
- Before publication, separated observed_wall_order from candidate_wall_order; only the latter includes new latent static candidates. No new device outcomes were consumed for that correction.
- Next completed full batch: run backtest_batch90.py against this freeze and new auto_triage JSON; retain unknowns and then revise a new version if a new family is evidenced. Current r16 sanity/control evidence is not a full batch.
