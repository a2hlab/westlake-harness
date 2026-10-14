# FZ-002 — Dedicated 8 MiB ActivityThread pthread

The actual frozen API implementation is [here](src/child_main_after_stock.cpp). It is copied into this repository; a branch name is provenance, not the delivery location. Byte identities are recorded in [provenance.json](provenance.json).

[Executable build entry](build.py) and [dependency/build instructions](BUILD.md) distinguish API-unit compilation from complete runtime/boot-image reproduction. No device was touched and the original frozen registry was not changed.

Remaining boundaries:

- Provider dependency sources/headers and original link objects live in the SHA-pinned external generation archives, not fully in this API-unit bundle.
- The registered benchmark source path was inaccurate; build-provider.sh in that directory compiles the baseline unit, not the frozen candidate.
- Relocating source/debug paths can change exact output bytes; build.py reports and rejects a different frozen SHA.

[License notices](LICENSE-NOTICE.md) are retained without assigning a new license.
