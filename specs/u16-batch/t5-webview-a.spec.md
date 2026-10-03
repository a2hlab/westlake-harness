spec: task
name: "T5 M2 路线 a:真 WebView 渲染(A0 出帧后)"
inherits: project
tags: [webview, m2, blocked-on-probe]
depends: [A0-probe]
---

## 意图

M2 簇(u16 簇 B)的 4 个全屏 WebView app(vaults-randomlydie、yatoo、jiten-webview、timur-webrtc-check)白窗的根因是 typed-zero WebView 桩没有渲染引擎:界面全在 WebView 里,桩画不出内容。路线 a = 提供 ArkWeb 承载的真 WebView 渲染。本任务是路线 a 的实现契约,但**阻塞于 A0 探针**(cc-t3/cc-wiki 在跑):A0 必须先证明 app 侧 WebView 能从 ArkWeb 拿到出帧(CreateNweb + 输出帧回调出图),否则路线 a 换向。

来源:benchmark/2026-10-03-u16-wall-clusters/clusters.csv 簇 B + benchmark/2026-10-03-m2-webview-roadmap(路线 a)+ benchmark/2026-10-03-m2-a0-probe(A0)。

## 已定决策

- depends: A0 出帧窗口的外环签认(探针 mode 0/1 至少一个出帧);A0 失败则本任务取消或重定向,不硬上。
- 实现分两步走(照 roadmap 的 A1/A2):A1 = 单 app 级 WebView 内容出帧;A2 = 多 app 并存与通用化。本契约覆盖两步,U16 批内只做 A1(4 键复验),A2 留 U17。
- 4 键全部进 U16 键表 movers(来源=簇 B/路线 a);jiten 保留自己的 M5 对话框路径,不因 WebView 改动丢。
- 观察点:4 键 movers + t20 截图判定(审核: human);check_fix_observers 命中 runtime JAR/webview 交付 token。
- 白窗上限先于亮判定:若 ArkWeb 承载出内容但布局错乱,记 alive-partial,不记 lit。

## 边界

### 允许修改
- benchmark/2026-10-03-u16-t5-webview-a/**
- runtime JAR WebView 桩的渲染路径(经外环批;不违反已冻结的 J10e/f/g 行为)
- tools/spec-checks/tests/u16_t5_webview.rs

### 禁止
- 不在 A0 未签出帧前上板
- 不动 ArkWeb 引擎本体(/system 侧 arkwebcore 不改)

## 验收标准

场景: A1 出内容
  测试: u16_t5_a1_content
  假设 A0 已签出帧且 A1 实现完成,U16 窗口跑 4 键各 1 次
  当 采 t20 截图并跑 first_fatal
  那么 4 键无一死于 WebView 桩 NPE/UnsupportedOperationException
  并且 t20 有非白内容(逐张人审,审核: human)

场景: 不回退 WebView 桩既有修复
  测试: u16_t5_no_webview_regression
  假设 U16 键表含 J10e/f/g 已修键(tutanota 等)回归观察
  当 pair_sheet 汇总
  那么 已修键 auto=same(或外环确认)无一翻暗

场景: A0 未出帧 → 任务取消
  测试: u16_t5_cancel_without_frame
  假设 A0 探针全部 mode 的出帧签认为否(无 CreateNweb 输出帧)
  当 U16 批排程评估本任务
  那么 本任务标记 cancelled(依赖失败),不上板、不占窗口并报依赖错误
  并且 取消原因引用 A0 签认件,重定向决策交外环

场景: depends 决策的验证(A0 签认前置)
  测试: u16_t5_depends_gate
  假设 依赖检查读取 A0 外环签认件
  当 A0 未签或签认为未出帧
  那么 depends 门不通过,t5 的实现与上板步骤全部被阻塞
  并且 门结果与引用的签认件路径一并输出

## 排除范围

- 不含 A2(多 app 通用化)与 Chromium 完整兼容;那是后续批次。
