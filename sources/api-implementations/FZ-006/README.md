# FZ-006 — Vibrator-manager fetcher with initialized lock

The actual frozen API implementation is [here](src/VibratorFetcher.java). It is copied into this repository; a branch name is provenance, not the delivery location. Byte identities are recorded in [provenance.json](provenance.json).

[Executable build entry](build.sh) and [dependency/build instructions](BUILD.md) distinguish API-unit compilation from complete runtime/boot-image reproduction. No device was touched and the original frozen registry was not changed.

Remaining boundaries:

- The complete historical J7b multi-fix JAR requires additional pinned source and binary inputs listed in its original build result.
- Project-specific Java helper has no explicit SPDX/license header in the original source; no new license is invented.

[License notices](LICENSE-NOTICE.md) are retained without assigning a new license.
