# API implementation, source and build correspondence

Latest observations: [2026-10-19 manual recovery and player loading](../2026-10-19-api-progress-update/index.html). This additive view links the actual source, build recipes and live evidence without changing the historical315 grades. Manual recovery has scoped feed evidence; video playback remains unpassed and its candidate was rolled back.

The earlier API atlas linked several reports without the actual implementation or a runnable build entry. The default branch now contains the recovered implementation source and build plans, and the 315-row atlas links them directly. There are **392 exact master source references and 143 non-null build entries**. All 315 original capability, Android/OH evidence and APK validation grades remain unchanged.

Start with the [Chinese table](views/API-PROGRESS.zh.md), [searchable Chinese HTML](views/index.html), [English HTML](views/index.en.html), [CSV](views/api-progress.csv) or [JSON](views/api-progress.json). The [source index](../../sources/api-implementations/README.md) groups the frozen API, Java, native, installer and Boat implementations. No agent worktree or branch switch is needed to find the delivered code.

Each row connects its API to source files and revision/blob hashes, implementation scope, executable build recipe and command, dependency/toolchain locks, expected outputs, and separately scoped build/deployment/app evidence. Missing APIs, stubs, upstream-only references and unavailable historical build inputs remain explicit. An existing source file does not establish a successful fresh native build, historical byte equality or complete API behavior. Unity engine binaries remain external dependencies; their proprietary source is not claimed to be in this repository.

The current mapping is [release-v4/source-build-mapping.json](release-v4/source-build-mapping.json), SHA `2892f1ef11051bc7b2834ddc40dc6da712f57cb61a31176f87c94fec46bbfe45`. Its [recipes](release-v4/recipes/recipes.json) are SHA `f26e7eabf187367ba4c84213b7bf04dc26e0b59c1c1818d2abb0251a3ae7fb33`. All 27 cumulative delivery amendments bind source on local master at `260231a3e1a440a90cc2ba67da100bd66cba8b55`. V4 updates only REG-002 actual build evidence and its scoped build entry. The [v3 mapping](release-v3/source-build-mapping.json), [v3 views](views-v3-review/API-PROGRESS.zh.md) and [v3 remote publication receipt](review-v3/remote-publication.json) remain historical evidence; that remote receipt does not certify publication of v4.

## Verification

The [v4 review](review-v4/results.json) records the original renderer/refusal and closeout amendment checks, canonical physical-link checks, and an [independent master-object and delta audit](review-v4/master-object-and-delta-audit.json). All 392 source and 143 build-entry references match actual local master objects. Only REG-002 has a substantive delivery delta; all original fields of the 315 historical records remain unchanged.

Build evidence has separate limits: TagSoup reproduces the historical DEX, while J1/J7b reproduce full class disassembly and raw code/debug/class-data but have different whole JAR/DEX SHA values. [FZ-002 new reproduction](../2026-10-14-verified-source-closeout/native/build-closeout/README.md) restored inputs, compiled the delivered `child_main_after_stock.cpp` and strict-linked original SHA-locked objects/dependencies, all rc=0. Its 504,984-byte provider is byte-equal to frozen SHA `0509fe235a7883b5cd9b57477221cb868465de944c6f70ed0cf2835b0fe4a97c`. This is not a whole-generation source rebuild or recovery of the original historical producing log. Prior failed restores remain preserved. FZ-001 has no new full BMS build; shared bridge8ab and libandroid9cc/ADC exact original producing bindings and FZ-003 complete original dependency generation remain unresolved. No API or device coverage grade changes follow from this build receipt.

From the repository root:

```sh
python3 benchmark/2026-10-14-api-source-delivery/verify.py
python3 benchmark/2026-10-14-api-source-delivery/publication_check.py actual --views benchmark/2026-10-14-api-source-delivery/views
```

The historical 315-row signed snapshot remains unchanged. `all315_complete=false` records remaining API/build/deployment gaps; it does not hide the code and build plans that are now available on the default branch.
