# Addendum: exact Input replay confirmed

The outer executor ran the exact-source-file prefix-map replay from **2026-10-24 13:36:28.047872 to 13:36:32.187666 +08:00**, with **rc=0**. The actual output is **293416 bytes**, SHA256 `5777e4302752f419a7f4a9d6da3e5676a89e5a6bbe4a8d1be81fcdc9c6b85f89`. Local read-only verification independently hashed the output and compared its bytes with the archived original: identical.

The actual argv contains the additional exact source-file prefix map recorded in the outer delta. This confirms that the staged source-path spelling caused the observed Input object mismatch; restoring that spelling reproduces the complete object without source/header changes or binary patching.

The original [README](README.md), [results](results.json), and private proposed argv are unchanged historical records of the earlier unexecuted proposal. This addendum records the subsequent real execution; it does not retroactively change that earlier status. Original seven payload hashes were checked unchanged before and after packaging.

See [the result](pathmap-replay-02.json) and [raw evidence index](pathmap-replay-02-raw-index.json) for the exact argv, delta, receipt, stdout, stderr, transport and object hashes. Large/raw files remain at their persistent locations. Outer has now reported exact reproduction of all three original targets (WMC, stage and Input); this addendum independently verifies the new Input result only. No rebuild or runtime validation was performed here.
