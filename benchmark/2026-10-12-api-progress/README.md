# Android API implementation atlas: preserve evidence strength and version scope

Previously, implementation knowledge was split between eight frozen entries, repair packages,
static export inventories, stub censuses and APK run reports. Reading a symbol count as functional
coverage, an AOSP source tag as a compatibility promise, or a past lit screenshot as current
behaviour gave the wrong picture. This atlas joins those records without promoting their claims.

Open **[the searchable Chinese atlas](index.html)** or **[the complete Chinese table](API-PROGRESS.zh.md)**.
The [CSV](api-progress.csv) has a UTF-8 BOM for spreadsheet applications; [JSON](api-progress.json)
is the structured capability record. Counts and validation levels are in [results.json](results.json): **314 records = 292 API capability records, 8 frozen indexes and 14 supporting-knowledge records**, with **125 hashed source paths**. The [verification receipt](verification.json) records four passing Rust checks and four passing contract lifecycles (12 scenarios). Browser preview was unavailable because the CUA connection timed out; generated JavaScript syntax passed, but no visual/interactive browser pass is claimed.

## Scope and evidence

Three independently assigned OctoLoop lanes inventory registry/cross-cutting, Java/services and
native/JNI capabilities. Every row names exact API members, implementation method, source/artifact
identity, separately scoped Android/OH versions, APK evidence, freeze IDs and outstanding gaps.
Outer review checks local source hashes, frozen-entry coverage and report semantics. No board
operation, runtime build or new functional test is performed for this atlas.

`reported` means a historical report was read, not that a screenshot was re-reviewed this round.
`static`, `unit`, `wall_shift`, `t20_ui` and `functional` retain distinct meanings. A wall shift proves
that API's failure disappeared, not that the whole application became usable. An intentional
no-op may be frozen as a compatibility behaviour without implementing its Android subsystem.

The scope is **repository-known capability groups and documented gaps**, not every Android SDK
method. Capability records include frozen indexes and related functional records, so their count
is not a distinct-API completion percentage. [Source coverage](source-coverage.json) retains each
lane's search scope, exclusions and unclassified material. [The benchmark index](benchmark-source-index.json)
lists all top-level benchmark README packages present at assembly, distinguishing packages with
cited evidence from those not directly cited; the latter label does not assert irrelevance.

## Historical detailed inventories

- [NDK symbol CSV](ndk-symbols-historical.csv): all 4,449 API-33 symbols in both 2026-09-21
  snapshots, joined by library and symbol. Legacy payload: OH 2,613, Westlake 117, missing 1,719.
  Source-build payload: OH 2,613, Westlake 307, missing 1,529. These are **export-presence** counts,
  not functional coverage or today's deployed gap count.
- [JNI stub CSV](jni-stub-declarations-historical.csv): original declarations from the 2026-10-02
  runtime `ac59dec0` census with source line numbers. The source reports 325 methods; it contains
  160 declaration lines, some grouping methods. The CSV preserves the grouping and does not
  invent an expanded list. Later fixes can supersede these historical states.
- [Platform context](platform-context.json): OH 6.1.0.31 current-campaign identity, historical
  OH 7.0.0.38 HelloWorld, AOSP 14 source, NDK API 33 and Android 11 reference exports remain
  different kinds of evidence. No cross-version support is inferred from them.

## Reproduce without a device

```sh
python3 benchmark/2026-10-12-api-progress/atlas.py build
cargo test --manifest-path tools/spec-checks/Cargo.toml --test api_progress
```

The checker hashes real referenced files and rejects missing files, hash drift, duplicate row IDs,
invalid status, missing fields and incomplete frozen coverage. It checks CSV field equality and
regenerated Markdown/HTML. Negative cases exercise missing evidence and hash drift explicitly.
This checks document consistency, not the truth of new API functionality. External worktree
references require the named sibling under `WORKSPACES` (default: repository parent); absent
material is an explicit validation failure, never an assumed pass.

No dependencies, external scripts or network calls are required by the searchable HTML.
Source/field edits belong in the shard JSON; outer semantic corrections and byte-identical canonical-path aliases are explicit in `curation.json`. Regenerate the views instead of editing them by hand.
The contracts are in `specs/api-progress/`. No push or runtime/frozen-registry modification is
part of this delivery.
