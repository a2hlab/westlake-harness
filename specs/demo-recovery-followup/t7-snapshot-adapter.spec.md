spec: task
name: "Observed package identity and seal snapshot adapter"
inherits: project
---

## 意图

将外环保存的真实只读命令原件转换成封板编译器需要的完整快照，拒绝从旧计划猜版本或把通用板快照改名冒充最终快照。修复 BMS 嵌套 applicationInfo.versionCode=0 被当作顶层已安装版本的歧义。

## 已定决策

- 内环仅本地转换已采原件；外环 collect.py 以白名单 serial 和显式目标列表执行只读采集，测试仅替身传输。目标列表来自已签 baseline、完整 demo manifest 和新 overlay 参数。
- 包版本读 bm dump 的同名顶层对象，Android APK 路径取其 applicationInfo.codePath；HAP 取唯一 entry 模块的 hapPath。不得递归收集所有 versionCode。
- 哈希、参数、boot、包版本都来自带远端 rc=0 的原件；缺项、重复路径、跨 boot 和错误状态均拒绝，快照不得声称 UI 已验收。

## 边界

### 允许修改
- benchmark/2026-10-12-seal-snapshot-adapter/**
- tools/spec-checks/tests/seal_snapshot_adapter.rs
- scripts/lab/demo_selfcheck.sh

## 验收标准

场景: 正确提取真实顶层包身份
  测试: seal_snapshot_adapter_identity
  假设 已保存 Anki 和 imehost 的真实 BMS 原件以及嵌套零版本
  当 离线解析包身份
  那么 得到顶层正确版本和实物 APK 或 HAP 路径，拒绝错名与缺版本

场景: 快照转换必须完整且同一启动
  测试: seal_snapshot_adapter_completeness
  假设 文件组、包列表、参数和首尾 boot 原件可读
  当 转换完整材料以及缺哈希、远端失败、跨 boot 变异
  那么 完整材料通过真实 t5 编译器，三类变异非零且不产生完成快照

## 排除范围

- 内环板访问、部署、重启、补签、修改旧计划和运行时；只读采集由外环单独执行，代码测试不得访问板子。
