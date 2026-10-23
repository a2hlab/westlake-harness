spec: task
name: "T79 independent platform automatic clock source map"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t76-automatic-time-readiness]
---
## 意图
T76 证实自动时间开启但设备日期仍为 1970。独立静态查明当前 OH 平台自动校时的配置、触发条件及已有验证方法，为最小校时修复提供可核依据，不将其当作头条白屏根因。
## 已定决策
- 先读 T76 和已保留系统版本资料，再查本地已有 OH 时间服务源码和产品配置。按本地工作树、vm-copies、OrbStack、hw248 的顺序找；本轮只读已有资料，不下载、不构建、不上板。
- 报告具体源码位置及 SHA、自动开关对应设置键、网络可用触发条件、NTP 来源和失败是否重试；只有源码绑定版本清楚才作当前系统结论，其余标候选或 unknown。
- 交付一个不超过 5 条的只读后续采集命令建议及其区分的假设；本卡不执行它们。预计移走首个致命点的 key 为 unknown，不能声称消除头条退出。8 分钟首交，找不到版本绑定即如实停止扩大搜索。
- 不使用 REA，不读 T71 故障或 T74 guardian/reentry 源码。保留他人脏文件，仅在本车道 analysis/t79-clock-source-map 提交本卡报告，不推送；不得声明未实现的测试通过。
## 边界
### 允许修改
- benchmark/2026-10-23-clock-readiness-source-map/**
### 禁止
- 设备访问、源码实现修改、构建、部署、手工校时、修改网络与凭据、权限变更、崩溃分析
## 验收标准
场景: 找到可绑定的自动校时实现
  审核: human
  测试: clock_readiness_source_map_review
  假设已有 OH 源码和产品版本资料
  当静态追踪自动时间开关与网络触发
  那么报告逐项源码位置和 SHA 并给有区分能力的只读探针，不推定白屏因果
场景: 版本或源码不完整
  审核: human
  测试: clock_readiness_source_map_review
  假设无法建立部署版本绑定或某个触发逻辑缺证
  当八分钟首交
  那么明确已搜索位置和 unknown，不下载构建或用设备试错填空
## 排除范围
时间服务修复实施、头条退出归因、随机崩溃防护、冷启动验收和全量测试。
