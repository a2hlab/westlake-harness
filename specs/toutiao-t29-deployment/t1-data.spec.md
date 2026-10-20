spec: task
name: "T29 dual artifact pending deployment data"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: []
---
## 意图
在生产未完成时先闭合部署参数和失败拒绝；预计移走部署等待，不声称修复视频首错。
## 已定决策
- 派生T28数据；保留原executor、来源pins、readonly inputs、run引用和player relocation字节。bridge和shim必须分别有最终生产SHA、bytes及公开构建引用后才能另轮冻结。
- check_final当前只检查pending模板与原入口拒绝，不提供新交易体。实际执行原executor的preflight/apply/rollback；缺任一产物必须在Board导入之前拒绝。
- 新bridge owner/GOT与shim三导出偏移保持未知，原player三个slot不变。static绑定不等于实际winner。
## 边界
### 允许修改
- benchmark/2026-10-20-t29-deployment/**
- specs/toutiao-t29-deployment/**
- tools/spec-checks/tests/toutiao_t29_deployment.rs
### 禁止
- benchmark/2026-10-20-t28-shim-deployment/**
- knowledge/frozen/**
## 完成条件
场景: 原事务及四件边界保持
  测试: ttvideo_t29_deployment_pending
  假设 T28原事务和四件参数可读
  当 检查派生pending数据与所有模板自pin
  那么 executor全字节及四件相等，三mode preview均device_calls为0，fresh身份和签认均null
场景: 任一产物缺失不得执行
  测试: ttvideo_t29_deployment_pending
  层级: integration
  替身: 本地合成production引用与不可用Board模块，实际原executor入口
  假设 bridge或shim的最终SHA缺失
  当 分别实调用原preflight/apply/rollback的execute入口
  那么 每例非零且在导入Board之前报对应candidate pin required，无设备调用
场景: 未完成来源与边界漂移拒绝
  测试: ttvideo_t29_deployment_pending
  假设 单候选仅有SHA却无production refs，或四件参数、executor、自pin被改
  当 运行实际校验器与原入口
  那么 无production closure时拒绝且每个漂移反例失败，不接受旧候选offset代替未知值
场景: 离线通过不授权设备
  测试: ttvideo_t29_deployment_pending
  假设 所有本地测试通过而双产物和fresh身份仍缺
  当 生成检查回执和交付清单
  那么 状态仅PENDING_TEMPLATE_CHECKED_NOT_ADMISSION，生产SHA/bytes/offset/receipt为空并列待补，禁止升级视频或封板结论
## 排除范围
不构建候选，不改executor交易，不重跑旧事务全套，不采设备身份或创建实际admission。
