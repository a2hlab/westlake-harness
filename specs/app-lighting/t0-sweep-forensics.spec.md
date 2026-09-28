spec: task
name: "T0 修扫量取证并重扫未亮 app"
inherits: project
tags: [forensics, sweep, board-5ea]
---

## 意图

2026-09-27 的扫量没有留下任何可诊断数据:每个 app 的 `hilog-crash.txt` 都是 223 字节,内容是 grep 命令在 hilog 里匹配到它自己的 HDC_LOG 行;child stderr 所在的运行时目录在收尾清理时被删掉。本任务修 `sweep_app.sh` 的采集,在清理前把每个 app 的具名 blocker 取回,然后重扫 43 个未亮 app 与 13 个 LIT 对照组。纯 Java 的 7 个未亮 app 在静态缺口图里找不到任何区分性缺口,所以采集必须同时覆盖 native 链接错误和 Java 侧主线程状态。

## 已定决策

- 清理前取回三类文件:`/proc/<child>/root/data/local/tmp/adapter_child_<pid>.stderr`、运行时目录 `private-tmp/*.stderr`、stage 目录 `parent.log`
- hilog 过滤用字符类写法 `grep -aiE '[F]atal signal|[S]IGSEGV|[c]annot locate symbol|[U]nsatisfiedLink|[F]ATAL EXCEPTION'`,并丢弃含 `HDC_LOG` 的行
- child 起活 30 s 后仍无渲染节点时,向它发 `SIGQUIT` 取 ART 线程栈,保存 `main` 线程段
- 渲染节点判据:`hidumper -s RenderService` 输出里是否存在该 app 的 `*_content` 节点,写入 `render_node` 字段
- 每个 app 产出 `triage.json`,`first_blocker.class` 取值 `native-symbol` / `java-exception` / `null-service` / `main-thread-blocked` / `no-marker`,附原文证据行
- 取 stderr 时过滤 `TOUCH21-POLL` 行

## 边界

### 允许修改
- benchmark/2026-09-27-app-breadth-sweep/scripts/**
- benchmark/*-blocker-triage/**
- tools/spec-checks/**

### 禁止
- 不修改运行时、framework、APK
- 不在白名单外的序列号上执行任何命令

## 验收标准

场景: 未亮 app 拿到具名 blocker
  测试: t0_blocked_apps_have_named_blocker
  假设 采集修复后的 `sweep_app.sh` 在白名单三块板上按 app 分片重扫 43 个未亮 app
  当 汇总各 app 的 `triage.json`
  那么 至少 39 个 app 的 `first_blocker.class` 不是 `no-marker`
  并且 每条非 `no-marker` 记录附带至少 1 行原文证据

场景: 纯 Java 未亮 app 拿到主线程栈
  测试: t0_pure_jvm_apps_have_main_stack
  假设 markor、fd-etar、fd-uhabits、fd-wifianalyzer、fd-libretube、opencamera、fd-api 在重扫集合里
  当 child 起活 30 s 后 `render_node` 为 false
  那么 该 app 的 `triage.json` 含非空的 `main_thread_stack`

场景: hilog 采集不再匹配自身
  测试: t0_hilog_capture_excludes_self_match
  假设 某 app 运行期间 hilog 没有任何崩溃行
  当 采集 hilog 崩溃片段
  那么 `hilog-crash.txt` 不含 `HDC_LOG` 与 `ExecuteCommand`
  并且 该文件大小为 0 字节

场景: 取回的 stderr 不被触摸轮询刷屏
  测试: t0_stderr_filters_touch_poll
  假设 某 app 的 child stderr 含大量 `TOUCH21-POLL` 行
  当 取回 stderr 存入证据目录
  那么 证据文件不含 `TOUCH21-POLL`
  并且 `triage.json` 记录原始行数与过滤后行数

场景: LIT 对照组无回退
  测试: t0_lit_control_set_unchanged
  审核: human
  假设 13 个 2026-09-27 LIT app 用同一采集脚本重扫
  当 人读每张截图
  那么 13 个全部判为 LIT

场景: 板子掉线时拒绝该分片剩余 app
  测试: t0_refuses_when_board_detached
  假设 某分片所在的板不在 `hdc list targets` 输出里
  当 运行 `sweep_batch.sh`
  那么 该分片每个剩余 app 记为 `REFUSE: not attached`
  并且 其余板上的分片照常完成
  并且 没有任何命令发往白名单外的序列号

场景: 基座不一致的板结果被拒绝
  测试: t0_board_without_full_lit_control_excluded
  假设 某块板上 13 个 LIT 对照组重扫后有 app 未亮
  当 汇总三块板的 `triage.json`
  那么 该板的分片结果标记 `base_mismatch` 且不进入汇总
  并且 这些 app 重新排进其余板的分片

场景: 跨板汇总每个 app 恰好一份
  测试: t0_merged_triage_one_record_per_app
  假设 三块板各自产出一个分片的 `triage.json`
  当 合并成一个 triage 集合
  那么 43 个未亮 app 每个恰好有 1 条记录,并注明来自哪块板

场景: 清理拒绝删除头条目录
  测试: t0_cleanup_exempts_toutiao_dirs
  假设 板上存在 `a2hlab-source-c91d26bf` 与 `a2hlab-app-c91d26bf` 前缀的目录
  当 单个 app 扫完执行清理
  那么 两个 c91d26bf 目录仍然存在

## 排除范围

- 修复任何 blocker
- 商业 co-* app 的首次扫量
- 深挖板与板之间结果不一致的根因(只记录现象)
