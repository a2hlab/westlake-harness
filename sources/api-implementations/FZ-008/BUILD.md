# Build and dependency boundary

`BUILD_OUT=/new/output ./build.sh` compiles the exact frozen Java class using standard javax.net.ssl types. The source blob `958e2cc5fd10c6bb72b3bf69b3de93f454662855` at commit `6b2e921203ab1489d2d88a58c740590369369cf2` is delivered exactly.

The complete T7d source delivery is now available on this same repository tree through [FZ-007 build.py](../FZ-007-tagsoup/build.py), [125-input source lock](../FZ-007-tagsoup/t7d-sources.lock.json) and [build instructions](../FZ-007-tagsoup/README.md). Its SSLSockets input is byte-identical to this frozen unit. The [new full build receipt](../../../benchmark/2026-10-14-api-source-delivery/tagsoup/t7d-build-receipt.json) records 125 Java inputs, 205 classes and a dex byte-identical to historical production (`deeb2a2157087d4367cafd6f30878c8f22a2e2089da4b304368b95b7b7bf6860`). Follow that entry for the full jar build and pinned dependency acquisition.

The new jar ZIP wrapper is not byte-identical to historical jar `d8b2406e…`. The copied earlier receipt (`6e2f450e…`) remains historical evidence only. Complete original build stdout/exit receipts remain unavailable; the new execution does not rewrite that gap. Neither entry rebuilds or deploys the final boot image.
