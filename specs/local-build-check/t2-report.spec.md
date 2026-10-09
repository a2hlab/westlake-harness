spec: task
name: "核验 BoatAttack 文件退路并交件"
inherits: project
depends: [t1-build]
---

## 意图

核验 BoatAttack 的现成 CLASSNAME_FIX 文件，给出本机构建结论和剩余缺口。报告只能声明证据实际证明的程度。

## 已定决策

- BoatAttack 源件只读；结果记录完整 SHA、两个目标路径和原件字节差。
- README 英文，其余文档中文；交件清单包含门禁、契约和小证据。

## 边界

### 允许修改
- benchmark/2026-10-09-local-build-check/**
- specs/local-build-check/**
- tools/spec-checks/tests/local_build_check.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md

## 验收标准

场景: 现成文件消除编译需求
  测试: local_build_boat
  假设 本机存在 adc125f4 CLASSNAME_FIX 文件
  当 校验文件 SHA 与 U13 原件字节差
  那么 results 记录完整 SHA 两个目标路径和是否需要编译

场景: 当前 runtime 不是补丁基底时拒绝宣称可直接替换
  测试: local_build_boat
  假设 当前 runtime SHA 为 18763dd4 且与 CLASSNAME_FIX 的基底不同
  当 比较对应偏移和导出表
  那么 报告记录仅 2/49 字节匹配和 520 个删除导出并将该路径替换标为 unverified

场景: 未证明部署效果时保持限制
  测试: local_build_report
  假设 本轮只完成离线构建与静态核验
  当 生成报告与交件清单
  那么 报告标明部署未验证且 frozen 和 user-path 门禁退出码均为零

## 排除范围

- 推送、锁、安装、重启和板写。
