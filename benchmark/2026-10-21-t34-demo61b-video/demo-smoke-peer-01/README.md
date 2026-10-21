# Independent demo smoke selector delta review

The existing UI entry launches imehost only. The successor adds a required two-app whitelist and changes only the object passed to `desktop_launch`. The remaining function sources are unchanged. Three new actual-main host tests were independently replayed, with source hashes unchanged before/after. Both selectors reach the real main branch; missing or invalid selectors stop before board construction. No device command was executed.

The exact activity names were also checked against actual historical selected-icon records: BoatAttack uses `com.unity3d.player.UnityPlayerActivity`; LibreSudoku uses `com.kaajjo.libresudoku.MainActivity`. This is not evidence that the current window has these icons or that either app is currently lit.

The original identity, power refresh, timeout and window budget code remains unchanged. Current screenshots still need human review; first-screen smoke is not completed gameplay or audio acceptance. Only the three new tests were rerun. The original replay receipt is persisted under `T34_DEMO_SMOKE_PEER_RAW`; its hash is recorded, and temporary fixture output paths are aliased in the public copy.
