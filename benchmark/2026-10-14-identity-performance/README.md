# Full128 identity gate: measured metadata cost

Replacing the identity gate with the 52-second R5 selfcheck would compare unequal contracts. Both check the same954 target/hash pairs, but candidate identity additionally checks507 file and5 directory metadata objects and every ancestor for symlinks.

| Completed window01 phase | Raw receipt span | Metadata attribution | Other attribution |
|---|---:|---:|---:|
| pre-lock |151.22s|137.10s|14.11s|
| after-lock (`before-identity`) |163.39s|149.09s|14.30s|

These are persisted finish-to-finish intervals, including scheduling/transport; startup and the first read are excluded. They are not isolated CPU timings. Each gate has73 reads:23 metadata batches, one Boat bundle,49 original Reader calls. The actual paths cause4,993 external `dirname` invocations and512 `stat` calls. Metadata accounts for about91% of the observed interval. SHA is already batched24.

The third native R5 selfcheck completed180 direct local calls in52.616s with rc0. This verifies the reusable direct transport pattern, not equivalent performance or safety of replacing the full identity gate. Existing presence batching and exact-realization/R5 transport are reusable; no fully equivalent already-validated bulk metadata replacement was found. Lowfork-audit r3 provides actual OH evidence that subprocess count matters, but its diagnostic helper is not a parent-path replacement.

Priority: remove external parent-path calculation while retaining each ancestor/type/stat check at its original position; then evaluate a separately pinned direct-transport adapter. Keep every pre-lock/after-lock/before-unlock epoch, boot/UID/parent/version/hash predicate, exact512 metadata objects, parser/status refusal, and raw receipt. Do not cache ancestors or results across paths/epochs. Any candidate needs offline equivalence and later independent on-device measurement; no speedup is promised.

`results.json` contains measurements, exact source pins, limitations and ranked proposals; the two receipt indexes bind every completed raw read to its SHA and mtime. No device call or running code/JSON mutation occurred. Recommendations apply only to future or independently rebound new runs, never an in-place change of current pins.
