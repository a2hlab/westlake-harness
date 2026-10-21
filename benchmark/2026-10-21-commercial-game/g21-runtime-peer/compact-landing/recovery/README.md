# Original-journal recovery: rolled_back

G23 commit 226d658b04 was used for the original U7 --rollback, which returned rc0 at 20:04:33 +08:00. The original plan, operations, mount before-image and remote transaction directory are unchanged. All 32 operations remain restored; this attempt issued no bind or unmount command.

The original label recipe completed at command 00528: shell paths299/mismatches0, and before/after audit each295 PASS. Command00592 started appspawn-x with remote0. Baseline direct files, parent21963 root and child22734 root each match all319 baseline hashes, retained in hash-stages.json. The recorded maps gate passes; reported runtime/boot fingerprints remain fd464714645b/ee927db88a67 (124/36 files). Label counts are summarized in ../label-summary.json; raw receipts are indexed in ../original-sha-index.json.gz.

This was Hello World control recovery, not a candidate retry or game launch. results.json preserves the recovery-stage screenshot-not-evaluated and closure-pending fields as historical state; the subsequent visual review and final closure are separately in ../closure/. Old failure strings in the successful rollback receipt are retained history, not new failures.
