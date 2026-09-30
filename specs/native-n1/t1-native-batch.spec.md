spec: task
name: "N1 合并 native 簇并保留 U0 公共 API"
inherits: project
tags: [native, n1, cx-t0]
---

## 意图

将 U0 runtime 9e14 的 asset-fd 修复、32df graphics-session-sync、Flutter ANL r6 及当前 native 簇中可复用的实现合为一个候选。对 JNA、WebView、SoundPool、AudioProductStrategy、GLImpl、bionic 和其他 native 依赖逐项记录首墙、来源、处理与预测，不能把未实现项写成已解决。

## 已定决策

- FZ-003 AssetManager 源原字节编入 runtime；graphics 与 audio 独立文件新增。
- Flutter 私有兼容库与加载域仅对六个已指定包生效，其他包保持原 ANL 路径。
- 使用已有部署器 SHA、maps、单 ART 检查与回滚，保持 JAR 和 installer 为 U0。
- 出版前运行 check_frozen --package；源码或链接失败如实记轮数，环境失败另列。
- 先单层 native 对照，报告 compare_runs 实际变量数，再交外环合 U1 全量。

## 边界

### 允许修改
- benchmark/2026-09-30-n1-native/**
- specs/native-n1/**
- tools/spec-checks/**
- bms/src/adapter/framework/** 非冻结实现
- README.md 与 .octos/KNOWLEDGE-DIGEST.md

### 禁止
- 修改 FZ-003 冻结源、FZ-001 安装器、FZ-002 provider
- 修改 APK、JAR、ART 或 boot image
- 未获板锁写板，或在控制回退后继续扩大验收

## 验收标准

场景: 冻结实现与候选清单一致
  测试: n1_frozen_sources_and_package
  假设 N1 候选已装配
  当 校验源码 blob 与包内文件 SHA 并运行 check_frozen --package
  那么 FZ-003 源与登记一致且 FZ-001/002 未改变

场景: native 簇逐项有据可查
  测试: n1_cluster_dispositions
  假设 当前首墙表包含 Flutter、graphics、audio、GL、JNA、WebView 和 bionic
  当 检查 N1 处理表
  那么 每项包含原始日志位置、源码来源、实施状态与可证伪预测
  并且 无源码或属于 Java 的项明确列出边界与后续负责人

场景: 加载域与构建闭包门
  测试: n1_host_closure_and_negative
  假设 N1 runtime、ANL 与私有库构建完成
  当 核 ELF 强导入版本与 NEEDED 闭包并测试非 Flutter 包选择
  那么 无未解释缺符号且非 Flutter 包不进入私有域
  并且 故意缺依赖或改冻结源的负控被拒绝

场景: 单变量验收与控制回归
  测试: n1_device_evidence
  审核: human
  假设 授权板处于 U0 且已记录 fingerprint
  当 仅叠 N1 运行 HW、ZigZag、NewPipe、uhabits 及各已实现簇代表 app
  那么 记录 t20、facts 原文、首致命异常与 compare_runs 变量数
  并且 原冻结证据保持且控制回退时立即回滚，不宣称失败 app 点亮

场景: 回滚与统一全量交接
  测试: n1_rollback_handoff
  假设 N1 短窗结束
  当 回滚到 U0 并释放板锁
  那么 留存恢复 SHA 与 JAR receipt、可重复部署包及 U1 三板分片命令
  并且 截图待外环签认，未执行 U1 不写全量无回退
