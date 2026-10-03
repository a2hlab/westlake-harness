# U16 frozen compiler environment binding

This is a derived output binding, not a newly rebuilt compiler. The original frozen compiler BUILD environment comes from $WORKSPACES/westlake-harness/knowledge/toolchains/art-r155/BUILD.md sha256=c2b9a506bd2e73ceaa966eedebe73329e876a795fb21b8bf4408302a5799f521.
Both live logs verify dex2oat ae865ddd and driver14b1; hostlibs match the frozen handoff. Only boot_oat_sha256 is rebound to the actual new run1 output; libart and environment are unchanged.

```t4b-build-json
{
  "schema": 1,
  "evidence_kind": "build_receipt",
  "artifacts": {
    "libart_sha256": "59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f",
    "boot_oat_sha256": "b9022366dabd285fb85e7344127a9f9614885ccca2d8d94ca4ca3c2cfed03157"
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
