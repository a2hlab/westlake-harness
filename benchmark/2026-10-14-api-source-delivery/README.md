# API implementation, source and build correspondence

The earlier API atlas linked several reports without the actual implementation or a runnable build entry. The default branch now contains the recovered implementation source and build plans, and the 315-row atlas links them directly. There are **340 exact master source references and 130 non-null build entries**. All 315 original capability, Android/OH evidence and APK validation grades remain unchanged.

Start with the [Chinese table](views/API-PROGRESS.zh.md), [searchable Chinese HTML](views/index.html), [English HTML](views/index.en.html), [CSV](views/api-progress.csv) or [JSON](views/api-progress.json). The [source index](../../sources/api-implementations/README.md) groups the frozen API, Java, native, installer and Boat implementations. No agent worktree or branch switch is needed to find the delivered code.

Each row connects its API to source files and revision/blob hashes, implementation scope, executable build recipe and command, dependency/toolchain locks, expected outputs, and separately scoped build/deployment/app evidence. Missing APIs, stubs, upstream-only references and unavailable historical build inputs remain explicit. An existing source file does not establish a successful fresh native build, historical byte equality or complete API behavior. Unity engine binaries remain external dependencies; their proprietary source is not claimed to be in this repository.

The final mapping is [release-v2/source-build-mapping.json](release-v2/source-build-mapping.json), SHA `c78e9e61f79b958f22e5f69a9309287d383c3824b74e38a16c4413e619c1d6b0`. Its [recipes](release-v2/recipes/recipes.json) are SHA `c6ad2f46e5b27578d4c1cda90ea7c973018f2ed49bcbb868c7c77cd6fd909261`. Earlier v1 snapshots are retained as historical evidence.

## Verification

The generator passed 13 refusal/data tests and its Rust wrapper. The supplement passed 15 mapping tests. An [actual MAIN physical-link audit](evidence/actual-main-links-publisher-fix.json) resolved 460 links in each language and 1,993 Markdown links, checking the source/build bytes where pinned. All 470 published source/build URLs are bound to `a2hlab/westlake-harness/master`, checked against the repository default branch. An [independent Git-object audit](evidence/actual-master-publisher-source-audit.json) verified all 340 source and 130 build references against actual default-branch bytes. This is an audit of the landed directory, not a simulated staging directory. Build receipts separately record the new 83-input Java compilation, production-matching TagSoup DEX, and J1/J7b historical DEX mismatches.

From the repository root:

```sh
python3 benchmark/2026-10-14-api-source-delivery/verify.py
python3 benchmark/2026-10-14-api-source-delivery/publication_check.py actual --views benchmark/2026-10-14-api-source-delivery/views
```

The historical 315-row signed snapshot remains unchanged. `all315_complete=false` records remaining API/build/deployment gaps; it does not hide the code and build plans that are now available on the default branch.
