# video-1919-r4-final-review

ACCEPT — executor scoped for the authorized four-file r4 window; not a playback verdict.

Original draft is unchanged. Successor binds accepted player 5fba8050 and actual b427/644:20011206:20011206/appdat preimage. Three original backups precede first swap; target SHA/metadata/label or compat absence is checked immediately before each rename. Rollback binds original apply plan/boot backups, accepts exact original/current WID pre/post hashes only, rejects foreign bytes, and requires a fresh boot afterward. Label matching is now exact rather than substring. Existing Board/parent/serial/cfg guards remain.

Offline checker: rc0, 32 known-state branches and 11 foreign/tampered-plan refusals; three UNAPPROVED sentinel branches still refuse before Board setup. Real old r3 apply-plan uses WID33; WID34 is a synthetic independent observation fixture, not live evidence. Generated apply/rollback shell parses. No device commands or runtime tests were run.

From MAIN after exact landing, invoke `python3 benchmark/2026-10-19-toutiao-rea-methods/video-r4-executor-draft/successor-r6/video_guarded_window_r6.py MODE --boot "$BOOT" --parent "$PARENT" --birth "$PARENT_BIRTH" --out "$NEW_OUT"`; MODE is preflight/apply/rollback, and rollback additionally requires `--apply-plan "$ORIGINAL_APPLY_OUT/plan.json"`. Each output must be new. Outer holds outer(codex) lock, supplies real current identity, controls the <=30 minute window and fresh boot. This executor does not acquire/release the lock or perform reboot. Do not run with Python optimization (-O), which disables inherited assertion guards.

Landing list and SHA256SUMS identify this exact successor only; no prior frozen files are included. Source/receipt pins and offline-check scope are recorded in source-pins.json and offline-checks.json.
