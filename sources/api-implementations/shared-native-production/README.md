# Shared native production recovery

The nearby `089bebe7` bridge build log is not the signed `8ab85446` producer.
Likewise the `0d7b9712` runtime build is not `9ccf64f8` or its `adc125f4`
49-byte derivative. Neither relationship is repaired by copying a similarly
named source file. Historical freezes, signed output identities and device
acceptance remain unchanged.

## Delivered implementation and dependencies

- `FZ-001/archive-source/` contains the final archived BMS implementation and
  installer implementation, not the earlier BMS source revision. The permission
  projection header, own-launcher resolver and original patches are included.
- `FZ-002/src/` contains the real dedicated pthread implementation and its
  declaration headers. `build_provider.py` executes the preserved compiler/link
  argument vectors against the exact dependency archives.
- `FZ-003/src/` contains the actual ParcelFileDescriptor implementation;
  `build_asset_fd.sh` invokes the retained original runtime recipe. Its complete
  original dependency generation is still not newly restored or built here.
- `related-source/` preserves 92 existing C/C++ implementation/recipe witnesses
  from the named local source family. These are **not certified original
  producing sources** for signed bridge8ab or libandroid9cc/ADC. Missing upstream
  GLES/asset-manager inputs and the exact historical source/link binding remain
  explicit, so the related recipes are not a reproducible signed build claim.

`source-index.json` pins all 247 source/evidence members. Eleven original files
have CRLF bytes; the readable files use LF and `raw-source-bytes/` preserves
their exact original bytes. `materialize.py` verifies both representations and
restores the original bytes in a new scratch directory. This is not a source
patch. The source index distinguishes current related witnesses from delivered
frozen implementation inputs.

## Execute without author-specific filesystem paths

Validate or fetch the locked dependencies:

```sh
python3 acquire.py --id FZ002_GENERATION --archive "$INPUTS/build-inputs.tar.gz" --receipt-dir "$NEW_RECEIPTS/generation"
HW248_HOST="$CONFIGURED_HOST" HW248_HOME="$PERSISTENT_HOME" python3 acquire.py --id FZ002_PLATFORM_LINK --archive "$INPUTS/external-link-inputs.tar.gz" --receipt-dir "$NEW_RECEIPTS/platform" --fetch
```

The archive locations and complete SHA256 pins are in `dependencies.lock.json`.
Downloads are optional and explicit; wrong bytes are refused, and partial
downloads are preserved. The FZ001 source and OH kit are acquired the same way
using IDs `FZ001_SOURCE` and `FZ001_OH_KIT`. No binary is silently substituted.

On hw248 only, from a newly staged copy of this directory:

```sh
LAB_HOME="$PERSISTENT_HOME" bash execute-hw248.sh "$PERSISTENT_HOME/native-closeout-attempt-$(date -u +%Y%m%dT%H%M%SZ)-$$"
```

The entry restores dependencies into a fresh private generation, stages only
the exact frozen BIGSTACK translation unit, then executes compile and link.
Every step writes distinct stdout, stderr and rc files. Compiler/linker/libc
pins are checked first. Output SHA `0509fe23...` equality returns 0; a successfully
built different object returns 3, not a historical exact-production claim.
No a2hlab build, device command, signed replacement or f28 rebuild is included.

The original archive contains 33 auxiliary headers outside its generation root.
`archive-layout.lock.json` enumerates their exact suffixes and hashes; unknown
roots, unknown auxiliary members, traversal and external links are refused.
Two old `v1-tests` links refer to unavailable B67 test sources. They are retained
as explicitly unresolved, unused test dependencies, not silently rebound to a
different revision. The restore receipt therefore does not assert complete
whole-generation reproduction.

For the installer, use the newly restored original OH kit and AOSP headers:

```sh
python3 build_installer.py --oh-root "$OH_INPUTS" --aosp-root "$AOSP_INPUTS" --out "$NEW_BUILD"
```

It materializes the actual installer sources, checks the compiler pin, rejects
partial legacy compilation and compares the stripped output with the frozen
installer SHA. This does not newly reproduce the entire libbms ninja graph.
For FZ003, `bash build_asset_fd.sh --help` describes the original dependency
variables. A missing full asset-fd generation must not be replaced with the
already reproduced U13/f28 generation and called a historical FZ003 build.

## Remaining historical bindings

Signed bridge:
`8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e`.
Baseline libandroid:
`9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db`.
ADC:
`adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130`.

ADC binary replay is already closed by the separately retained 387553-byte
archive at configured hw248 root `westlake-boat-v2-window2-20261013T1143/adc-exact-reuse.tar.gz`,
SHA `2824b0504ec6a9362e7c15bf9e57fe04238adad4d18c5b6824d81e301fa9b96d`.
That archive is not a C++ production-source closure. The source manifest,
exact original argv and rc0 producer-to-target relationship for bridge8ab and
libandroid9cc remain unproven. New executions, failures and their raw locations
are reported separately in the companion benchmark; source presence is not
historical byte equivalence.
