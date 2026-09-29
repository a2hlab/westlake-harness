# Three-board alignment rules after the 14:46 capture

**Current control: accepted #66 native generation `6cb40cd6`, B5 Java and B2/B3 installer.** [alignment-profile.json](alignment-profile.json) contains all 130 active-profile full hashes from the 5ea snapshot, with collection identity. [reference-pins.json](reference-pins.json) is the older R155 historical reference retained for provenance; it is not an instruction to replace the current accepted generation.

## Concrete choices

| Component group | Current common native / reproducible control | Next action for a unified B4 run |
|---|---|---|
| Host / child / provider | `b7205719` / `03aa6216` / `3aa5d169`, generation `6cb40cd610ec29a69e320b8cc7d766ccffc675cbd7e94b709cc5d2462b9cddb0` | Keep this accepted control until a successor passes its own controls. Three-board native disk parity is already established. |
| Bridge | `84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a` | Current common control contains Stage/AcceptWant replies; known manifest JNI gap belongs to B9. Do not substitute the no-reply `7db99e1b`. |
| ART / openjdkjvm | `59e1bb45` / `8b462862` from route `6cb…` | Confirm the child's actual mapped route, not only the library basename. 5ea/61b HelloWorld confirmed; 5cd pending. |
| Java JAR | Control `250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146` | 5cd currently has r8b `d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554`; finish its acceptance, then select one full hash for all shards. Do not label it r7b `c432d987`. |
| Installer, both paths | Control `675536e8a43ac747cbffc0e130d5681ba7bcf2bd3fd305f3d0d357ca797a793d` | 5cd has fallback extension `1ebf78ab2bbe4573dfbe146b9f99e6b06e3a581fb9d16721c2272bc18e6cdfa5`. Promote this accepted functional fix consistently when publishing the forward profile; do not confuse it with stock `184d40a5`. |
| Old `74e6…` directory | 61b has two differing dormant files | Not used by captured children. Before selecting old R155 as rollback, restore that entire coherent profile, including provider `80c9aee0` and nativeloader `fde6f31c`; do not assume the directory name pins its contents. No cleanup is needed for current active parity. |

The immediate reproducible control is fully pinned; the recommended **forward** procedure is to finish the currently authorized r8b/B9 experiments, publish one accepted successor manifest, and only then distribute B4 shards. This task does not request interrupting tests or rolling back 5cd's experiment merely to erase the difference table. A B4 histogram combining B5 and r8b is not one-runtime evidence.

The latest user-approved B9 policy removes runtime sealing and moves identity checks to deployment, with single-file replacement after the new native generation is accepted. This inventory respects that direction. Its requirement is **observable deployed identity and compatible components**, not preservation of a particular runtime hash-enforcement mechanism.

## Evidence rules

1. **Compare snapshots by time and generation as well as boot.** Same boot does not prevent bind overlays changing. Preserve each command interval and collection SHA. Supplemental process evidence has its own timestamp and must not silently replace the original tree snapshot.
2. **Use whole trees and explicit coverage.** Equal requires three observed full hashes. A missing path is positively absent only after a complete tree walk. Connection failure with exit code 0 is still unavailable evidence. All 158 requested paths were read successfully in this collection.
3. **Derive roles rather than trusting ps NAME.** Here two real HelloWorld children inherited NAME `appspawn-x`. Require exact APK path, stat comm and parent relation; keep original role/evidence in derived JSON. PID reuse is checked with start time.
4. **Maps identify the file object.** Prefer a map-files hash whose device/inode equals maps. A process-root fallback is acceptable only with the same device/inode and a non-deleted mapping. A matching pathname string is insufficient. Backing-file hash is not a claim about relocated in-memory pages.
5. **Distinguish duplicate file mappings from duplicate ART runtimes.** Offset-zero rows are a useful flag, not sufficient proof of two initialized ART instances: a read-only inspection mapping can share the same inode. Inspect executable segments/load bases and namespace provenance before a causal claim. The two captured HelloWorld controls each have one offset-zero ART mapping.
6. **Do not conflate same-named provider copies.** The current child maps `6cb…/3aa5d169`; `74e6…/80c9aee0` and `74e6…/6787ea7d` are old copies. Differences in the latter are not evidence of the currently loaded provider.
7. **JAR/boot images remain distinct.** Preserve all ART/OAT/VDEX/JAR rows. A JAR may be consumed into anonymous dex mappings: report the active-byte gap instead of inventing a named mapping. Do not copy one boot image artifact in isolation to make a hash match.
8. **Installer parity includes foundation.** Both paths agree within each board; the captured foundation maps prove which variant is active. Existing desktop labels may predate the replacement library and require reinstallation by the execution lane to reflect new parsing.
9. **Hash difference is not automatically harmless.** r8b and installer fallback are known behavioral changes. Inactive old-generation files are inactive only within captured process scope; do not generalize to every possible future launch or rollback.
10. **Inventory does not award LIT.** UI acceptance remains the execution lane's screenshots and controls. This task has no new launch, screenshot or app-result claim.

## Pending item and finish rule

5cd has no HelloWorld process in the 14:46 capture. The outer loop confirmed cc-t3 owns the board for B8 and will supply a supplemental capture after release. Keep this field **pending**, without starting an app or taking a lock from this lane. `collect_process.py` and `summarize.py --supplement` preserve the new read's provenance and reject a changed boot or mapped hash mismatch. If the board moves to another generation first, report a separate sample instead of forcing it into the old snapshot.
