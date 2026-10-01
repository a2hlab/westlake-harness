# N11f 61b window: single-copy refuted, U9 restored

The proposed callback reuse did not eliminate duplicate load instances. The host emitted `done stage=8 branch=0 index=0`; candidate SHA **f1b43386** was witnessed from the child view. ART/JVM were single; bridge/runtime each still had **two mapping bases of the same inode**. The activation gate therefore failed and board_run invoked finish; **no 18-key target observation ran**. Outer signed REFUTED. Do not treat the normal control images or branch 0 as single-owner proof.

- Window: **00:32:30–00:37:13**, 61b only, no reboot. `candidate-zero-offset-maps.txt` lists exact addresses/inodes; full probe maps are retained.
- Final U9: **318 assertions / 316 paths**, diff={}, absent=[]; runtime **a2919b793eb6**, boot **4db882a81732**, unchanged boot ID. Rollback reports byte-identical and zero residual mounts. Restored smoke PASS, final verification followed it, before_unlock=0, lock released.
- Candidate and restored HW/ZZ `run_facts.py` outputs are copied verbatim in four `*-facts.txt` files. They count capture and UID-process presence, not rendered lighting.
- `controls-contact-sheet.jpeg`: rows 1/2 candidate HW/ZZ, rows 3/4 restored HW/ZZ; **left t20, right t5**. Individual snapshots are indexed with SHA in `screenshots.json`. Outer reads/signs UI; no lane lighting count is asserted.
- `predict_vs_actual` on an empty signed-sample set prints **compare: {'missing': 18}**. Its exit0 means no evaluable regression, **not prediction success**; all targets are unobserved.
- Continuous capture/raw transaction location and hashes are in `raw-evidence.json`. Only small excerpts and maps are committed; the complete logs remain intact in the raw directory. Native code was not changed during this window.

Next task is a design-only N11g blueprint, separately recorded in `benchmark/2026-10-02-n11g-sealed-owner-blueprint/`; no new build or deployment.
