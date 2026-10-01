# N10b activation-marker revision

The approved 342198db candidate lacked success logs for the child JNI-owner preload and Emboss registration. That could pass offline checks without demonstrating activation on the device. This revision adds logs after successful initialization; it preserves the original approval evidence in the parent directory.

Child dc73a28d and runtime ac59dec0 were independently rebuilt twice with identical bytes. Native manifest a118aca0 has 154 findings identical to the approved candidate; master 27943e370 registers them for this short window. The production dry-run is deployable, G1/G2 pass, and frozen checks report zero violations.

`knowledge/smoke/n10b.json` requires all four fixes’ own success markers, control survival, exact runtime/boot fingerprints, four single-copy libraries and five child-view SHA values. Offline tests reject missing markers, duplicate owners, incorrect hashes/fingerprints and dead controls.

The 5cd transaction uses the standard master board_run and master bms_batch. Its optional before_unlock command restores and verifies U8 before releasing the board. If rollback fails, the lock stays held for recovery. Six bridge targets are split across their actual v1 and cv2 manifests and run sequentially. Screenshots remain pending outer review.

Build recipes retain their recorded pre-relocation source paths. `source-relocation.json` records the unchanged source bytes now archived here. No original approved parent evidence was overwritten.

## 5cd authorized retry result

The first window was mistakenly stopped on `foreground_unconfirmed` and `unknown sessionId`. Outer review of all four control screenshots showed normal HelloWorld/ZigZag UI, with unknown-session counts equal to the signed baseline. This was a screenshot-unread error, not a control regression. That attempt, its recovery refusal on a live RPN child, the exact cold stop and successful U8 rollback are retained.

The fresh window began 14:14:10 and completed before 14:35:48, within 30 minutes. Standard master board_run ran detached. The historical activation smoke reported 19 checks passed using distinct-path counting; post-hoc c2508ebdd counting rejects it because bridge and runtime each have two load instances. both three-key bridge shards completed. Facts are copied verbatim in `board5cd-a118aca0-r3/summary/facts-all.txt`: controls 4/4 screenshots and 2 alive t20; three fix targets 6/6 and 2 alive t20; old bridge shard 6/6 and 3 alive t20; cv2 bridge shard 6/6 and 1 alive t20. These are process/capture facts, not lit counts.

GLMark2 emitted the NDK-cache initialization marker but still aborted through GetLongField; its t20 is the OH desktop. The cause of that remaining abort is not determined. All six read80 diagnostic reports say NOT FIXED; their log criteria do not substitute for outer screenshot review.

The before_unlock rollback returned zero. All 312 U8 identities, parent/child views and the ART map gate passed; fingerprints are e953c0921536 / 4db882a81732. The board lock was released. N10b was not retained. Source/tests are locally committed only, no push.

A cloned pre-read helper initially saved the retry's read-only snapshot under r2. Its actual retry snapshot was copied to r3 with `baseline-output-provenance.json`; recursive helpers now use their own __file__. The original approved gate artifacts remain unchanged. Raw attempts and screenshots were not deleted.

## Corrected owner count and outer UI verdict

`posthoc-instance-check.json` rechecks the preserved probe maps with master c2508ebdd. ART and openjdkjvm each have one instance; bridge and runtime each have two, even though each repeats the same pathname. The old smoke JSON is retained unchanged and is not evidence of single ownership. Outer ACK(95) 14:35:25 signed acrylic and ath0-rpn lit; glmark2 remains dead and the six #80 keys are unchanged. N11 addresses the duplicate owners.
