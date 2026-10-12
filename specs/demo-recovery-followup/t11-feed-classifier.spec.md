spec: task
name: "Recognize observed Toutiao feed layouts without admitting non-feed screens"
inherits: project
depends: [t9-child-readiness]
---

## 意图

修复当前 screen-gate 将真实信息流判成 unknown 的确定性缺口。外环在 boot 52533 使用原部署分类器读取 before、returned、refresh 三张目视正常的信息流，均得到 unknown；文章页 unknown 正确。先以原源码逐项像素判据解释错判，再增加有真实截图依据的最小布局支持。

## 已定决策

- 新独立候选复用已有 JPEG/PNG 解码和构建流水线；保留 privacy、login 优先级以及原已验证 feed 布局，不修改历史源码或产物。
- 只支持由实际截图证据确认的信息流布局；联合检查多个界面区域和实际文章内容特征，不以单个红点、进程存活或任意有图页面当作 feed。
- 新旧正例、隐私页、登录页、IMEhost、文章页、桌面、HelloWorld、ZigZag、空白及坏图分别记录来源 SHA、期望、实际和退出码；不得将拒绝样本改标为 feed 来通过测试。
- 原始构建 stdout、stderr、退出码、源码 SHA、工具链 SHA 与候选产物 SHA 一起交付；本地和 ARM 实测证据分开，内环只做本地工作，外环负责 ARM 准入和真实截图复验。

## 边界

### 允许修改
- benchmark/2026-10-12-feed-classifier/**
- tools/spec-checks/tests/recovery_feed_classifier.rs

## 验收标准

场景: 已观察的新旧信息流布局均被准确识别
  测试: recovery_feed_classifier_positive
  假设 原已通过的信息流与本轮目视确认且内容不同的信息流截图及固定 SHA
  当 编译候选并对原图逐项分类
  那么 这些正例均为 feed 且错误原因、变更判据和原始结果逐项可追溯

场景: 非信息流和无效图片不能触发成功
  测试: recovery_feed_classifier_negative
  假设 隐私、登录、IMEhost、文章、桌面、HelloWorld、ZigZag、空白、缺失、截断和不支持尺寸等负例
  当 原分类器与候选分别读取相同输入
  那么 候选没有任何负例被判 feed 且隐私和登录优先级保持不变并保留失败退出码

场景: 发布件可由固定输入重建且旧件不变
  测试: recovery_feed_classifier_reproducible
  假设 固定源码、工具链和原始构建执行日志
  当 检查重建产物、来源和交付清单
  那么 产物 SHA 匹配且旧冻结字节不变并明确尚未获得的 ARM 或最终上板证据

## 排除范围

- 内环板访问、修改守护脚本或封板判据、自动同意隐私、发送 UI 操作、随机崩溃或运行时修复、将离线识别通过作为封板完成。
