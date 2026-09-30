# c-route-dex2oat-108 r12(asm_defines 重生成版)

OC-T4 黑板 #91 Option A(asm 常量对齐 108)。2026-09-30。本文更新 commit 060f5024 的记录。

## r12 变更(相对 r4-r11)

run3 上板死于 `thread_arm64.cc:28 Check failed: 0x90 == CardTableOffset<k64>()(…=152)`——yao 手写 A15 `asm_defines.h` 与 108 Thread 布局差。修法 = 上游生成器重生成:

1. `asmgen/gen3.cc`(aarch64 静态,qemu-aarch64-static 跑)dump 108 真值:CARD_TABLE **0x98**、EXCEPTION **0xa0**、SELF **0xe0**、IS_GC_MARKING **0x24**(FLAGS/THIN_LOCK_ID/TID 不变)。
2. 编 108 自带 `tools/cpp-define-generator/asm_defines.cc` → `.s`(2,449 行/188 标记;需补 `-DART_DEFAULT_GC_TYPE_IS_CMS`、5 个 `-DART_STACK_OVERFLOW_GAP_*`、jni/tinyxml2 include),`make_header.py` 提取 → `stubs108/asm_defines.h`(188 defines,真 108 值)。
3. 强制重汇 asm 三件(`quick/jni_entrypoints_arm64.o`、`memcmp16_arm64.o`)+ `thread_arm64.o`,r12 重链:**0 FAIL**。

除 4 个 THREAD 常量外,全头 diff 另见 ART_METHOD/COMPACT_CODE_ITEM 等约 40+ 处 A15→108 差异(完整 diff 在 hw248 可复跑)。

## 哈希与位置

| 文件 | sha256(前 16) |
|---|---|
| `dex2oat`(r12) | `724b4bd1e458b9d9` |
| `stubs108/asm_defines.h` | `3b63c7df6217948c` |

hw248 `/home/alvin/c-route-dex2oat-108/`(142M:源+patches+stubs108+Makefile+libz.a+fmtlib-vm+asmgen[.s/gen3.cc]+r4/r12 日志);构建树 `/home/yao/c-route-dex2oat/`(build108 对象,可增量)。产物 `art\n108\0`×3/`art\n118\0`×0。

## 待办

5cd 空闲(约 10:10 后,61b 有 cx-t0/cc-t3 排队按黑板顺序)→ 取锁上板 r12 → 原 5-jar 重编 9 段 → 拉回逐段比 checksum;通过才做 tagsoup 1.2.1 版。
