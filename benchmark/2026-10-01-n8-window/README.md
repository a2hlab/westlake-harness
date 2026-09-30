# N8 one-window test on 61b

N7 lost ZigZag with `inflateInit2_: symbol not found`. N8 removes only the root `libz.so` shell and retains its private copy. A missing symbol in N7 is evidence; assigning causality to the root shell requires the control experiment below.

Outer ACK(90) 2026-10-01 05:13:56 authorizes manifest `3dd48299b599c2adebe8cc574649a31d84fabae53b77d5a7df704f4f380b993e` and its 185 exact findings for one 61b window. This explicitly supersedes the offline-only boundary for the earlier preparation task, without authorizing new payload changes. The initial deployment grant expires at 05:45:22. A subsequent explicit outer answer extends testing to 05:56 and final restoration/release to 06:00:52 (45 minutes from lock acquisition). `extension.json` records that decision; the original deployment grant remains unchanged and cannot authorize another activation after its expiry.

Order: verify U5 hashes/runtime/boot and preserve J6 receipt; U5 ZigZag t20; same-board LocalSend maps reference; N8 deployment; three separate ZigZag t20 launches, each requiring image review before the next; then HelloWorld, six Flutter apps, Firefox/Fennec, McDonalds/Element and six additional controls. Any ZigZag image failure stops the experiment. Candidate singleton inode counts may not exceed this window's U5 reference. Sampled maps do not prove constructor-once behavior.

The VM supervisor uses the existing N7 rollback and receipt workflow. Every exit restores U5, checks native paths and parent view plus runtime `73ecf422dba2` / boot `0876029078e2`, revokes the grant, and releases the lock. Failed restoration retains the lock. The runtime JAR remains J6 during all launches; only native activation/rollback temporarily exposes package r8b.

Input manifests are retained from N7; tests use the current master bms_batch. Local inputs are symlinks outside the committed evidence set. Results and raw facts will be recorded after the window; no target success is implied by this plan.

## Scheduling handoff

The first target group retained master manifest phase order and captured ooniprobe, Aegis and Auxio before targets. The outer extension explicitly changed priority to the six Flutter apps, browser/Realm targets, then remaining controls. `handoff.py` verifies the command lines of our VM-only supervisor, runner and observer before stopping them; it does not signal any device process. The successor owns the existing activation and receipt and never redeploys. The new manifest changes only scheduling metadata (`phase` normalized for master sorting, `original_phase` retained); APK, package, entry and input identities are unchanged. Incomplete records from the interrupted group are retained and are not represented as completed tests.

`compare-n7-n8-zigzag.txt` reports **two** variables: root libz removal and launch-only app-data carryover. The three bright N8 images support the libz suspicion but do not establish a single-cause attribution under FLAW-008. No data reset was introduced into this window.

## Observed result

**Partially verified; not a full N8 acceptance.** U5 restored and lock released at 05:51:15, before the 06:00:52 hard deadline. Native/J6 fingerprint is `73ecf422dba2`; boot is `0876029078e2`. The supervisor stopped after `HDC lost remote status marker` while starting Fennec, restored every declared SHA and parent view, then unlocked. See `supervisor-result.json` and `final-receipt.json`.

ZigZag displayed its own UI in all three N8 captures; HelloWorld, OONI, Aegis and Auxio also displayed their own UI. Markor's captured t20 shows onboarding, but its interrupted record has no completion stamp. LocalSend/FluffyChat/KitchenOwl/Saber show white app areas; Immich/Libre/Firefox return to the launcher. Immich stops at Cronet `ATrace_beginSection`; Libre at `MediaStore$Images$Media.EXTERNAL_CONTENT_URI`; Firefox's process disappears with cause unknown. Do not turn absence of a terminal log into rendering success.

All six completed Flutter samples and Firefox have no added singleton inode count against this window's U5 reference (liblog already has two). Fennec, McDonalds, Element, Catima and Calendar remain unknown. Raw facts are in `facts-all.txt`, exact screenshot paths in `run-index.json`, reviewed classifications in `visual-reviews.json`, scoped logs and original records in `evidence/`. Interrupted records remain present.

Native deployment gates and the 257 approved A exceptions are independently reviewable in commit `8829b1ad`, branch `analysis/native-gate-master-landing`, based on master `7bd0060b5`. That commit does not grant N8 permanent exceptions: U5 actual dry-run passes 131 excepted findings; N8 without a grant still rejects all 185.
