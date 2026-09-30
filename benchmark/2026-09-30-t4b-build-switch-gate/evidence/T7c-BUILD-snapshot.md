# T7c BUILD snapshot (for t4b gate; full record in knowledge/toolchains/art-r155/BUILD.md §T7)

## T7c(T7 镜像用 T3c dex2oat64 重出,2026-10-01 00:30,oc-t4)

同一版 adapter-mainline-stubs.jar(366acc276a39e4fc17…,tagsoup Parser + cc-t3 4 个 boot-api 桩),
其余 8 jar 与 T5c 相同;dex2oat64 = T3c ae865ddd6a7e4b25(补丁 #22,显式挂起轮询)。
oatdump 抽查 isOHEnvironment() 入口仍为显式挂起轮询(sub x16,sp,#0x2000 + ldr wzr,[x16] +
ldr w16,[tr] + tst #0x7,code_offset 0x4c9f0,size 316,与 v3c/T5c 同型)。
rb 门 PASS(kv concurrent-copying=false)。与 T5c 差异件:boot-adapter-mainline-stubs.{art,oat,vdex}
(jar 内容变了,预期)+ 其余 8 jar 的 .oat/.art 与 boot.{art,oat}(嵌 cmdline 路径串,预期);
全部 9 个 .vdex 除 adapter-mainline-stubs 外逐字节同。

构建环境(6 项,同 T3b/T3c):

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
    "boot_oat_sha256": "3a2737cd4430f2369807fd1db4aad1ffa0f00bc2a2efa4ae76e26079d204b6f4"
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
