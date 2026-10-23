spec: task
name: "T69 compare observed first-launch paths before another device trial"
inherits: project
depends: [t68-61b-single-network-boot-demo]
satisfies: [REQ-TTVIDEO]
---
## 意图
对照T59/T61信息流成功与T66/T68首启白屏的已有证据，确认我们控制的桌面入口、启动脚本、运行时版本或启动时序是否有可行动差异。只有具体差异才推动修复或最小实验，避免无差别重复重启。
## 已定决策
- 限15分钟，只读已有持久证据和本地已验证源码；不操作设备。至少比较T61与T68；T59/T66用于补充。首个可见错误只记录普通启动日志，不研究第三方随机崩溃机制。
- 每轮列出boot、实际HAP/config/native指纹证据、图标目标与点击时间、child出生/退出、guardian状态、首张实图、网络事件。未测字段填unknown，不拿另一个boot指纹替代。
- 从已记录源码定位桌面入口到我们拥有的启动器/guardian的实际路径，最多提出一个有证据支持的可控差异和一个能区分解释的最小实验；每项给文件行号与SHA。没有可控差异则明确报告，不发明修复。
- 保留T68在30/90秒之间有2秒断连的反例，不能写连续网络稳定；不由时间相近推出因果。不重复T53/T54已知缺口的全量研究。
- 不变更运行时、重启、重开应用、读凭据、操作REA/debugger/内存或二进制。只commit不push。人工回执选择器尚未实现，不报lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-first-launch-path-comparison/**
### 禁止
- 设备操作、产品源码或配置修改、构建部署、第三方崩溃/反虚拟化研究、全盘搜索、其他worktree修改。
## 验收标准
场景: 发现可控启动差异
  审核: human
  测试: existing_first_launch_comparison_receipts
  假设已有成功与失败轮次的启动证据
  当按同一字段表对照且核查对应本地源码
  那么输出逐字段证据定位和SHA、一个可控差异及可证伪实验，不把候选解释写为根因
场景: 无可行动差异或证据缺失
  审核: human
  测试: existing_first_launch_comparison_receipts
  假设差异不能归属或15分钟预算到达
  当结束调查
  那么交付明确unknown及搜索边界，不上板重复试验、不声称已经修复
## 排除范围
随机崩溃修复、关闭进程重开、网络驱动排障、原神、全量APK。
