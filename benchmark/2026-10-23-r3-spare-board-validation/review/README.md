# T121 package-stage independent review

**Package PASS: 70/70 independent checks. Executor review is separate and pending.**

The initial draft lacked promotion bytes; `initial-review.json` preserves that earlier state. Actual `promotion-01` now resolves that package gap. CC owns concrete init installation/restoration and the 900/180-second execution schedule; their absence from the env package is not a package-stage blocker.

- 22 actual regular payload files have verified SHA and local modes; the install manifest is the exact 20-file installable subset, with explicit target modes and owner `0:0`. Both generated cfg files are excluded from installation.
- Only `startup.env` and its expected digest changed. Startup bytes equal the exact two-line ENABLED/APPROVED_BY transformation. Other 20 files, including all 17 historical fixed files, remain unchanged; the T120 parent remains intact.
- Original init matches T116 raw bytes and SHA `19d0201b…`; rollback bytes are identical. Candidate init changes only the unique boot-entry argv. Original stat confirms `0:0`, mode `550`.
- Actual author promotion receipt is rc0 with empty stderr, pinned argv/start/end/stdout/stderr/rc. The reviewer did not execute author generators, payloads, or device commands.

Package manifest: `4eed2410d8d6c0d5d899bd7287c5b34ca53127d329df2ab69ae0d2482d8bcf47`.
Install manifest: `a4c87fd43a000edf02b40477d42e4d6cb38722bbbcfc360a5a357e6474543417`.
Env plan: `299097fe848b43306edfd00f52f1de8620b38c46bbb78ace019f3067823755df`.

Reproduce package checks with `python3 benchmark/2026-10-23-r3-spare-board-validation/review/check_promotion.py` from this checkout. The script writes adjacent `results.json`; implementation files are hash/stat only. Public results contain pins and check outcomes, not payload implementations.

This is neither device-write admission nor runtime acceptance. The outer coordinator must bind the accepted package and separately reviewed CC executor. Old ROOT stays untouched; restoring exact original init returns to it. No additional scan of five unindexed historical names is required. `spec-explain.txt` records three skipped contract scenarios, not device validation.
