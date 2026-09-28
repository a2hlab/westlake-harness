# B2 kit+dockbuild 本地复现编译与部署(#40,oc-t4)

WIP f677d817(oc-t0)曾在 hw248 编出 29/29 全绿并部署 c9f1d01a;本文件记录条目 #40 要求的
**本地 kit+dockbuild 复现链**,产物已部署 5cd 并验证。

## ① 编译(14 轮迭代,最终全绿)

- 入口:`dockbuild.sh run` + `OH_ROOT=~/orca/workspaces/oh61-bms-kit` + `build/build_adapter.sh --no-apply --target=libapk_installer.so`
- **build14 = Compiled: 30/30,Linking OK,1.3M**(raw sha256 `b938d2e5…`)
- 修复的墙(逐个):
  1. wire 代缺源 5+1 个(`game_install_plan_wire` 等)与 6 个配套头、`lodepng.cpp/.h`、`package_transaction` 2 源 2 头——全部从 hw248 `full-src` 拉回
  2. **代际混杂**:本地 jni 是 v1 代(c_entry 路径版 API),与拉回的 wire 头冲突 → 把 hw248 的 `framework/package-manager` 全子树自洽同步(jni/manifest_facts/application_attributes/…;其 `arsc_resolver.cpp` 带 REFERENCE 标签修复)
  3. SRCS 对齐 hw248 全绿清单:补 `game_install_plan_v1.cpp`(链接缺 `GameInstallPlanV1_Validate` 的根因)
  4. `directory_ex` ABI 命名空间墙:kit `libutils.z.so` 只导出 `std::__h` 版 `OHOS::ForceCreateDirectory/ForceRemoveDirectory`,SDK libcxx 编译对象引用 `std::__n1` → 自包含 shim(`jni/directory_ex.h` 声明 + `jni/directory_ex_shim.cpp` 强定义,POSIX mkdir -p / 递归 rmdir,无 std::filesystem)
  5. isinf 家族重声明冲突:`-DWESTLAKE_LIBCXX_HAS_NATIVE_COMPAT=1`(libcxx_compat.h 注释明示的构建覆盖通道)
  6. `package_transaction.cpp` → `_v1` 文件名漂移修正
- patchelf:`libz.so → libshared_libz.z.so`(板 chipset-sdk-sp 有,127056B);改后 sha `80d66c6e…`(staging-kit/libapk_installer.kit-build.so)
- 日志:`evidence/kit-build-2026*.log`(build5 起逐轮保留)

## ② 部署 5cd(00:41)

- 备份:`/data/local/tmp/b2-kit-backup/{sys64,platformsdk}.so`(现库实为 c9f1d01a,条目写的 3de38f09 是 #25 时代旧值)
- 换库:rw remount → 双路径 cp → chmod/chown → ro remount
- foundation 重启:pid 25979
- **四处哈希核验一致**(80d66c6e):/system/lib64、platformsdk、/proc/25979/root 下两份
- 已知差异:kit 版 NEEDED `libc++_shared.so`(hw248 版是 `libc++.so`);板上该库存在(1278536B)且导出 1893 个 `__n1` 符号,kit 版 76 个 `__n1` 引用可解析

## ③ 四 app 重装(00:42)

bm uninstall → 同 APK 重装 → bm dump label:`Wikipedia` / `Markor` / `Aegis` / `Termux`(一手输出存 apps/<key>-label.txt)。

## ④ 桌面截图

`desktop.jpeg` sha256 `f6fa2c03…`(VM board/b2-kit-deploy-20260929T0045/),外环读图。

## ⑤ hilog 证据与回退场景

- 采集自 00:43 markor 重装:`OH_ArscResolver: ResolveResourceIdToString: 0x7f1100a1 is a reference -> 0x7f1100a2 (hop 1)` + `ResolveResourceIdToString: 0x7f1100a1 -> Markor (1 candidates)` + `ApkInstaller: ResolveLabelResId: @string 0x7f1100a1 -> Markor`(label-hilog.txt)
- 回退场景(b2_unresolvable_label_falls_back_to_package):本次四 app 无解析失败,未自然触发;历史证据=WIP results.json 的 previous_attempt(3de38f09 代 wikipedia/markor 解析失败退包名)。**partially**。

## R2

编译/部署/哈希核验/label/REFERENCE-hop hilog = **verified**(原始文件);回退场景 = **partially**(历史证据,本次未触发);桌面显示 = 外环读图。
