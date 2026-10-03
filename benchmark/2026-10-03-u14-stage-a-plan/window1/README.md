# U14 first-lock preparation

The copied U12 gate entry initially used the U12 BUILD receipt against U14's actual OAT. It correctly rejected the OAT SHA mismatch. Both raw failures are retained under `history-u12-t4b-binding/`; the corrected local entry invokes the unchanged T4b checker with the donor's actual `U14-BUILD.md`. No gate criterion or exception registry was changed.

The common and61b candidate bundles were armed by changing only `rollout_ready` and `rollout_blocker`. Each variant's3555 other files are byte-identical to its approved unarmed bundle. `arming-summary.json` records both exact field diffs and computed candidate identities. `arming-proof.json` in each variant contains the full inventory. The combined original is persisted with its SHA and size in `persistent-proof-index.json`.

Common armed bundle:56974aa051137bfd0da6f0dba2d714891c2aea4f65114e1600ebc5854a721770.
61b armed bundle:afb443708cdb9f7b4a26657b0f00068547f5918ea10802d6aafbb30156c95a1a.
Native manifest:3460435aa75195a3103a6da5b3e85e9299d9389ac64fedb7ee098d4bcb6103cf.

The candidates have322 identity assertions across320 distinct paths. The extra assertion is the admitted ICU74 compatibility library. Candidate runtime fingerprints are32c76e6fac13(common) and64f0b1538d49(61b), each125 files; boot fingerprint isf3e758e028b9 across36 files. Every observation must unconditionally restore its own U13 base,321 assertions/319 distinct paths, rather than a predecessor unified state.

## Smoke proposal pending outer review

The three `smoke-*-proposal.json` files contain HelloWorld/ZigZag controls, candidate fingerprints, all28 changed member SHA checks, and ART/JVM/bridge/runtime strict single-copy checks. They remain proposals: composition execution is disabled, and no board lock has been taken.

The M5/M6, Flutter and runtime bind-order markers come directly from donor sources, indexed in `smoke-source-index.json`. ICU74's seven tail branches, Gecko successful ABI paths and the AOSP ScanCallback class have no success logger. Their exact deployment identity does not establish a runtime call. The proposals explicitly record those gaps rather than using a failure log as proof of success. Also, the accepted U13 bridge/runtime maps contained two load bases; U14 does not contain the N11 owner repair. No two-copy exception has been silently imported into the requested strict single-copy proposal. The first-lock outer review must resolve these precise conditions.

`control_selftest.py` reuses the landed schema2 scanner. Both controls must have complete process logs and PASS: any selftest_error, badtag, probe_error, unknown or missing control rejects. A positive OK followed by an error still rejects. The8 known-answer tests pass independently on Mac andVM. No board smoke or UI verdict is claimed.

Fresh production outputs and the final four-surface summary are kept per variant. No infrastructure pre-lock report is claimed while these gates are still running; a real pre-lock report is required after the smoke review and before any lock.
