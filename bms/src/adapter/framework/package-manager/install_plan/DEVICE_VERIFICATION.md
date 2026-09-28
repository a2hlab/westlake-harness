# install_plan — 02d 合并 + ARM64 device_verified 记录

> 来源：`02d.APK_Flow/L03.install-package/work/`（HP-2 host oracle，codex headless 挑刺门 4 轮 FAIL→FAIL→FAIL→PASS）。
> 本文件记录合并进 `02.unity.cardwords/adapter/framework/package-manager/install_plan/` 后，
> 第一次针对 OH arm64 (musl) 交叉编译 + 5EAB5 真机执行的结果。此前 HANDOFF.md 明确标注
> "ARM64 installer producer 实际可编译" 与 "5eab 真机 User Story 3" 均为 Not Proven；本轮把
> 两者都推进到 device_verified（仅限 judgment-logic 本身，不含 BMS/apk_installer.cpp 生产集成，见下）。

## 环境
- 交叉编译：Gz02（`ssh gz02`），OH 源码树 `/data/source/oh-p7885-wukong100`（wukong100 arm64 平台树），
  clang15（`prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang`）。
- 设备：D600-B `5eab586000000000000000001123012c`（HDC `/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc`）。

## 编译命令（`--target=aarch64-linux-ohos`）
```bash
CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
SR=$OH/out/wukong100/obj/third_party/musl/usr
ML=$SR/lib/aarch64-linux-ohos
BUILTINS=$(ls $OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/*/lib/aarch64-linux-ohos/libclang_rt.builtins.a | head -1)
"$CC" --target=aarch64-linux-ohos --sysroot="$SR" -B"$ML" -L"$ML" -std=c11 -D_GNU_SOURCE -O2 \
  -I"$SR/include/aarch64-linux-ohos" -I install_plan/include -I install_plan/tests/host \
  install_plan/src/install_plan.c install_plan/src/sha256.c \
  install_plan/tests/host/{fixtures_us1,fixtures_us2,fixtures,install_plan_host_test,test_us1,test_us2}.c \
  "$BUILTINS" -o install_plan_arm64_test
```

## 真机执行结果
```
$ HP2_STAGING_BASE=/data/local/tmp/hp2_staging /data/local/tmp/install_plan_arm64_test
HP-2 install-plan host oracle: 133 checks, 0 failures
EXIT_CODE=0
```
- staging 目录执行后 zero-residue（`ls /data/local/tmp/hp2_staging/` 只剩 `.`/`..`）。
- 已清理设备上的测试二进制与本轮安装的 APK，未残留。

## 交叉编译/真机跑第一次暴露、host 从未暴露的 3 处真问题（已修复，非重跑同一逻辑）
1. **`install_plan.h`：`PATH_MAX` 在 musl `<limits.h>` 里被 `_POSIX_C_SOURCE`/`_XOPEN_SOURCE`/
   `_GNU_SOURCE`/`_BSD_SOURCE` 中至少一个宏门控，纯 `-std=c11` 不可见**（host 的 Apple libc
   无条件暴露，掩盖了这个问题）。修复：`#ifndef PATH_MAX #define PATH_MAX 4096 #endif` 兜底。
2. **`install_plan.c`：调用 `mkdtemp()` 但只 `#include <unistd.h>`，未 `#include <stdlib.h>`**
   （macOS 的 `<unistd.h>` 透传声明掩盖了这个缺失）。修复：补 `#include <stdlib.h>`。
3. **`execute_staging()` 硬编码 `/tmp/hp2-install-plan-staging.XXXXXX`**：5EAB5 生产设备 `/`
   （含 `/tmp`）只读挂载，`mkdtemp()` fail-closed 返回 `rc=-1`，这本身符合设计（fail closed，
   不发布）；但 `test_us1.c` 的 `run_us1_tests()` 没检查这个 `rc`，继续用未初始化的
   `state.final_dir` 读回文件，`read_all()` 失败返回 `(size_t)-1`，被当长度传进
   `sha256(readback, (size_t)-1, ...)` → 越界读 → **SIGSEGV（真机 crash，非 host 可见）**。
   修复两处：①`execute_staging()` 的 staging 根目录改为 `HP2_STAGING_BASE` 环境变量可覆盖
   （默认仍是 `/tmp`，host 行为字节级不变，`133 checks/0 failures` 保持）；②`test_us1.c` 在
   `rc != 0` 时提前 return，不再级联进未定义状态。

## 仍未证明（Not Proven，本轮范围之外）
- **生产集成**：`install_plan.c`/`sha256.c` 仍是独立 judgment-logic 模型，尚未接入
  `framework/package-manager/jni/apk_installer.cpp` / `apk_manifest_parser.cpp` 的真实
  BMS/installd 安装流程（`BUILD.gn` 未把它们加进 `apk_installer` target）。这是下一轮工作，
  不在本次"合并+编译+真机跑通 judgment oracle"范围内。
- **`bm install -p` 端到端**：本轮验证的是 judgment 逻辑本身在真机 musl/arm64 上的正确性，
  不是通过真实 `bm install` 走完整 BMS 安装流程。
