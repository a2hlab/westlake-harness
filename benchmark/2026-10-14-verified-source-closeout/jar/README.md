# SOURCE-CLOSEOUT — J1/J7b

Previous full-overlay producer rc0 was not an exact reproduction: only `classes.dex` differed, and strict wrappers returned 2. Static comparison now establishes **129/129 J1 and 161/161 J7b full class disassemblies identical**, without a missing/added/changed class. Raw code_item, debug_info and class_data sections are also identical. The mismatches are metadata pools, their referencing offsets and DEX signature/checksum. This evidence cannot replace the historical output SHA.

The [source sidecar](../../../sources/api-implementations/jar-production-closeout/README.md) contains 39/51 actual Java inputs and original Git/source hashes, a runnable producer pair, 14 locked dependency inputs, acquisition scripts and exact Docker image identity. One fresh JDK17 execution pair added only final smali `--jobs 1`, retaining every original injected call, baseline and postflight check. Both producers returned 0; both strict wrappers returned **2**. Fresh full disassemblies again match, while exact JAR hashes still differ.

| Artifact | Historical JAR SHA256 | Fresh JAR SHA256 | producer/wrapper |
|---|---|---|---|
| J1-final | `faf0782bb3a6dbf67a59022c35f95a1e3d33f35401f36d3a4ddbef309888180e` | `018cd9bd12325355cd8ab727b8b05d39b09d1dc65b1c0e6408a49f95d71b3cc3` | 0 / 2 |
| J7b | `381110a675fb543b6ad4102c8fc721fcb5673bc0da8644ececd1bab1ca60bec8` | `d5807ea1667442068a6d0557b36fa56be53174f03964a4e05f140f8634e0b70b` | 0 / 2 |

Observed bytecode in [ordering-probe.json](evidence/ordering-probe.json): `DexWriter.writeTypeLists 16→21`, `writeAnnotations 23→28`, `writeAnnotationSets 28→33` iterate pool values without an outer sort. Builder pools use `ConcurrentHashMap`; smali submits sorted source files to shared DexBuilder threads, with default jobs from `availableProcessors`. Prior J1 five and J7b six type-list order inversions are all same-bucket exchanges. Example J1 `(File,String)` versus `(S)` share bucket114; J7b `(Set)` versus `([B,String,String)` share bucket142. The decoded lists, hashes and offsets are [J1](evidence/j1-type-list-order.json) and [J7b](evidence/j7b-type-list-order.json). These are static observations; the inferred cause is concurrent insertion order. Identity hash was **not** established as the cause. The original scheduling and full production logs are unknown.

The new recipe recommendation is explicit serial final assembly for reproducible new outputs. It is not a fix for existing signed binaries and not a claim that historical layout has been recovered. Do not change historical expectations to the new hashes. There is no API implementation or device change.

Raw new [J1 stdout](evidence/j1/producer.stdout.txt), [stderr](evidence/j1/producer.stderr.txt), [receipt](evidence/j1/execution.json), and corresponding [J7b stdout](evidence/j7b/producer.stdout.txt), [stderr](evidence/j7b/producer.stderr.txt), [receipt](evidence/j7b/execution.json) are small tracked files. Wrapper rc and stream hashes are in [run.json](evidence/run.json). The original host executable path is normalized only in that public receipt; the unmodified host receipt is in the durable archive. Container source/output paths `/repo` and `/run-output` are actual executed paths. Class manifests and section comparisons retain both hashes.

[archive.json](archive.json) pins the persistent local and `hw248:$HOME/westlake-verified-source-closeout-91-20261014` archives. They contain the image (382,740,509 bytes) and original/prior/fresh artifacts, intermediate classes/disassemblies and unmodified raw receipts (6,898,116 bytes). Original 14 inputs remain in their existing 44,523,873-byte locked archive. Large binaries are not Git files. Nothing useful relies on `/tmp`.

```sh
python3 benchmark/2026-10-14-verified-source-closeout/jar/verify.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test verified_jar_source
```

The offline verifier checks actual source hashes, original/candidate producer hashes, exact one-line recipe delta, preserved wrapper gate, both real output hashes, raw streams, identical full classes/code and explicit rejection of unsupported historical completion. Negative tests reject missing/drifted dependencies, invented production logs, absent raw stdout, hidden rc2 and semantic-to-byte-exact promotion. The contract's human review remains pending; test PASS is not historical binary PASS. Source scope is the complete overlay producer with an explicit inherited baseline binary input.
