# t3 deployment and rollback review — plan only

The controlled reboot is intended to answer whether normal startup overwrites the payload. **That runtime unknown is not a precondition requiring proof or additional user approval.** If the new child does not actually map the candidate SHA, the experiment is not established: stop candidate UI validation and restore. Do not change any controller, policy, permission gate or startup configuration to defeat an overwrite. No evidence reviewed here establishes equivalence between this ordinary single-library deployment and a previously stopped action.

## Bound target and rollback

The target is the application-owned backing file:

`/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/liboh_adapter_bridge.so`

The historical child22035/b6535369 maps it through `/data/local/tmp/asx/liboh_adapter_bridge.so`. Maps lines 6649–6652 and mountinfo line 112 identify this namespace relationship. Root `/system/android/lib64/liboh_adapter_bridge.so` is **8ab85446…**, a different object and excluded from the update. Root `/data/local/tmp/asx` was absent; do not infer the correct global target from that pathname alone.

Outer `rollback-copy-01` now supplies the actual global backing hash and metadata, matching the child object: baseline **b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4**, dev66352/inode560578, 2,023,136 bytes, UID/GID20011206, mode0644, label `u:object_r:appdat:s0`. Before/after stat and hash are equal; all seven recorded commands returned rc0. This lane independently hashed the downloaded baseline to the same full SHA. The copy is window-preparation evidence; the unique writer must repeat identity/metadata binding immediately before writing under its lock.

## Minimum reviewed sequence

1. Bind snapshot02 candidate **3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819**, its source/build and final CC/outer review, the exact rollback copy, fresh board/boot/process identities, payload metadata and freeze checks. Build01 is historical. Check original power/screen state and precise restoration steps. Existing factual gate refusals must be reported; no new approval gate is invented for the runtime overwrite question.
2. The designated writer alone publishes this single library by a verified temporary file and same-filesystem atomic rename, preserving original owner/mode/label. It does not overwrite a live mapped inode in place or modify system bridge/other runtime files. Perform one ordinary software reboot. Identify the new child afresh and bind its maps dev/inode to process-root stat/full SHA; a root-disk candidate hash alone is insufficient.
3. Only after actual activation, observe one initial desktop launch, one same-host Home/return, and one Recent-close/new-host reopen. At most one icon click per stage, at most 120 seconds observation per stage; use actual screenshots and normal approved touch actions. A replacement child does not prove recovery of the retained child. READY is not feed. Missing resource-identity observations remain unknown.
4. Stop new experiments by LOCK+900 seconds, start restoration by +1200, close by +1800. Restore exact baseline and metadata on success or failure, with at most one ordinary restoration reboot when necessary to remove candidate mappings. Verify the new baseline-loaded child, non-target fingerprints, original power settings and final screen before unlock. Unknown writes require read-only reconciliation, not duplicate writes; failed restoration is explicit recovery_required with a single-writer handoff.

The draft defines seven acceptance scenarios, including missing-input rejection, wrong target/activation, white screen or changed child, unknown writes, deadlines and rollback. `parse-final` and `lint-final` are rc0; lint quality is 100%, warnings retained. The future Rust receipt selector is named but **not implemented or run** in this planning task; visual outcomes require human review. No device command, deployment script, build, source/control edit, remote action or Git write occurred here.
