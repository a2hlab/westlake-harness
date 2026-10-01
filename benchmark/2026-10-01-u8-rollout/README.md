# U8: preserve U7 native, deploy J9 plus the T7e image group

The previous unsafe assumption was that a jar/stubs change could reuse an unbound image-build receipt. This bundle binds every input/output explicitly; missing original T7e log evidence remains unknown until supplied. No gate is bypassed.

Staging has 29/29 SHA matches. Candidate native is unchanged U7 manifest 7bc02de7 (312 identities); only J9 runtime jar 87fd463d, T7e stubs f3bcc9d7 and the 27-image group change. `assembly.json` records each byte change. Expected RUNTIME **e953c0921536** (119 files), BOOTIMAGE **4db882a81732** (36 files); baseline U7 is 68b7fb016253 / 8fe2e5fd7d65.

Package: `$WORKSPACES/westlake-generation-u8-j9-t7e`. `assemble.py` uses the production U7 executor example and trusted repository primitives; source staging is preserved. T7e source recipe/receipts are cc-t3's `benchmark/2026-10-01-j8-t7e-reproducible/` and `benchmark/2026-10-01-j8-jar-donors/build-receipt-t7e.json`; J9 is based on J8, not rebuilt from another Java base. Native package, bridge846, original ART, installer and declared ZigZag app-native sidecars are unchanged.

Deployment follows the outer ACK97: one <=30-minute window per board, LOCK/held, exact U7 readback, stop only identified residual BMS children, production apply, 312 identities/parent-child views/one ART, then master bms_batch HelloWorld and ZigZag with launch-only and t5/t20 captures. Leave U8 if passed, unlock, submit facts verbatim for outer image review. 5ea waits for cc-wiki's bridge-only window and full U7 rollback. On failed production verification the executor performs full U7 rollback; retain all original raw evidence and receipts. Signed suite controls are not clean-reinstalled because reinstall removes their five private native mounts.

No board writes have occurred in this U8 report yet. Counts and UI verdicts remain unknown until records and outer review exist.

The changed-output-path logcap replay is historical evidence only: it matches 25/27 files. Its boot.oat difference is not excepted, because the oat key/value header embeds the complete dex2oat command line. Approval proposal `T7E-REPRO-BACKTRACE-001` is restricted to the PendingFuture backtrace word in boot.art and its derived header checksum; exact-original-path reproduction must first confirm all other 26 files (including boot.oat) and all remaining bytes. The proposal remains pending and the package remains non-deployable.

## Exact-path reproduction

The original-path replay matches **26/27 files**, including boot.oat, with the complete original embedded command found in both oat headers. Original boot.art is `5af70ff6`, replay is `293dc1af`; only offsets 254905..254907 differ in the backtrace word. The header checksum and all bytes outside that word match. Original reference hashes still match all 27 staged originals. `evidence/same-path-comparison.json` is independent read-only verification by cx-t0; cc-t3 preserved original `out` and placed the replay in `out-recheck`. The final proposal excepts only the word, not header checksums or boot.oat. It is still proposed pending outer registration.
