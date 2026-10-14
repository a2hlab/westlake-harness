# FZ-005 — R155-compatible dex2oat toolchain and boot image generator

The actual frozen API implementation is [here](frozen/series). It is copied into this repository; a branch name is provenance, not the delivery location. Byte identities are recorded in [provenance.json](provenance.json).

[Executable build entry](build.sh) and [dependency/build instructions](BUILD.md) distinguish API-unit compilation from complete runtime/boot-image reproduction. No device was touched and the original frozen registry was not changed.

Remaining boundaries:

- AOSP14 ART base and full OH6.1 trees are locked upstream dependencies, not vendored wholesale.
- Toolchain and input-JAR binaries are external pinned build inputs; no new toolchain build was performed.

[License notices](LICENSE-NOTICE.md) are retained without assigning a new license.
