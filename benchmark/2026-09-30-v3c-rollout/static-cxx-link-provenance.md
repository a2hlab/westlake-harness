# TLS 39c2cfe9 + gapfill d1a1961d 构建来源 (Build provenance)（2026-09-30, cx-t0 v3c 上板前补）

**目的**：给两件冻结候选的静态 C++ 链接法留持久可复现记录。产物未重编，与 vm-copies 中的 .so 逐字节一致（源码/命令均未改动语义）。

## 产物

| 产物 | SHA16 | vm-copies 路径 |
|---|---|---|
| liboh_tls_boundary.so | `39c2cfe9cb830f08` | `vm-copies/tls-boundary-39c2cfe9/` |
| libwestlake_jni_gapfill.so | `d1a1961d7682a482` | `vm-copies/jni-gapfill-d1a1961d/` |

## 源码（westlake-harness-b4 @ feat/bms-sweep）

| 文件 | 状态 |
|---|---|
| `bms/src/adapter/framework/native-compat/westlake-tls/wl_tls_block.cpp` | §441 原文（verbatim）+ JNI_OnLoad + 第 8 个 native `nativeTlsSelfTestOk`；commit 链 7e511ad0→当前 |
| `.../jni-gapfill/westlake_jni_gapfill.cpp` | commit 56b5295c 原文 |

**无源码 patch**——两步链接纯是**链接命令差异**（同一 .cpp 同一编译 flag），故 provenance 落在 build.sh + 本文件。

## 链接命令（实测两步，静态 C++ 运行时）

两个 build.sh 已更新为实测命令（tls: `bms/.../westlake-tls/build.sh`; gapfill: `benchmark/2026-09-29-westlake-port/jni-gapfill/build.sh`），核心：

```bash
# step 1: compile to .o（tls 为例；gapfill 同构）
clang-15 --target=aarch64-linux-ohos --sysroot=$SYSROOT \
  -fPIC -O2 -std=c++17 -Wall -I. -I$JNI_INC \
  -c -o wl_tls_block.o wl_tls_block.cpp

# step 2: link with EXPLICIT static libc++/libc++abi（clang 的 -static-libstdc++ 在此是 no-op，故显式 -l:）
clang-15 --target=aarch64-linux-ohos --sysroot=$SYSROOT \
  -shared -fPIC \
  -o liboh_tls_boundary.so wl_tls_block.o \
  -L$TOOLCHAIN/llvm/lib/aarch64-linux-ohos -l:libc++.a -l:libc++abi.a \
  -ldl -lpthread        # gapfill 无 -ldl/-lpthread
```

## 输入 SHA（工具链，VM `~/a2hlab/ws/toolchains/ohos-sdk/native`）

| 输入 | SHA16 |
|---|---|
| `llvm/lib/aarch64-linux-ohos/libc++.a` | `52e59afca841c333` |
| `llvm/lib/aarch64-linux-ohos/libc++abi.a` | `c73cf1e47d8ecd42` |
| clang-15 | OHOS (dev) clang 15.0.4 (llvm-project `feef13a36e78b7a2ff3e9e3f180a958f2782be1e`) |

## 为什么这么链（修复历史）

5ea r17d 实测：一步 `-shared` 链接的库里 UND 含 15 个 C++ 符号（`_Znwm`/`_ZdlPv`/`__cxa_*`/`_ZSt9terminatev`），app 域无 C++ 运行时可解析 → `relocating failed: _Znwm`。两步静态链后 UND 仅剩 WEAK `__cxa_finalize`（musl 下无需定义），`DT_NEEDED` 仍只 `libc.so`。

## 验证（复现用）

`llvm-readelf --dyn-syms | grep UND | grep -E '_Z|__cxa'` → 仅 `__cxa_finalize`(WEAK)；`--dynamic | grep NEEDED` → 仅 `libc.so`；`nm -D | grep JNI_OnLoad` → 有。
