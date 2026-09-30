spec: task
name: "N3b runtime publication candidate"
inherits: project
---

## 意图

原N3没有WebView发布函数，单有webviewupdate应答不能通过feature门。移植真实provider可用性检查、cache/public双回读及post-bind发布，打成单runtime替换包；输入缺件和Java接线写清，不声称Chromium上屏。

## 已定决策

- 以532633da的三个helper和两个公开函数为来源，保留可用性、Application与readback条件。
- 新增明确的JNI prime/post-bind入口供cc-t3调用，不依赖日志字符串触发，不复制头条专用wrapper修复。
- 只编新增对象，再按N3原顺序重链；先无新增对象重链核基线逐字节一致。
- 非目标app无自动行为；调用由Java配套决定且真实provider缺失必须返回false。

## 边界

### 允许修改
- benchmark/2026-09-30-n3b-webview/**
- specs/native-n3b/**
- tools/spec-checks/**
- README.md 与 .octos/KNOWLEDGE-DIGEST.md

### 禁止
- 任何板操作，修改N3导出包或冻结源
- 修改生产JAR/APK、ART/boot、provider/host/ANL、installer
- 用空provider或强制true冒充真实WebView能力

## 验收标准

场景: 整段来源与真实JNI主机测试
  测试: n3b_publication_host
  假设 532633da源和JDK可读取
  当 编译原helper并在真实JVM执行JNI
  那么 无provider和无Application均不发布true且公有cache回读失败不报成功
  并且 post-bind成功后迟到的prime不撤销feature且负控被拒

场景: 最小构建与替换包
  测试: n3b_single_runtime_package
  假设 N3原对象和冻结工具链可用
  当 原样重链基线再加入一个对象重链候选
  那么 基线逐字节命中且候选仅runtime一个声明路径改变
  并且 导出不减少、严格链接和check_frozen及dry-run通过

场景: 跨层交接与效果边界
  测试: n3b_java_handoff
  审核: human
  假设 板仍离线且生产JAR未修改
  当 交付Java方法签名、发布时机和真实provider输入清单
  那么 配套未完成不放行且回滚命令可复核
  并且 截图与新增点亮写unknown
