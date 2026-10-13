# 5ea base controls — narrow offline ACCEPT

Exact apply SHA `4c04fb9ed3756177e71b0ee8f4c41c5b8e0421422a7db457acdff78399517cc9`,
plan `73034290318e255e8469c45f1c95697e2da4e26e2bc48a78f57149b2138c5990`.
Independent local **8/8 checks**, shell syntax rc0. No board commands or previous
transaction-matrix rerun. `5ea-base-delta-review.json` records each assertion.

The new body exactly equals validated5cd `0ddcad1e` after the declared boot/stage
substitutions, archive-present guard, and old-worker550-to755 guard/rollback
metadata changes. Partial-temp inode ownership, foreign preservation, rollback
97, pre-remount reseal flag and post-trap RO readback remain unchanged. Five
candidate/preimage hashes match actual referenced local files. Raw meta4/meta5
prove old worker and retained archive755:0:0; absence slots are not inferred.

**Retained archive does not itself reactivate adc on successful migration.**
Cfg7a954 still contains a boat service/job, but it invokes precisely the old
`/system/etc/westlake-u13-boat-overlay.sh`; apply167–173 removes this file and
191–192 asserts absence. Therefore this leftover service can fail on a missing
script, not read `sources-boat` or bindadc. New worker43491 has no boat archive
consumer or invocation of that old worker. The old cfg and script are backed up;
failure rollback restores them deliberately, so **do not reboot after failed or
partial apply**. A future reintroduced boat worker must not silently consume the
retained archive. No claim of zero service-attempt noise is made.

Placement does not remove current overlay mounts: 5ea remains nonbaseline until
the authorized reboot and fresh319 identity. Other independently installed init
activation entries must remain covered by root's existing init inventory; this
review does not assert their absence from these five files alone. No installer,
archive deletion, app start or reboot is present in this transaction body.
