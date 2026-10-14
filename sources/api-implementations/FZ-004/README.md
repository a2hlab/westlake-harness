# FZ-004 — BouncyCastle JAR verification provider

The actual frozen API implementation is [here](src/JarVerificationProviderFix.java). It is copied into this repository; a branch name is provenance, not the delivery location. Byte identities are recorded in [provenance.json](provenance.json).

[Executable build entry](build.sh) and [dependency/build instructions](BUILD.md) distinguish API-unit compilation from complete runtime/boot-image reproduction. No device was touched and the original frozen registry was not changed.

Remaining boundaries:

- The unit compiles independently, but the complete historical multi-fix runtime JAR requires the original helper set, baseline JAR, D8 and smali inputs from the pinned build receipt.
- Project-specific Java helper has no explicit SPDX/license header in the original source; no new license is invented.

[License notices](LICENSE-NOTICE.md) are retained without assigning a new license.
