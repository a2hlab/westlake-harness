# U10.1 tools repaired before supplemental observation

The runner continued to cv2 after original returned 2 for cleanup refusal. The first local mitigation exempted rc=1; the new outer instruction explicitly requires **every nonzero shard result** to stop remaining shards and enter before_unlock. Codes 1, 2 and interrupted negative statuses now stop; cleanup failure retains the lock. This is a tool-only change.

The failed 5ea activation read was `cat /proc/self/mountinfo` (recorded command-00899, original apply-device receipts). Missing markers can contain partial stdout; that output is never accepted or concatenated into the next attempt. Simple literal cat/sha256sum reads and exact process-table reads retry at most three times, one-second gaps, with a fresh marker and the **original shared timeout budget**. Valid remote nonzero status is final. Writes, command substitutions, redirections and compound shell fragments are never replayed. Uncertain writes still fail into the existing transactional rollback; the integrated executor test confirms original layers/bytes/running parent are restored.

Evidence: 18 runner tests, 65 batch tests, 25 executor tests passed offline. Four old batch fixture failures exposed its missing six installation-chain paths; the fake now supplies all six hashes. Production installation identity checks were not changed. No device I/O or lock acquisition occurred in this task.

## Proposed supplemental windows (not authorized to run yet)

The same armed bundle SHA `4714527476551b9f7072564741f23a29ac5bd36a1c01496c0b38ae5c84edcfad` and native manifest `325cd0a65d57407f8d41615501d2379c7afd4b446ff7458c736eb48ae05e0ddb` are unchanged; no binary was rebuilt. The three plans retain original serials, U9 verify-before-apply, activation markers/copy checks, 45-minute window /35-minute new-key cutoff, and unconditional U9/318/recovery-smoke/final finish. Each gets a new output through U101_RUN_ID.

* 5ea: original22+cv2 33 (55).
* 61b: original23+cv2 33 (56); repeat the earlier original prefix to produce a clean complete observation. Cleanup-damaged cv2 is not retained.
* 5cd: only remaining cv2 26; retain the outer-signed original22+cv2 7.

137 proposed plus29 retained equals166 unique prediction-v5 keys. New per-board CSVs are exact subsets of the existing predictions-v5. Any nonzero original shard ends that board window immediately; remaining cv2 is unknown and must be scheduled later, not auto-resumed. Completed app-failure summaries also return 1, so this may require another window even without cleanup trouble. **No new locks until outer reviews these plans.**

Commands after approval: set a fresh U101_RUN_ID and use master `scripts/lab/board_run.py retry-plans/plan-<board>.json --detach` in the configured lab environment. U9 fingerprints remain 5ea/5cd565fc6fdc116,61ba2919b793eb6; BOOT4db882a81732. N11g stays after the supplemental observation.
