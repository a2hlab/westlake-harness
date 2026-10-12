spec: task
name: "API atlas registry evidence inventory"
inherits: project
---

## 意图

盘点冻结全部条目、版本环境与横切运行时能力、各类扫描覆盖缺口。从冻结表、静态清单、修复报告与实测材料提取可追溯的知识行，交给外环合表；不重新上板验证。

## 已定决策

- 按 project 的 row-template 填写 rows；同族有不同实现状态必须拆行。汇总文档不能把静态覆盖数改称实测数。
- 每个来源记 SHA256，缺失材料写 gaps；输出 shard 顶层 rows、sources、coverage_notes、unclassified。

## 边界

### 允许修改
- benchmark/2026-10-12-api-progress/shards/registry.json
- benchmark/2026-10-12-api-progress/shards/registry-notes.md
- benchmark/2026-10-12-api-progress/shards/registry-landing-paths.txt

## 验收标准

场景: 来源可追溯的能力行入表
  测试: api_progress_registry
  假设 仓库内存在本分片范围的实现报告和实测证据
  当 生成分片 JSON
  那么 每行有唯一 ID、成员、实现方式、版本、APK 证据、限制与至少一个带 SHA256 的来源

场景: 未知版本不被补成支持范围
  测试: api_progress_registry
  假设 材料只说明 AOSP 源码版本或 APK targetSdk
  当 填写 OH 与 Android 实测版本
  那么 无直接证据的字段为 unknown，版本推断写入 gaps，不声明跨版本有效

场景: 静态存在和占位不冒充实测成功
  测试: api_progress_registry
  假设 某 API 只有符号导出、桩实现或历史报告
  当 生成状态与 APK 验证列表
  那么 证据级别分别保留 static、unit 或 reported，未实测 APK 不进入成功列表

## 排除范围

- API 修复、板上实验、改冻结登记、重判历史截图、签 #91 封板回执。
