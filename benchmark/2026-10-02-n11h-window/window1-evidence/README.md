# N11h observation: owner-sharing markers do not imply a single loaded owner

The host-only candidate failed the **load-base gate**, despite its resident-check and inherit markers. The production runner evaluated the smoke result and automatically rolled back; no observation shard started. This is a mechanism refutation, not a screenshot-based control regression verdict.

`candidate-smoke.json` binds host `65ac5089`, runtime `5b620859a5f6` and boot `e3806b65a079`. `candidate-maps.txt` from PID 12129 has one ART and one JVM load-base, but **two bridge and two runtime load-bases**, at the addresses preserved in `results.json`. Both required marker patterns matched four times in the HelloWorld buffer. Per-key marker counts in `results.json` are file-local; shared hilog buffers overlap and must not be summed as independent calls. Conditional HOST-OPEN has zero hits and is advisory.

The 26 distinct targets / 40 planned launches were **unmeasured**. Screenshots from the two smoke controls and restored controls are supplied for outer review. No lighting count is asserted.

`finish.json` passes restoration to **U10.1T8**, not U9. `final318.json` has 318 assertions / 316 paths, empty diff and absent lists, runtime `d6848fa2c989`, boot `e3806b65a079`. `restored-smoke.json` passes HW/ZZ survival, signed bytes and the baseline's accepted two bridge/runtime copies. `runner-result.json` records before_unlock=0 and no shards. The runner released the 61b lock at 18:36:06; a separate held check returned 1 (empty).

Both facts files were regenerated using `scripts/lab/run_facts.py` on the actual run directories and are copied verbatim. Raw logs, transaction journal, full screenshots and command captures remain intact under the raw_root in `results.json`; this landing copy does not prune them. A subsequent root-cause claim requires new evidence; this delivery does not infer where the remaining second load originated.
