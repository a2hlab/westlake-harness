spec: task
name: "G07 bounded per-shard startup observation options"
inherits: project
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
原神首次初始化可能超过20秒；把现有bms_batch已支持的wait/shots由board_run按分片透传，使一次启动可以观察到60秒而不重复重启。
## 已定决策
- 仅增加分片可选wait_seconds与shots，缺省生成原--shots 5,20且不传--wait，既有计划行为不变。
- 新选项在取锁及任何设备调用前验证：wait_seconds是有限正数且不超过120；shots为非空、递增、无重复的正数列表，最大值不超过120；bool、NaN、Infinity、字符串注入均拒绝。显式同时给wait时须不小于最大shot。
- 透传给原BMS CLI，不修改安装/锁/恢复/冒烟门。新原神计划使用wait_seconds=60与shots=[5,20,60]，不改控制组采样。
- CC仅离线实现及测试，不调用设备、不运行REA；Codex G06不改这个公共文件，交件后外环合入再给G06源码pin。首片5分钟，不扩通用调度功能。
## 边界
### 允许修改
- scripts/lab/board_run.py
- benchmark/2026-10-21-commercial-game/bounded-sampling/**
- tools/spec-checks/tests/commercial_game_bounded_sampling.rs
### 禁止
- 不修改bms_batch、冻结项、其他计划或设备，不push，不改主树。
## 验收标准
场景: 缺省兼容
  测试: commercial_game_bounded_sampling
  假设 分片不含新字段
  当 生成真实BMS argv
  那么 shots仍为5,20且没有wait覆盖，其他参数不变
场景: 一次观察到60秒
  测试: commercial_game_bounded_sampling
  假设 分片含wait_seconds=60和shots=[5,20,60]
  当 原board_run构造执行命令
  那么 argv包含wait60和shots5,20,60且仍含原hilog和恢复接线
场景: 非法配置先拒绝
  测试: commercial_game_bounded_sampling
  假设 新字段为负值、超过120、bool、非有限数、乱序重复或命令字符串
  当 加载计划
  那么 在取锁和设备调用前拒绝并报告字段原因
## 排除范围
不新建调度器，不改变设备运行时，不宣称原神运行通过。
