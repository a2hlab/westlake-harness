# Complete J1-final and J7b overlay build delivery

The first delivery provided exact frozen API units but did not yet make the complete runtime-JAR overlay producers runnable from this tree. This supplement vendors all **39 J1-final and 51 J7b actual Java inputs**, the original producer with only an explicit path/freeze-check adaptation, strict source/dependency locks, and executable build/fetch entries. The original receipts listed 31/43 inputs; eight additional files per build were used by the producer but omitted from its receipt. They were recovered byte-for-byte from the same original Git commit and labelled separately.

The complete builds actually ran in the existing JDK17 image (`f3940036…`). Both original producers returned **rc0** after javac, D8, baseline disassembly, controlled injections, smali assembly and the original changed-class/postflight assertions. Both strict wrappers returned **rc2**: the newly generated dex and jar hashes differ from the historical frozen artifacts. `build-comparison.json` gives both exact pairs. This is a working complete overlay build, not a claim of byte-identical historical reconstruction. The difference remains unexplained; no freeze/acceptance criterion was relaxed and no output was deployed.

The 14 original compile/tool/baseline jars were found in OrbStack after checking local copies. All original receipt SHA values match. Their 44,523,873-byte compressed bundle was uploaded into a new persistent hw248 directory and independently read back by the new fetcher, which verifies archive SHA/size and each member. The small archive lock and explicit environment-based acquisition command remain in Git. Source code and build logic resolve entirely from this same tree; only pinned binary build dependencies are fetched. Complete source reconstruction of every inherited baseline-jar class remains outside this overlay producer.

- [FZ004 full producer and instructions](../../../sources/api-implementations/FZ-004/full-jar/README.md)
- [FZ006 full producer and instructions](../../../sources/api-implementations/FZ-006/full-jar/README.md)
- [New execution comparisons](build-comparison.json)
- [Source-drift rejection, SHA checks and original user-path gate](verification.json)

Original source and license comments are preserved. The full outputs, source snapshot, executable producers and raw new build logs are durably archived separately from the dependency bundle. Small raw stdout/stderr and execution receipts are retained here. These are new execution receipts; missing historical execution logs were not fabricated. No frozen source/runtime paths, devices, commits or remote branches were changed by this lane.
