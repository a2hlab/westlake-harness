# T7 BUILD snapshot (for t4b gate; full record in knowledge/toolchains/art-r155/BUILD.md §T7)

## T7(mainline-stubs 合一版镜像,2026-09-30 22:59,oc-t4)

构建环境(6 项,同 T3b):

```sh
export ART_USE_READ_BARRIER=false \
       ART_DEFAULT_GC_TYPE=CMS \
       ART_USE_GENERATIONAL_CC=false \
       ART_HEAP_POISONING=false \
       ART_TEST_DEBUG_GC=false
export ALLOW_MISSING_DEPENDENCIES=true
```

```t4b-build-json
{
  "schema": 1,
  "evidence_kind": "build_receipt",
  "artifacts": {
    "libart_sha256": "59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f",
    "boot_oat_sha256": "4a46e40fa7ffb1d183dc3c08020198b30287da4c96b0f8a4e61585a5593fa711"
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
