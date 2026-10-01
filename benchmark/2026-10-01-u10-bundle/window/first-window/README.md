# U10 first window: rejected candidate

The offline baseline was not the deployed baseline. U10 policy `621caec4` was built from the reconstructed `0048d7d3` library, whose system-library list omitted `libsoundpool`; signed U9 actually deployed `fb9dc937`, which includes it. Export and normalized-call checks did not detect this data-table mismatch. Outer ACK(90) at 23:32:22 confirmed a regression and required all three boards to restore U9. Comparing a candidate against a reproduced surrogate does not establish compatibility with the deployed binary.

Bundle `11adfff7fef7` passed production admission and activation smoke on all boards. Each board locked at 23:00:48, with an enforced 23:35:48 new-key cutoff. The in-flight key finished normally. Original shards completed 18 / 20 / 18 keys (56 total); all 100 cv2 keys and 10 original keys were unrun, hence unknown. No continuation is permitted for this rejected candidate.

OpenCamera exited with `UnsatisfiedLinkError: system library is absent from the adapter manifest` in `android.media.SoundPool.<clinit>`. The same wall affected fd-app and fd-plus. The initial single-sample report was explicitly unconfirmed; the later deployed-policy comparison and correlated failures established the outer decision. No single-cause claim is inferred merely from a multi-component U9/U10 run comparison.

Per-board facts and summary files preserve the actual runner counts. Activation HW/ZZ t20 screenshots show their own interfaces on all three boards. The full raw evidence remains under `../boards/20261001T225833-u10r2/`; large hilog and transaction logs are not copied into this landing. `t20-index.json` lists all 56 shard screenshots with SHA and pending outer verdict. Recovery reports and screenshots are appended only after rollback and identity checks finish.

The candidate package is immutable failure evidence and has a durable `NOT-FOR-DEPLOYMENT.txt` marker. Its prior `rollout_ready=true` is historical authorization, not current deployment approval. A repaired U10.1 requires a new package and renewed gates.

All three transactions restored their 34 operations; final reports contain 318 assertions / 316 paths, empty diff/absent and unchanged boot IDs. Recovery smoke passed and local t20 review confirmed HelloWorld and ZigZag own UI on all boards. All locks were empty by 23:44. The compare_runs output reports 7 differences: four actual logical changes plus three installation-fingerprint fields absent in the older U9 recording; installation service bytes were not changed in this window.
