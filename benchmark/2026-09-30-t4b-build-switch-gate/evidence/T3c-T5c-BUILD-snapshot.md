# T3c/T5c BUILD snapshot (for t4b gate; full record in knowledge/toolchains/art-r155/BUILD.md §T3c)

## T3c(补丁 #22:arm64 关隐式挂起检查,2026-10-01 00:20,oc-t4)

补丁 22-dex2oat__implicit-suspend-checks-off.patch:dex2oat.cc:859 arm64 分支
implicit_suspend_checks_ true→false(只动挂起检查)。证据:oatdump 对照(OATDUMP-DIFF.md)
isOHEnvironment() 入口 v3c=显式挂起检查 vs T5b=隐式 ldr x21,[x21];Westlake 先例
aosp-art-15 dex2oat.cc(source-excerpts.txt:886-891)。增量 m -j32 dex2oat 绿(04:19,t3c-build.log)。
T5c 镜像 27/27,vdex 9/9,kv concurrent-copying=false;oatdump 核 isOHEnvironment 入口已变显式
(sub x16,sp,#0x2000 + ldr wzr,[x16] + ldr w16,[tr]+tst #0x7,CodeSize 回 316)。

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
    "boot_oat_sha256": "0e7dc0e457463b3d991e589c727e0f6bae19e11eedb6ac6fb7ee28ffcdde21b3"
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
