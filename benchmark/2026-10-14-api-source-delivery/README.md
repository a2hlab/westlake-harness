# API implementation, source and build correspondence

The earlier API atlas linked several reports without the actual implementation or a runnable build entry. The default branch now contains the recovered implementation source and build plans, and the 315-row atlas links them directly. There are **392 exact master source references and 143 non-null build entries**. All 315 original capability, Android/OH evidence and APK validation grades remain unchanged.

Start with the [Chinese table](views/API-PROGRESS.zh.md), [searchable Chinese HTML](views/index.html), [English HTML](views/index.en.html), [CSV](views/api-progress.csv) or [JSON](views/api-progress.json). The [source index](../../sources/api-implementations/README.md) groups the frozen API, Java, native, installer and Boat implementations. No agent worktree or branch switch is needed to find the delivered code.

Each row connects its API to source files and revision/blob hashes, implementation scope, executable build recipe and command, dependency/toolchain locks, expected outputs, and separately scoped build/deployment/app evidence. Missing APIs, stubs, upstream-only references and unavailable historical build inputs remain explicit. An existing source file does not establish a successful fresh native build, historical byte equality or complete API behavior. Unity engine binaries remain external dependencies; their proprietary source is not claimed to be in this repository.

The current mapping is [release-v3/source-build-mapping.json](release-v3/source-build-mapping.json), SHA `061642bd3490f6c0ebc8db1a62a2a42121ed9d863d88a3e94abb0dd41665d2c1`. Its [recipes](release-v3/recipes/recipes.json) are SHA `0a7368cf25c5e9c4f37f3a22d3165d550553b6720d151835c53a57d0d31f433a`. The 27 delivery amendments bind source on local master at `6ac1a8f7045519f617a04e9ba33563091e98b608`; earlier v1/v2 snapshots remain historical evidence. Remote publication is not established by the local Git-object audit.

## Verification

The current v3 verification passed 13 refusal/data tests and 6 closeout amendment tests. The [actual MAIN physical-link audit](review-v3/publication.stdout.txt) resolved 536 links in each language and 2,163 Markdown links, checking the source/build bytes where pinned. All 535 published source/build URL references target `a2hlab/westlake-harness/master`. The [independent Git-object audit](review-v3/master-object-audit.json) checked all 392 source and 143 build-entry references against actual local master objects. The [independent review](review-v3/results.json) also confirms that all original fields of the 315 historical records remain unchanged.

Build evidence has separate limits: TagSoup reproduces the historical DEX, while J1/J7b reproduce full class disassembly and raw code/debug/class-data but have different whole JAR/DEX SHA values. Both native provider attempts stopped during input restoration, before compilation. Shared bridge8ab and libandroid9cc/ADC exact producing source/build bindings and the FZ003 complete original dependency generation remain unresolved. Source delivery and a callable build entry do not establish successful native reproduction.

From the repository root:

```sh
python3 benchmark/2026-10-14-api-source-delivery/verify.py
python3 benchmark/2026-10-14-api-source-delivery/publication_check.py actual --views benchmark/2026-10-14-api-source-delivery/views
```

The historical 315-row signed snapshot remains unchanged. `all315_complete=false` records remaining API/build/deployment gaps; it does not hide the code and build plans that are now available on the default branch.
