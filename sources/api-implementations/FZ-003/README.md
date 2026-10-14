# FZ-003 — Real ParcelFileDescriptor for AssetManager.openFd

The actual frozen API implementation is [here](src/android_util_AssetManager_aosp.cpp). It is copied into this repository; a branch name is provenance, not the delivery location. Byte identities are recorded in [provenance.json](provenance.json).

[Executable build entry](build.sh) and [dependency/build instructions](BUILD.md) distinguish API-unit compilation from complete runtime/boot-image reproduction. No device was touched and the original frozen registry was not changed.

Remaining boundaries:

- The complete AOSP/OH/native runtime link dependency set is not re-vendored by this unit; baseline-objects.json pins existing link objects but is not full upstream source closure.
- The original recipe itself records missing upstream arm64 producer routes. This delivery cannot mark a fresh full-runtime rebuild complete.

[License notices](LICENSE-NOTICE.md) are retained without assigning a new license.
