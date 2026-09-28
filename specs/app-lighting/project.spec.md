spec: project
name: "横向点亮更多 app"
tags: [westlake, app-breadth]
---

## 意图

在 DAYU600 / OpenHarmony 6.1.0.31 的 Westlake 运行时上,把点亮到首个可用界面的 distinct app 数从 2026-09-27 扫量的 13 个往上推。做法是先给每个未亮 app 取到具名 blocker,再按「一个修复覆盖几个 app」给修复族排序、逐族修,每族修完都在同一构建上对 13 个已亮 app 做回归。2026-09-28 第一轮修订采认了 外环(codex) 对抗审查的意见。

## 约束

- 点亮判据只认本轮 `snapshot_display` 截图(后缀 `.jpeg`)经外环读图签认;`alive=yes`、`state=READY`、`render_node=true`、脚本打印 PASS 都不算点亮,任何脚本不得写出 LIT 判定
- 每张截图绑定 serial、run_id、app key、package、apk_sha256、child pid、采集时间、framework 与 boot image 哈希;外环签认记录截图 sha256 与判据一句话,未签认的一律记 `pending_review`
- 上板实验只在白名单设备上执行:`5ea34a4500000000000000001123012c`、`5cd1e3dd00000000000000000923012c`、`61b0657200000000000000000324012c` 与安卓参考机 `N100CU025C18D000128`;白名单外的序列号一律拒绝
- 对一块板下任何写命令之前先 `board_note.sh lock` 取得该 serial 的 flock 锁,退出码 75 时零写命令;用完 `board_note.sh unlock`
- 车道之间隔离:每车道每次运行使用独立的 OUT_ROOT 与 app-input 副本,`~/a2hlab/app-inputs/*` 与共享构建产物只读
- 一块板参与判定前,记录该板完整部署清单与实际哈希,并在该板上重扫 13 个 LIT 对照组与已知失败哨兵 markor;13 个全亮且 markor 仍未亮才算基座一致,运行中基座变动立即使该板本轮结果作废
- 每个修复族交付前,13 个 LIT app 在**最终修复构建**上重扫,13 个全部仍判为 LIT
- 交付状态分三档:`lit`(外环读图签认)、`advanced`(原失败调用现在成功的正证据 + 新的具名 blocker)、`no-change`;只有 `lit` 计入点亮数
- 车道每个里程碑或至少每 20 分钟用 `board_note.sh progress` 写一条 PROGRESS
- 板上计数进程不用裸 `pgrep -f`,用 `pgrep -f '[x]yz'` 或 `scripts/lab/stop_by_pattern.sh`
- 不提交密码、服务器账号、个人数据;不推送远端
- 提交信息不带 Claude 署名行

## 已定决策

- 基座:所有 OH 板统一 stage 与 5ea34a45 `framework-2`(a2hlab-framework-cab462ff)同一构建的 framework;probe 参数模板取自 `benchmark/2026-09-27-app-breadth-sweep/sweep_config.5ea34a45.sh`,按板替换序列号与 framework report
- native 构建走 `westlake-inputs/tools/dockbuild.sh`(OrbStack amd64 docker + 锁定 OH 工具链,与 VM 逐字节相同);Mac 本机 DevEco clang 只用于快速迭代
- 框架层修复走 smali 外科补丁 `adapter-runtime-bcp.jar`,用 westlake 自带 host dex2oat(oat 247)重建 boot image,不依赖 `/home/dspfac/bridge-build`
- native 缺符号用薄 stub 或 shim 导出补,经 `app-input.json` 的 `native_libraries` 带入 staging,不改 APK
- 证据落 `benchmark/<YYYY-MM-DD>-<主题>/`:英文 README + `results.json` + 签认过的截图(`git add -f`)
- `tools/spec-checks/` 的每个 Rust 测试调用生产脚本或生产分类器读本轮证据,并配一个负控:故意破坏真实逻辑后该测试必须失败
- 截图前执行 `power-shell timeout -o 3600000` 与 `uinput -T -m 600 1600 600 400 200`,防熄屏重锁抓到黑帧
- hook、拦截器、二进制补丁类任务派 Claude agent 执行,不派 codex
