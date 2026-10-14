# FZ-008 — SSLSockets compatibility fallback

The actual frozen API implementation is [here](src/android/net/ssl/SSLSockets.java). It is copied into this repository; a branch name is provenance, not the delivery location. Byte identities are recorded in [provenance.json](provenance.json).

[Executable build entry](build.sh) and [dependency/build instructions](BUILD.md) distinguish API-unit compilation from complete runtime/boot-image reproduction. No device was touched and the original frozen registry was not changed.

Remaining boundaries:

- The frozen API intentionally returns false for isSupportedSocket and has a no-op setUseSessionTickets; it is not a TLS session-ticket implementation.
- The copied early T7d build receipt references jar6e2f450e, not the later frozen source_record jar d8b2406e. The same-tree [full T7d build](../FZ-007-tagsoup/README.md) now reproduces the historical dex from all 125 source inputs; its ZIP wrapper differs, and missing original execution logs remain a separate gap.
- Project-specific shim has no explicit SPDX/license header in the original source; no new license is invented.

[License notices](LICENSE-NOTICE.md) are retained without assigning a new license.
