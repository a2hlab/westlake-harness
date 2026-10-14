# API implementation sources and build entries

These directories contain the actual historical implementations recovered for the frozen API registry. They are delivered on the repository's default branch, `master`. They are not instructions to switch to an agent branch or recover a private worktree.

| Frozen API | Actual implementation | Build recipe | Verified scope |
| --- | --- | --- | --- |
| FZ-001: background launcher permission | [Installer and BMS source](FZ-001/README.md) | [Build and pinned dependencies](FZ-001/BUILD.md), [entry](FZ-001/build.sh) | Exact production source archive; full native rebuild still requires the recorded OH kit. |
| FZ-002: child thread stack | [Child implementation](FZ-002/src/child_main_after_stock.cpp) | [Recipe](FZ-002/BUILD.md), [entry](FZ-002/build.py) | Exact frozen source; original native link dependencies required. |
| FZ-003: asset file descriptor | [Implementation and provenance](FZ-003/README.md) | [Recipe](FZ-003/BUILD.md), [entry](FZ-003/build.sh) | Exact frozen source; complete external runtime build dependencies remain a gap. |
| FZ-004: JAR verification provider | [Implementation and integration](FZ-004/README.md) | [Recipe](FZ-004/BUILD.md), [entry](FZ-004/build.sh) | API unit compiled; unit compilation does not establish whole runtime JAR reproduction. |
| FZ-005: ART toolchain patch series | [Source patches](FZ-005/README.md) | [Recipe](FZ-005/BUILD.md), [entry](FZ-005/build.sh) | Exact patch series and production image generator; upstream AOSP tree and locked inputs required. |
| FZ-006: accessibility manager initialization | [Implementation and integration](FZ-006/README.md) | [Recipe](FZ-006/BUILD.md), [entry](FZ-006/build.sh) | Exact source; compile dependency is SHA checked. |
| FZ-007: TagSoup XML/HTML parsing | [Complete parser source](FZ-007-tagsoup/src/org/ccil/cowan/tagsoup/Parser.java) | [Recipe](FZ-007-tagsoup/README.md), [entry](FZ-007-tagsoup/build.py), [dependency fetcher](FZ-007-tagsoup/fetch-dependencies.py) | All 125 T7d source inputs in this repository; actual rebuilt DEX matches production. ZIP wrapper differs. |
| FZ-008: SSL socket compatibility fallback | [Implementation](FZ-008/README.md) | [Recipe](FZ-008/BUILD.md), [entry](FZ-008/build.sh) | API unit compiled; shared full T7d DEX verified. This fallback is not a complete TLS implementation. |

The API atlas must join each capability to its implementation paths, revision or source SHA, build entry, dependencies, output and verification evidence. A report path alone is not an implementation. Source delivery, source build, deployed identity and app behavior are separate facts; unknown evidence remains explicitly unknown.

Original source bytes and license notices are preserved, including upstream whitespace. Large toolchains and binary dependencies are kept in the SHA-pinned durable archives referenced by each recipe. Historical missing execution logs are not replaced by claims based on newly generated inventories.
