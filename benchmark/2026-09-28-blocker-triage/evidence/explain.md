# Contract Review: T0 修扫量取证并重扫未亮 app

## Intent

2026-09-27 的扫量没有留下任何可诊断数据:每个 app 的 `hilog-crash.txt` 都是 223 字节,内容是 grep 命令在 hilog 里匹配到它自己的 HDC_LOG 行;child stderr 所在的运行时目录在收尾清理时被删掉;旧 `sweep_app.sh` 还会复用上一轮截图、凭日志直接写 LIT。本任务修采集,在清理前把每个 app 本轮的观测取回,然后重扫 43 个未亮 app 与 13 个 LIT 对照组。纯 Java 的 7 个未亮 app 在静态缺口图里找不到区分性缺口,所以采集同时覆盖 native 链接错误与 Java 主线程状态。本任务交付观测与候选 blocker,不强行命名根因。

## Decisions

- 基座:所有 OH 板统一 stage 与 5ea34a45 `framework-2`(a2hlab-framework-cab462ff)同一构建的 framework;probe 参数模板取自 `benchmark/2026-09-27-app-breadth-sweep/sweep_config.5ea34a45.sh`,按板替换序列号与 framework report
- native 构建走 `westlake-inputs/tools/dockbuild.sh`(OrbStack amd64 docker + 锁定 OH 工具链,与 VM 逐字节相同);Mac 本机 DevEco clang 只用于快速迭代
- 框架层修复走 smali 外科补丁 `adapter-runtime-bcp.jar`,用 westlake 自带 host dex2oat(oat 247)重建 boot image,不依赖 `/home/dspfac/bridge-build`
- native 缺符号用薄 stub 或 shim 导出补,经 `app-input.json` 的 `native_libraries` 带入 staging,不改 APK
- 证据落 `benchmark/<YYYY-MM-DD>-<主题>/`:英文 README + `results.json` + 签认过的截图(`git add -f`)
- `tools/spec-checks/` 的每个 Rust 测试调用生产脚本或生产分类器读本轮证据,并配一个负控:故意破坏真实逻辑后该测试必须失败
- 截图前执行 `power-shell timeout -o 3600000` 与 `uinput -T -m 600 1600 600 400 200`,防熄屏重锁抓到黑帧
- hook、拦截器、二进制补丁类任务派 Claude agent 执行,不派 codex
- 43 个未亮 app 的 key 固定成清单,每个记 package、apk_sha256、launch Activity;每次 attempt 都保留,有效记录的选择规则写进 README
- 截图写到每轮唯一路径 `<run_id>/<serial>/<key>.jpeg`,确认本轮 `snapshot_display` 成功且文件新于本次启动,失败记 `shot=failed`;删除旧 `sweep_app.sh` 凭 alive 与渲染日志写 LIT 的分支
- child stderr 按本轮 device-report 的 child pid 与 runtime 精确定位 `<runtime>/private-tmp/adapter_child_<pid>.stderr`,区分 `missing` / `read_error` / `empty`,记原始与过滤 `TOUCH21-POLL` 后的行数
- hilog 过滤用字符类写法 `[F]atal signal|[S]IGSEGV|[c]annot locate symbol|[E]rror relocating|[s]ymbol not found|[U]nsatisfiedLink|[F]ATAL EXCEPTION`,丢弃含 `HDC_LOG` 的行,并只保留本轮 child pid 且在本次启动之后的行
- 先用最小实验确认 ART `SIGQUIT` 线程栈的真实落点与完成标志;对所有未确认可用且仍存活的 app 间隔 5 s 各取一次栈,识别 `MessageQueue.next`/`Looper.loop` 空等,超时、进程已退出或无栈都记 `capture-failed`
- `render_node` 取自 `hidumper -s RenderService`,绑定本轮 pid 与窗口并保存原始片段,只作观测字段,不据此跳过取栈
- `triage.json` 分列 `observations`、`candidate_blocker`、`confirmed`;`candidate_blocker.class` 取值 `native-symbol` / `java-exception` / `null-service` / `main-thread-blocked` / `native-crash` / `exited-normally` / `render-stalled` / `capture-failed` / `no-marker`;只有同轮因果证据才进 `confirmed`
- 本轮输出放 VM `~/a2hlab/ws/out-appsweep-t0-<run_id>/`;`~/a2hlab/app-inputs/*` 只读
- 板写命令前 `board_note.sh lock`;61b 的 broker、keeper、自启在基座准备时停用并记清单

## Boundaries

**Allowed:**
- benchmark/2026-09-27-app-breadth-sweep/scripts/**
- benchmark/*-blocker-triage/**
- tools/spec-checks/**

**Forbidden:**
- 不修改运行时、framework、APK
- 不在白名单外的序列号上执行任何命令
- 不对当前车道未持锁的板下写命令

**Out of Scope:**
- 修复任何 blocker
- 商业 co-* app 的首次扫量
- 深挖板与板之间结果不一致的根因(只记录现象)

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 14 | 2 | 0 | 12 | 0 | 14.3% |

- ⏭️ 未亮 app 取得本轮观测
  - test: `t0_blocked_apps_have_observations`
- ⏭️ 纯 Java 未亮 app 取得两次主线程栈
  - test: `t0_pure_jvm_apps_have_main_stack`
- ⏭️ 取栈失败时显式记 capture-failed
  - test: `t0_stack_timeout_marked_capture_failed`
- ✅ hilog 只保留本轮 child 的真实异常
  - test: `t0_hilog_keeps_own_pid_crash_only`
- ⏭️ stderr 按本轮 pid 定位并区分缺失与空
  - test: `t0_stderr_located_by_pid`
- ⏭️ 快照失败时拒绝判亮
  - test: `t0_stale_screenshot_rejected`
- ⏭️ LIT 对照组无回退且哨兵仍未亮
  - test: `t0_lit_control_set_unchanged`
- ⏭️ 基座不一致的板结果被拒绝
  - test: `t0_board_without_full_lit_control_excluded`
- ⏭️ 争锁失败时零写命令
  - test: `t0_lock_contention_no_writes`
- ⏭️ 板子中途掉线时终止该分片
  - test: `t0_midrun_detach_stops_shard`
- ⏭️ 跨板汇总每个 app 恰好一条有效记录
  - test: `t0_merged_triage_one_record_per_app`
- ⏭️ 采集不写共享输入与其他车道目录
  - test: `t0_isolated_out_root`
- ⏭️ 清理拒绝删除头条目录
  - test: `t0_cleanup_exempts_toutiao_dirs`
- ✅ 负控使检查器失败
  - test: `t0_negative_controls_fail`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | 未亮 app 取得本轮观测 | t0_blocked_apps_have_observations | missing | skip | computational |
| — | 纯 Java 未亮 app 取得两次主线程栈 | t0_pure_jvm_apps_have_main_stack | missing | skip | computational |
| — | 取栈失败时显式记 capture-failed | t0_stack_timeout_marked_capture_failed | missing | skip | computational |
| — | hilog 只保留本轮 child 的真实异常 | t0_hilog_keeps_own_pid_crash_only | found | pass | computational |
| — | stderr 按本轮 pid 定位并区分缺失与空 | t0_stderr_located_by_pid | missing | skip | computational |
| — | 快照失败时拒绝判亮 | t0_stale_screenshot_rejected | missing | skip | computational |
| — | LIT 对照组无回退且哨兵仍未亮 | t0_lit_control_set_unchanged | missing | skip | computational |
| — | 基座不一致的板结果被拒绝 | t0_board_without_full_lit_control_excluded | missing | skip | computational |
| — | 争锁失败时零写命令 | t0_lock_contention_no_writes | missing | skip | computational |
| — | 板子中途掉线时终止该分片 | t0_midrun_detach_stops_shard | missing | skip | computational |
| — | 跨板汇总每个 app 恰好一条有效记录 | t0_merged_triage_one_record_per_app | missing | skip | computational |
| — | 采集不写共享输入与其他车道目录 | t0_isolated_out_root | missing | skip | computational |
| — | 清理拒绝删除头条目录 | t0_cleanup_exempts_toutiao_dirs | missing | skip | computational |
| — | 负控使检查器失败 | t0_negative_controls_fail | found | pass | computational |
