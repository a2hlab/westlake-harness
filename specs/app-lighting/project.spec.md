spec: project
name: "横向点亮更多 app"
tags: [westlake, app-breadth]
---

## 意图

在 DAYU600 / OpenHarmony 6.1.0.31 的 Westlake 运行时上,把点亮到首个可用界面的 distinct app 数从 2026-09-27 扫量的 13 个往上推。做法是先给每个未亮 app 取到具名 blocker,再按「一个修复覆盖几个 app」给修复族排序、逐族修,每族修完都在扫量板上对 13 个已亮 app 做回归。

## 约束

- 点亮判据只认 `snapshot_display` 截图(后缀 `.jpeg`)经人读图确认;`alive=yes`、`state=READY`、脚本打印 PASS 都不算点亮
- 上板实验只在白名单三块板上执行:`5ea34a4500000000000000001123012c`、`5cd1e3dd00000000000000000923012c`、`61b0657200000000000000000324012c`(2026-09-28 用户全部放开,演示已结束);白名单外的序列号一律拒绝
- 同一块板同一时刻只跑一个上板任务(板锁);多板并行靠按 app 分片
- 一块板参与判定前,先在该板上重扫 13 个 LIT 对照组,13 个全亮才算基座一致
- 每个修复族交付前,2026-09-27 的 13 个 LIT app 在同一构建上重扫,13 个全部仍判为 LIT
- 板上计数进程不用裸 `pgrep -f`,用 `pgrep -f '[x]yz'` 或 `scripts/lab/stop_by_pattern.sh`
- 不提交密码、服务器账号、个人数据;不推送远端,推送等用户明示
- 提交信息不带 Claude 署名行

## 已定决策

- 基座:三块板统一 stage 与 5ea34a45 `framework-2`(a2hlab-framework-cab462ff)同一构建的 framework;probe 参数模板取自 `benchmark/2026-09-27-app-breadth-sweep/sweep_config.5ea34a45.sh`,按板替换序列号与 framework report
- native 构建走 OrbStack docker(`--platform linux/amd64`)+ 锁定 OH 工具链,见 RUNBOOK §5;Mac 本机 DevEco clang 只用于快速迭代
- 框架层修复走 smali 外科补丁 `adapter-runtime-bcp.jar`,用 westlake 自带 host dex2oat(oat 247)重建 boot image,不依赖 `/home/dspfac/bridge-build`
- native 缺符号用薄 stub 或 shim 导出补,经 `app-input.json` 的 `native_libraries` 带入 staging,不改 APK
- 证据落 `benchmark/<YYYY-MM-DD>-<主题>/`:英文 README + `results.json` + 读图确认过的截图(`git add -f`)
- 截图前执行 `power-shell timeout -o 3600000` 与 `uinput -T -m 600 1600 600 400 200`,防熄屏重锁抓到黑帧
- hook、拦截器、二进制补丁类任务派 Claude agent 执行,不派 codex
