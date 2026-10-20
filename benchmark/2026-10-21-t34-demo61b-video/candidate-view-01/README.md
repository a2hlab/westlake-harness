# Immediate candidate process view (offline preparation)

W03 candidate physical hashes did not prove what the newly booted parent or child could see. Generate this bounded read immediately after the fresh candidate parent appears, before waiting for video failure. No device call is implemented here; the existing executor retains the board lock, transport, timeout and window budget.

Fill profile.template.json from actual current candidate boot, before boot, init namespace, parent/host PID, birth, PPID, UID, exe SHA, mount namespace and real host WID. For a currently observed child, add its independent identity object with PPID equal to the selected parent. Otherwise leave child null: output explicitly says UNKNOWN_NOT_SELECTED, not absent or passed. Host UID is20011206, parent UID0. Use the exact locally derived candidate run.sh; only its single numeric WL_PARENT_ID line may differ from the reviewed WID30 run. Other five candidate hashes are fixed.

```sh
python3 prepare.py --profile "$FRESH_PROFILE" --candidate-run "$CANDIDATE_RUN" --hdc "$HDC" --out "$FRESH_OUTPUT"
sh -n "$FRESH_OUTPUT/collect.sh"
```

CC executes collect.argv.json exactly once through the existing transport, saves the full actual argv/rc/stdout/stderr, and retains failures. Do not rewrite the argv as a placeholder. This is a read-only collection, not permission to apply, reattempt UI, restart or extend the window. The generated command is under32KiB. Identity drift, wrong WID, hash mismatch or failed command rejects the collection; do not auto-retry against another PID.

```sh
python3 report.py --stdout "$RECEIPT/stdout" --rc "$RECEIPT/rc" --out "$RECEIPT/report.json"
```

Physical and parent-root (optionally child-root) six files are stat/hash/stat read; compat must actually exist with its candidate SHA. Boot/process identities bookend collection. Run WID, parent environment and actual host WMS row must match. Maps/mountinfo are raw evidence. The report compares Linux device/inode identities at exact map paths; no mapping is UNKNOWN, not a load failure. Even a mapping identity match does not establish the selected dynamic-symbol winner. No process lifetime after the final guard is promised.

The seven offline tests use the actual W03 candidate run bytes and explicit synthetic identity fields, exercising profile refusal and real sh syntax; they do not simulate an OH runtime pass. CLI rejects fixture-profile.json. No build or board validation is claimed.

Revision02 preserves diagnostics before refusal: each available pre-stat, actual SHA and post-stat is printed before comparison. Missing files and mismatches accumulate rc82 while remaining six-state views and maps/mountinfo are attempted, then the final identity guard runs. Identity drift still stops immediately. The report retains observed lines and partial file comparisons under INCOMPLETE_OR_REJECTED; the final marker is not a pass when rc82. Init namespace format is validated and /proc/1/ns/mnt is tested in both guards. Two targeted tests execute the actual file_read shell against real host files and the actual init guard against an explicit readlink seam. No device validation is implied.
