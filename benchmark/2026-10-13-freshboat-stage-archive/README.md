# Completed spare-board Boat stage archive

The completed 5cd Boat stage previously retained its original evidence only on the local workstation. This archive preserves the exact closed `routeb-fresh-boat-stage/` tree, including stage execution stdout/stderr, original transaction data, one-boot evidence, both 954 selfchecks, controls, and screenshots. No external directories were traversed or included. The outer scheduler was notified to keep the source unchanged until verification completed.

The source completion receipt records `CANDIDATE_READY_RETAINED_NO_ADDITIONAL_EXPERIMENT`, full954 PASS, controls PASS, and outer visual review `HOST_TOUTIAO_FEED_WITH_PRIVACY_DIALOG; HW_AND_ZZ_T20_LIT`. The live final selfcheck independently records 954 entries, PASS, `synthetic=false`, and the same boot ID. Their exact SHA256 pins are in `completed-stage-gates.json`; this archive does not reinterpret or promote the source verdict. Boat playability on this board remains `not_tested`, and `v2_sealed` remains false.

- **11,437 regular source files**, **63,008,024 bytes**, zero symlinks.
- Each file was hashed before packaging. Every tar member was streamed and checked against the corresponding SHA256 and byte count. A fresh full source inventory after packaging exactly matched the first inventory, including file identity and metadata.
- The full per-file manifest is inside the archive at `__archive_meta__/source-manifest.jsonl`, SHA256 `ce1bf51bd6b703ea9bd8242e06aad35b2fb0f667d126f01bcbc25be7843b66c2`. Large local output stays under `.artifacts/`, outside the intended Git evidence set.
- Local and remote `gzip -t` passed. The uniquely created remote directory and noclobber upload avoided overwriting prior archives. Remote SHA256 and byte count exactly matched the local artifact; all subprocess return codes were zero and their original stdout/stderr are retained.

Archive: `hw248:/home/alvin/westlake-boat-fresh-stage-20261013T220632-cad0722d/freshboat-stage.tar.gz`

SHA256: `7581eb59438732fed9f05aa1d575a52b7535c1be9a96b1a4cff7496639e2961c`; compressed size: **5,354,636 bytes**.

Persistence completed at `2026-10-13T22:06:35.108222+08:00`. No HDC or other device call, source mutation, process change, commit, or push occurred. No private Noice backup was included. The completed full487 restoration and full128-window archives are separate prior receipts; this package adds the final closed Boat stage evidence without modifying them.
