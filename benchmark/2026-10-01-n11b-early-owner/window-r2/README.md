# N11b corrected-reference retry

The previous candidate preparation confused old underlay references with resident U8 identities. After correcting references, the production dry-run was deployable and the locked pre-deployment read matched all 312 U8 identities exactly. The approved native manifest and sidecar were unchanged.

The executor then applied the candidate but its built-in HelloWorld probe failed with `control child count != 1`. Activation smoke and the ten Wikipedia/Noice samples never started. This does not establish the cause of the missing child or a single-owner result. No candidate maps or t20 screenshots were captured. Facts, screenshot and survival counts are unknown.

Automatic rollback restored files but initially failed its child probe; the next attempt lost an HDC status marker. One further idempotent rollback succeeded: 312 baseline identities and both parent/child process-root views passed, parent PID 26019, HelloWorld child PID 26693, one ART/JVM instance, child SHA d240f8d2, runtime/boot fingerprints e953c0921536 / 4db882a81732. The board was unlocked before 17:00, without reboot or kill -9. Earlier failure fields remain in the journal as historical evidence.

See `results.json`, `board61b/before.json`, `board61b/final-u8.json`, and `board61b/runner/board-run-result.json`. Large raw logs and command transcripts remain local; no raw run was removed.
