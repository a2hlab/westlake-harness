# Later Java implementation source and build entry

The local legacy adapter still returned `-1` from `getTaskForActivity`. It therefore could not represent the r84 task-root repair. This directory delivers the real later implementations from **a2hlab/westlake commit 691433b967ba01365a382d30fbd820c1231c0811**: all 206 Java files under `framework/`, their repository license, and the five `apps/imehost` source/resource files. No binary is substituted for code.

The snapshot includes the complete seven-component Java input set used by `build_westlake_java.py`, plus mainline stubs. Later upstream changes coexist with the r84–r89 repairs. This is an exact source snapshot of that commit, **not an assertion that its output equals a historical r84–r89 production artifact or the sealed device**. Old frozen sources and registry entries remain unchanged.

`manifest-tools/` contains the original compiler and helper/import closure, packaging recipes, and toolchain/source locks from **a2hlab/manifest commit 5057daae74503004ad2a9d627d0c04429a8e14fd**. Four irrelevant old-machine import scripts are omitted; no production implementation was omitted from the 206-file Java snapshot. These source-build recipes predate some delivered Java changes: a new full compile remains unexecuted, and compatibility with the restored framework prerequisites must be verified by that compile. There is no historical stdout/rc claim.

Run from the repository root:

```sh
python3 sources/api-implementations/source-build-host/build-java.py --check-only
python3 sources/api-implementations/source-build-host/build-java.py \
  --workspace "$RESTORED_SOURCE_WORKSPACE" \
  --core-build "$CORE_JAVA_BUILD" --framework-build "$FRAMEWORK_JAVA_BUILD" \
  --core-extension-build "$JAVA_EXTENSIONS_BUILD" --out "$FRESH_OUTPUT"
```

The wrapper pins every delivered input, rejects an existing output directory, invokes the actual source compiler, and preserves new stdout, stderr and exit-code receipts. The compiler checks prerequisite artifact hashes and class ownership. Output is `westlake-unrelocated.classes.jar`; it is not directly deployable. The retained `manifest-tools/tools/package_framework_runtime.py` and `manifest-tools/SOURCE_STACK.md` describe D8/runtime packaging and its separate prerequisites.

External dependencies are explicit: the source workspace supplies the locked JDK 21 compiler and Android source module descriptor, and the core/framework/extension build directories supply their hash-verified `artifacts.json` and class JARs. These large AOSP/toolchain prerequisites are not represented as vendored here. Their acquisition pins are in `manifest-tools/*sources.lock.json`, `java-compiler.lock.json`, `toolchains.lock.json` and related included locks; the delivered `fetch_sources.py` / installation recipes read those locks. Full native/build dependency closure and a new complete Java build are not claimed.

`westlake-java/LICENSE` is the original upstream Apache-2.0 license. Individual original headers remain intact. The retained manifest repository has no root LICENSE in the selected source tree; no separate license is invented for its original project scripts. `java-source.lock.json` records exact Git blobs and SHA-256 values for both origins. Capability/member mapping is in `benchmark/2026-10-14-api-source-delivery/review/java-source-resolutions.json`.
