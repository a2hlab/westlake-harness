spec: project
name: "BMS 路线抄录收尾"
tags: [bms, oh61, copy]
---

## 意图

2026-09-28 用户决定改走 BMS 路线:Android APK 经补丁版 BMS 安装(`bm install -p`)、从桌面图标拉起,代码照搬 00.Workspace `games/boatattack-repro`,已入库 `bms/`。HelloWorld 与 ZigZag 已在三块板上亮,但我们的 app 批量安装后 0/62 亮、桌面名全是 "Hello World"、图标取的是低分辨率位图。本契约族把安装与拉起的三处缺口补齐(沙箱准备、名字、图标),然后用 BMS 路线重跑横向点亮。

## 约束

- 系统保持 OpenHarmony 6.1.0.31,不刷机;运行代用 `bms/` 复现器部署的那一份
- 修法优先照搬 `bms/` 与 00.Workspace 已有的代码与产物,只在找不到现成实现时才新写
- 上板前 `board_note.sh lock`;只对条目写明的独占板下写命令
- 点亮判据只认外环读图签认的截图;`bm install` 成功、进程存活、`bm dump` 可查都不算点亮
- 补丁版 BMS 生效的判据:`/proc/<foundation pid>/root` 下实际加载的库哈希与 maps,不看全局库哈希
- 只在本地 commit,不推送;APK、HAP、`.so`、payload 不入 git

## 已定决策

- 名字与图标都在 `bms/src/adapter/framework/package-manager/jni/apk_installer.cpp` 合成资源 HAP 的流程里修;两项由同一车道先后做,避免同文件冲突
- native 库用 `westlake-inputs/tools/dockbuild.sh` 按锁定工具链为 OH 6.1 编;换 installer 的步骤必须带回滚
- 沙箱准备照搬 HelloWorld restore 与 ZigZag `prepare_sandbox` 的逻辑,参数化为包名与 uid
