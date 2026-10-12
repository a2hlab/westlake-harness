spec: task
name: "Frozen API platform evidence binding"
inherits: project
---

## 意图

针对 frozen.json 的 8 条 API 和各自已登记 APK，离线查找原运行目录、平台身份与产物哈希，把表中 unknown 分成可直接补齐和仍缺证两类。仅输出补充表，禁止改 atlas shard 或 frozen.json。

## 边界

### 允许修改
- benchmark/2026-10-12-api-version-bindings/**
- tools/spec-checks/tests/api_version_bindings.rs

## 验收标准

场景: 冻结条目逐项有结果
  测试: api_version_bindings_inventory
  假设 主树 frozen.json 恰有 8 条且来源记录存在
  当 生成 version-bindings.json 与中文对照表
  那么 8 个冻结 ID 恰好各一条，每条列 APK、产物、来源 SHA、版本值和 binding_strength；找不到为 unknown

场景: 跨运行上下文不伪装直接绑定
  测试: api_version_bindings_scope
  假设 平台版本只出现在另一个运行或仅有 AOSP tag/targetSdk
  当 校验关联键及版本断言
  那么 只有同运行或明确身份关联才标 direct，否则 context_only 或 unknown；不从截图猜系统版本

场景: 来源漂移拒绝
  测试: api_version_bindings_negative
  假设 真实补充表含相对路径与 SHA256
  当 用临时副本注入不存在路径、错误 SHA 与重复冻结 ID
  那么 三种变异均非零退出，检查器不修改原证据

## 排除范围

- 真实上板、运行时二进制修复、修改冻结登记、自动签封板与推送。
