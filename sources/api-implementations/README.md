# API implementation sources and build entries

These directories contain the actual historical implementations recovered for the frozen API registry. They are delivered on the repository's default branch, `master`. They are not instructions to switch to an agent branch or recover a private worktree.

| Frozen API | Actual implementation | Build recipe | Verified scope |
| --- | --- | --- | --- |
| FZ-001: background launcher permission | [Installer and BMS source](FZ-001/README.md) | [Build and pinned dependencies](FZ-001/BUILD.md), [entry](FZ-001/build.sh) | Exact production source archive; full native rebuild still requires the recorded OH kit. |
| FZ-002: child thread stack | [Child implementation](FZ-002/src/child_main_after_stock.cpp) | [Recipe](FZ-002/BUILD.md), [entry](FZ-002/build.py) | Exact frozen source; original native link dependencies required. |
| FZ-003: asset file descriptor | [Implementation and provenance](FZ-003/README.md) | [Recipe](FZ-003/BUILD.md), [entry](FZ-003/build.sh) | Exact frozen source; complete external runtime build dependencies remain a gap. |
| FZ-004: JAR verification provider | [Implementation and integration](FZ-004/README.md) | [Unit recipe](FZ-004/BUILD.md), [full JAR recipe](FZ-004/full-jar/README.md), [full entry](FZ-004/full-jar/build.py) | Unit and full producer compile completed; full JAR DEX differs from the historical frozen artifact, so strict verification rejects it. |
| FZ-005: ART toolchain patch series | [Source patches](FZ-005/README.md) | [Recipe](FZ-005/BUILD.md), [entry](FZ-005/build.sh) | Exact patch series and production image generator; upstream AOSP tree and locked inputs required. |
| FZ-006: VibratorManager initialization | [Implementation and integration](FZ-006/README.md) | [Unit recipe](FZ-006/BUILD.md), [full JAR recipe](FZ-006/full-jar/README.md), [full entry](FZ-006/full-jar/build.py) | All 51 full producer sources delivered; compiled DEX differs from the historical frozen artifact, so strict verification rejects it. |
| FZ-007: TagSoup XML/HTML parsing | [Complete parser source](FZ-007-tagsoup/src/org/ccil/cowan/tagsoup/Parser.java) | [Recipe](FZ-007-tagsoup/README.md), [entry](FZ-007-tagsoup/build.py), [dependency fetcher](FZ-007-tagsoup/fetch-dependencies.py) | All 125 T7d source inputs in this repository; actual rebuilt DEX matches production. ZIP wrapper differs. |
| FZ-008: SSL socket compatibility fallback | [Implementation](FZ-008/README.md) | [Recipe](FZ-008/BUILD.md), [entry](FZ-008/build.sh) | API unit compiled; shared full T7d DEX verified. This fallback is not a complete TLS implementation. |

The API atlas must join each capability to its implementation paths, revision or source SHA, build entry, dependencies, output and verification evidence. A report path alone is not an implementation. Source delivery, source build, deployed identity and app behavior are separate facts; unknown evidence remains explicitly unknown.

Original source bytes and license notices are preserved, including upstream whitespace. Large toolchains and binary dependencies are kept in the SHA-pinned durable archives referenced by each recipe. Historical missing execution logs are not replaced by claims based on newly generated inventories.

## Additional implementation families

- [Later Java and host sources](source-build-host/README.java.md): the actual 206-file Java snapshot, host declarations, original build tools, source locks and patches; [build entry](source-build-host/build-java.py). [A new executed build](../../benchmark/2026-10-14-api-source-delivery/review/later-java-build-01.md) compiled 83 adapter inputs to 160 owned classes. This does not assert byte identity with the historical r84–r89 runtime.
- [SQLite JNI runtime187 sources](native-sqlite187/README.md): eight exact native compilation inputs with source provenance and the original runtime build route.

- [Later native implementations](source-build-native691/README.md): 177 exact upstream blobs, original bionic and missing-native build entries, headers, locks and 22 API member mappings. Source and shell checks passed; a new native compilation and historical ELF equivalence are not yet claimed.
- [Activity-name launcher](JAVA-115-launcher/README.md): actual Python launcher, imported helper and locks; its relative/bare/qualified/invalid Activity checks passed.
- [Historical graphics compatibility source](legacy-graphics-7e4b38/README.md): preserved implementation and provenance for the legacy supporting record.

- [Exact APK native extraction](JAVA-042-installer/README.md): the two historical production C++ inputs, patches and isolated build entry using the SHA-pinned OH kit.
- [Boat V2 overlay implementation](NATIVE-138-boat-overlay/README.md): five original orchestration scripts/configuration files and an offline staging entry. Unity binary dependencies do not imply delivery of Unity engine source.
- [Bitmap owner source reference](NATIVE-122-bitmap-reference/README.md): exact Android 14 upstream implementation; historical deployed ELF binding and the unimplemented proposed patch remain separate.

See the [complete API/source/build correspondence table](../../benchmark/2026-10-14-api-source-delivery/views/API-PROGRESS.zh.md) or its [searchable HTML view](../../benchmark/2026-10-14-api-source-delivery/views/index.html).

- [Activity manifest theme (J10d)](JAVA-033-theme/README.md): exact tracked Java source, original caller patch and newly executed build reproducing historical JAR `57d62183`.
- [Boat C9 input-dispatch JAR](boat-c9-jar/README.md): original producer, two exact donor smali inputs, locked baseline/tools, and independent archived-input replay reproducing signed JAR `6333bcab`.

- [Boat V2 production sources](boat-v2-production/README.md): exact signal shim source, C7/C4 transforms, project revision and build inputs. C7/C4 output hashes match; the new signal build differs only in GNU build-id.
- [J1/J7b full producer source and recipes](jar-production-closeout/README.md): 39/51 exact source inputs, 14 locked dependencies and raw new build receipts. All 129/161 disassembled classes match historical outputs; whole JAR hashes differ and the historical exact-byte gate remains rejected.
