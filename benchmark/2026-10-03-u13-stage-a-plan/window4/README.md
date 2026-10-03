# U13 Stage A window 4: evidence and safe recovery

The outer reference list originally contained 16 real keys and a spurious `see` token parsed from a comment. The first 61b batch therefore refused before creating any app record. Our first plan test compared only the authority list, so it failed to catch the bad token. A subsequent claim that `see` belonged to corpus-v2 was withdrawn after reading both manifests. Master `f321212543` removed the token; the new pre-lock membership guard rejects unknown and duplicate keys without changing any acceptance gate.

## Execution and evidence

5ea and 5cd completed six authorized keys each, restored their exact U10.1T8 baseline and released their locks. Minesweeper was captured by normal desktop launch; the reviewed conditional ability fallback was not invoked. The outer read these twelve t20 captures and signed them without confirmed regression.

The corrected 61b retry captured NetGuard, K-9 and OrganicMaps. OrganicMaps then failed verified cleanup, producing `batch_interrupted`; the runner stopped immediately with rc2 and did not attempt Seal. The master batch loader orders keys by phase and manifest order, not keyfile order. Our earlier statement that putting OrganicMaps at the end of the keyfile guaranteed it ran last was incorrect. Its actual order was NetGuard, K-9, OrganicMaps, Seal. Do not claim a keyfile order as an execution order; an app required to run last needs its own shard.

The initial retry finish rejected live Android children and retained the lock. RUNBOOK's existing manual recovery identified the OrganicMaps BMS UID and the unique root parent, checked each child UID/PPID in the same command before signaling, drained the observed children in one batched shell, and stopped the parent only with `begetctl`. No root parent was killed and no board reboot occurred. An initial attempt used unavailable `awk` and returned rc1 before its guarded kills; the successful attempt used the existing `sed` identity checks. Both command receipts remain in the raw archive. Normal executor finish then restored all forty mount operations, verified 318 assertions, passed recovery smoke and final verification, and unlocked at 08:13:26.

Seal is continued as an isolated, previously unattempted authorized key in `window4-61b-seal`, with the same package bytes and actual 61b baseline, fresh Mac/VM production gates, a 30-minute window /20-minute new-key cutoff, and unconditional restoration. It completed with two captured shots, t5/t20 alive, zero selftest_error/badtag/probe_error/unknown, followed by unconditional318 restoration, recovery smoke PASS, final PASS and unlock. The final receipt reads finish.json mtime08:37:47.958493+08:00. Screenshots remain subject to the outer verdict.

## Identity and interpretation

The candidate uses common native manifest `85aef68e…` and the separately authorized per-board bundle/base. Activation identity is 321 assertions over 319 unique paths. Restoration is 318 assertions over 316 paths: 5ea/5cd runtime `f3b604c94df4`, 61b runtime `d6848fa2c989`, and boot `e3806b65a079`. The installation chain remains unchanged and intentionally differs between boards; no installer, JIT or unrelated configuration was changed.

Facts are copied verbatim from records. `alive`, `foreground_unconfirmed`, or a PASS receipt does not establish displayed app content. Screenshots require the outer review. OrganicMaps has a t20 capture even though cleanup interrupted the batch; completed-attempt counts and captured observations must remain separate. Selftest schema2 records the three failure classes separately; an unknown process is not a PASS.

The first window had actual Mac/VM production rc0 receipts. The corrected four-key retry reused those exact receipts only after recomputing unchanged policy/native ticket bindings; it is not represented as a fresh full-gate run. The isolated Seal continuation reruns both production surfaces. Infrastructure receipts preserve vmgr RSS, orb latency and VM boot identity. OrbStack reopen was performed only after all boards were unlocked; it did not reboot the VM. Raw logs, fault trees, process views, screenshots and original failed windows are retained in `$WORKSPACES/westlake-inputs/generations/u13-stageA-window4-20261003/`, with a complete chunked SHA inventory.

## Validation

`test_window4.py` and `test_plan_membership.py`: 6 tests passed, including known rejection of the original `see` plan, acceptance of sixteen real keys, correct path resolution with WORKSPACES unset, and a known answer for the actual manifest execution order plus isolated Seal continuation. The guard also ran through actual Mac and VM production paths. The delivery carries exact image bytes and path-normalized small evidence; full raw artifacts are persistent rather than discarded. This window does not authorize promotion.

The complete raw inventory contains **104,512 files /471,495,342 bytes**, bound by140 SHA-indexed chunks. `observation-coverage.json` distinguishes sixteen captured authorized keys from fifteen completed attempts; OrganicMaps is the captured cleanup-interrupted attempt. The old retry plan's unattempted Seal is resolved by the isolated continuation rather than erased from its historical coverage. `final-recovery-receipt.json` preserves separate per-board verification times; `results.json` uses normalized public copies.
