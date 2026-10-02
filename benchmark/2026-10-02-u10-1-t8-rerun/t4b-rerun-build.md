# Image-only T8 rerun switch binding

Uses the FZ-005 frozen RB-off baker ae865ddd; R155 libart is byte-identical 59e1bb45. Flags are inherited from the archived T3b build receipt in knowledge/toolchains/art-r155/BUILD.md; only boot_oat artifact binding is updated to the new bake, proven by the actual log and header. This does not assert a new libart build.

```t4b-build-json
{
  "schema": 1,
  "evidence_kind": "build_receipt",
  "artifacts": {
    "libart_sha256": "59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f",
    "boot_oat_sha256": "4ba08485100228609a0d2acb8ea9db51ef7376c95517896362c0b7bf33a2a0cb"
  },
  "environment": {
    "ART_USE_READ_BARRIER": "false",
    "ART_DEFAULT_GC_TYPE": "CMS",
    "ART_USE_GENERATIONAL_CC": "false",
    "ART_HEAP_POISONING": "false",
    "ART_TEST_DEBUG_GC": "false",
    "ALLOW_MISSING_DEPENDENCIES": "true"
  },
  "native_debug_build": false
}
```
