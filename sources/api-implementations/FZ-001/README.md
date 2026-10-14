# FZ-001 — Background launch permission and APK launcher selection

The actual frozen API implementation is [here](archive-source/base_bundle_installer.cpp). It is copied into this repository; a branch name is provenance, not the delivery location. Byte identities are recorded in [provenance.json](provenance.json).

[Executable build entry](build.sh) and [dependency/build instructions](BUILD.md) distinguish API-unit compilation from complete runtime/boot-image reproduction. No device was touched and the original frozen registry was not changed.

Remaining boundaries:

- Complete OH6.1 B79/B89 kit, its generated headers and link libraries are not vendored here; their original archive identities are retained.
- The executable entry builds the archived installer sources; the BMS half uses the original ninja recipe in a separately restored scratch kit. No new native build is claimed.

[License notices](LICENSE-NOTICE.md) are retained without assigning a new license.
