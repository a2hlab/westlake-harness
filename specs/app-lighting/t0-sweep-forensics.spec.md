spec: task
name: "T0 修扫量取证并重扫未亮 app"
inherits: project
tags: [forensics, sweep, critical-path]
---

## 意图

2026-09-27 的扫量没有留下任何可诊断数据:每个 app 的 `hilog-crash.txt` 都是 223 字节,内容是 grep 命令在 hilog 里匹配到它自己的 HDC_LOG 行;child stderr 所在的运行时目录在收尾清理时被删掉;旧 `sweep_app.sh` 还会复用上一轮截图、凭日志直接写 LIT。本任务修采集,在清理前把每个 app 本轮的观测取回,然后重扫 43 个未亮 app 与 13 个 LIT 对照组。纯 Java 的 7 个未亮 app 在静态缺口图里找不到区分性缺口,所以采集同时覆盖 native 链接错误与 Java 主线程状态。本任务交付观测与候选 blocker,不强行命名根因。

## 已定决策

- 43 个未亮 app 的 key 固定成清单,每个记 package、apk_sha256、launch Activity;每次 attempt 都保留,有效记录的选择规则写进 README
- 截图写到每轮唯一路径 `<run_id>/<serial>/<key>.jpeg`,确认本轮 `snapshot_display` 成功且文件新于本次启动,失败记 `shot=failed`;删除旧 `sweep_app.sh` 凭 alive 与渲染日志写 LIT 的分支
- child stderr 按本轮 device-report 的 child pid 与 runtime 精确定位 `<runtime>/private-tmp/adapter_child_<pid>.stderr`,区分 `missing` / `read_error` / `empty`,记原始与过滤 `TOUCH21-POLL` 后的行数
- hilog 过滤用字符类写法 `[F]atal signal|[S]IGSEGV|[c]annot locate symbol|[E]rror relocating|[s]ymbol not found|[U]nsatisfiedLink|[F]ATAL EXCEPTION`,丢弃含 `HDC_LOG` 的行,并只保留本轮 child pid 且在本次启动之后的行
- 先用最小实验确认 ART `SIGQUIT` 线程栈的真实落点与完成标志;对所有未确认可用且仍存活的 app 间隔 5 s 各取一次栈,识别 `MessageQueue.next`/`Looper.loop` 空等,超时、进程已退出或无栈都记 `capture-failed`
- `render_node` 取自 `hidumper -s RenderService`,绑定本轮 pid 与窗口并保存原始片段,只作观测字段,不据此跳过取栈
- `triage.json` 分列 `observations`、`candidate_blocker`、`confirmed`;`candidate_blocker.class` 取值 `native-symbol` / `java-exception` / `null-service` / `main-thread-blocked` / `native-crash` / `exited-normally` / `render-stalled` / `capture-failed` / `no-marker`;只有同轮因果证据才进 `confirmed`
- 本轮输出放 VM `~/a2hlab/ws/out-appsweep-t0-<run_id>/`;`~/a2hlab/app-inputs/*` 只读
- 板写命令前 `board_note.sh lock`;61b 的 broker、keeper、自启在基座准备时停用并记清单

## 边界

### 允许修改
- benchmark/2026-09-27-app-breadth-sweep/scripts/**
- benchmark/*-blocker-triage/**
- tools/spec-checks/**

### 禁止
- 不修改运行时、framework、APK
- 不在白名单外的序列号上执行任何命令
- 不对当前车道未持锁的板下写命令

## 验收标准

场景: 未亮 app 取得本轮观测
  测试: t0_blocked_apps_have_observations
  假设 修复后的采集脚本在持锁的板上按 app 分片重扫清单里的 43 个未亮 app
  当 汇总各 app 的 `triage.json`
  那么 至少 39 个 app 有 `capture-failed` 以外的观测
  并且 每条 `candidate_blocker` 附带至少 1 行本轮原文证据与来源文件

场景: 纯 Java 未亮 app 取得两次主线程栈
  测试: t0_pure_jvm_apps_have_main_stack
  假设 markor、fd-etar、fd-uhabits、fd-wifianalyzer、fd-libretube、opencamera、fd-api 在重扫集合里且进程存活
  当 采集 `SIGQUIT` 线程栈
  那么 每个 app 的 `triage.json` 含两份间隔 5 s 的 `main` 段,且都来自本轮 child pid
  并且 只剩 `Looper` 空等的栈不被当作 `main-thread-blocked`

场景: 取栈失败时显式记 capture-failed
  测试: t0_stack_timeout_marked_capture_failed
  假设 child 在发送 `SIGQUIT` 前已退出
  当 采集线程栈
  那么 该 app 记 `capture-failed` 并写明原因
  并且 不使用任何旧栈或其他进程的栈

场景: hilog 只保留本轮 child 的真实异常
  测试: t0_hilog_keeps_own_pid_crash_only
  假设 hilog 里同时有本轮 child 的 `Error relocating … symbol not found` 行、另一个 pid 的 `Fatal signal` 行与采集命令自己的 HDC_LOG 行
  当 采集 hilog 崩溃片段
  那么 结果只含本轮 child 的那一行
  并且 不含 `HDC_LOG` 与 `ExecuteCommand`

场景: stderr 按本轮 pid 定位并区分缺失与空
  测试: t0_stderr_located_by_pid
  假设 运行时目录里有本轮 child 与上一轮 child 各一个 stderr 文件
  当 取回 stderr
  那么 只取回本轮 pid 的文件,且不含 `TOUCH21-POLL`
  并且 文件不存在时记 `missing`,存在但为空时记 `empty`,两者不混用

场景: 快照失败时拒绝判亮
  测试: t0_stale_screenshot_rejected
  假设 板上残留上一轮同名截图,且本轮 `snapshot_display` 失败
  当 采集截图
  那么 该 app 记 `shot=failed`
  并且 证据目录里没有该 app 本轮的截图文件,results.json 不出现 LIT

场景: LIT 对照组无回退且哨兵仍未亮
  测试: t0_lit_control_set_unchanged
  审核: human
  假设 某块板记录了完整部署清单,并用同一采集脚本重扫 13 个 LIT app 与 markor
  当 外环逐张读图签认
  那么 13 个全部判为 LIT,markor 仍未亮

场景: 基座不一致的板结果被拒绝
  测试: t0_board_without_full_lit_control_excluded
  假设 某块板的 LIT 对照组有 app 未亮,或运行中部署清单哈希发生变化
  当 汇总各板的 `triage.json`
  那么 该板本轮结果标记 `base_mismatch` 且不进入汇总
  并且 这些 app 重新排进其余板的分片

场景: 争锁失败时零写命令
  测试: t0_lock_contention_no_writes
  假设 目标板的锁被另一条车道持有
  当 采集脚本对该板启动分片
  那么 `board_note.sh lock` 返回 75
  并且 该板上没有执行任何写命令,分片内 app 记 `not-run`

场景: 板子中途掉线时终止该分片
  测试: t0_midrun_detach_stops_shard
  假设 分片进行到一半时该板从 `hdc list targets` 消失
  当 采集脚本检测到阶段失败
  那么 该分片 app 分别记 `completed` / `interrupted` / `not-run`
  并且 不读取任何上一轮的 `verdict.tsv`,没有命令发往白名单外的序列号

场景: 跨板汇总每个 app 恰好一条有效记录
  测试: t0_merged_triage_one_record_per_app
  假设 两块板各自产出分片的 `triage.json`,其中一个 app 在两块板上各有一次 attempt
  当 合并成一个 triage 集合
  那么 清单里 43 个 key 各有恰好 1 条有效记录,并注明板、run_id 与 apk_sha256
  并且 被淘汰的 attempt 仍保留在 `attempts` 里

场景: 采集不写共享输入与其他车道目录
  测试: t0_isolated_out_root
  假设 `~/a2hlab/app-inputs/localsend` 与另一车道的 OUT_ROOT 在采集前记录了哈希清单
  当 一个分片跑完并清理
  那么 本轮所有写入都在 `out-appsweep-t0-<run_id>/` 之下
  并且 app-inputs 与另一车道 OUT_ROOT 的哈希清单不变

场景: 清理拒绝删除头条目录
  测试: t0_cleanup_exempts_toutiao_dirs
  假设 板上存在 `a2hlab-source-c91d26bf` 与 `a2hlab-app-c91d26bf` 前缀的目录
  当 单个 app 扫完执行清理
  那么 两个 c91d26bf 目录及其内容仍然存在

场景: 负控使检查器失败
  测试: t0_negative_controls_fail
  假设 把生产分类器里 pid 过滤或截图新鲜度检查之一改成恒真
  当 运行对应的 `t0_*` 检查
  那么 该检查失败并指出被破坏的逻辑

## 排除范围

- 修复任何 blocker
- 商业 co-* app 的首次扫量
- 深挖板与板之间结果不一致的根因(只记录现象)
