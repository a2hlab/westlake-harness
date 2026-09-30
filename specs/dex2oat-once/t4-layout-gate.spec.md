spec: task
name: "T4 新编 libart 与板上 R155 libart 的布局对照"
inherits: project
depends: [t3-build-art]
tags: [dex2oat, layout, gate]
---

## 意图

CheckSystemClass 比对的是 libart 编进去的系统类布局。在上板前用离线探针比较新编 libart 与板上 R155 libart(59e1bb45)的 mirror 类大小与字段偏移、Thread 偏移、ImageHeader/OatHeader 布局;对不上就回到 T1 补齐补丁,不上板。

## 边界

### 允许修改
- knowledge/toolchains/art-r155/**
- tools/spec-checks/**
- specs/dex2oat-once/**
- benchmark/2026-09-30-t4b-build-switch-gate/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md

### 禁止
- 不上板

## 已定决策

- 复用 cc-wiki 的 offsetof/sizeof 探针方法(DIGEST B.23)
- 比对清单覆盖 CheckSystemClass 检查的全部系统类
- T4b 只读实物：以完整 SHA256 绑定 R155 libart 的已核二进制谓词，解析 arm64 OAT230 的真实 KV；不能执行或修改输入。
- KV读取复用cc-wiki的check_boot_oat_rb.read_kv；既有compare_oat.parse只作有界结构交叉核验，扫描值与结构值不一致硬拒。
- BUILD.md 用唯一 `t4b-build-json` 围栏提供环境与部署 libart/OAT SHA256；历史无回执不补写为事实。普通 shell 文本只作待审证据。
- 已知不一致返回 2，缺证返回 3 并列 exceptions，完整一致返回 0；stdout 为 JSON，`--out` 同内容且拒绝覆盖输入或现有输出。
- v3c 为已知值一致正控、T5 为读屏障错配反控；v3c 缺历史 BUILD.md 时 consistency=pass 而 verdict=pending_review，不能冒充构建证据齐全。
- 原系统类布局场景保留，本子项不以编译开关测试替代它；不要求编造 OAT 没有的 GC/poisoning 键，不从 debuggable 推导 native debug。
- unknown 不能自动豁免，例外由外环审核；T5b 通过同一 CLI 补验，不绑定路径名字判断候选。

## 验收标准

场景: 系统类布局与板上 libart 一致
  测试: d4_mirror_layouts_match_board
  假设 新编 libart 与从板上拉回的 R155 libart
  当 对 CheckSystemClass 覆盖的系统类逐个比较对象大小与字段偏移
  那么 不一致项为 0
  并且 Thread 偏移与 ImageHeader/OatHeader 字段偏移不一致项为 0

场景: T4b v3c 实物正控与完整回执
  测试: d4b_reference_and_receipt
  假设 SHA256 匹配的 R155 libart 与 v3c boot.oat 实物
  当 比对二进制谓词、KV 和测试用完整 BUILD.md 回执
  那么 读屏障为 false、GC 为 CMS、generational CC 与 heap poisoning 为 false 且返回 0
  并且 测试回执标为合成夹具而非 v3c 历史构建事实

场景: T4b T5 与构建开关矛盾硬拒
  测试: d4b_mismatch_rejection
  假设 T5 boot.oat concurrent-copying 为 true 或 BUILD.md 开关与二进制不一致
  当 运行检查器
  那么 返回 2 并逐项列出 mismatch 的值与证据
  并且 缺失其他字段不能掩盖已知不一致

场景: T4b T5b 第三组实物与回执缺项
  测试: d4b_t5b_artifact
  假设 T5b 本机副本27件SHA256与外环提供的清单一致且BUILD.md声明五开关
  当 对比R155二进制、T5b真实KV与该BUILD.md
  那么 7项已知比较一致且consistency为pass
  并且 缺结构回执、两项SHA绑定与native release声明保持4项exceptions并返回3

场景: T4b 缺证与未知二进制待审
  测试: d4b_unknown_review
  假设 BUILD.md 缺失、无结构回执或 libart 不属于已核 SHA256
  当 运行检查器
  那么 返回 3 并输出非空 exceptions 且 deploy_allowed 为 false
  并且 原 v3c 历史缺证保持 pending_review 而已知一致性为 pass

场景: T4b 身份错误与 CLI 输入保护
  测试: d4b_cli_integrity
  假设 回执 SHA256 错误、OAT 损坏或输出路径为输入文件
  当 使用 CLI 的 --out 输出 JSON
  那么 身份或结构错误返回 2、拒覆盖返回 2
  并且 原输入 SHA256 不变且合法输出与 stdout 一致
