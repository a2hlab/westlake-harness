spec: task
name: "N3 61b controls targets rollback"
inherits: project
---

## 意图

实测离线候选 N3 8a7880fa 是否越过 U2 native 墙，以截图和首致命点报告，不把符号闭包当上屏。

## 已定决策

- 原 JAR 记录 receipt，部署前露出包内 r8b，部署后恢复同一 J3。
- 使用 master bms_batch 与 16M 预检，HW/ZZ 在前，Firefox/Fennec、VLC、SPD、Termux 和保护组在后。
- 每组保存 facts 原文、t20 截图及实际差异；单次保护失败先按剩余窗口复验，明确回退就撤。

## 边界

### 允许修改
- benchmark/2026-09-30-n3-61b/**
- specs/native-n3-device/**
- tools/spec-checks/**
- README.md 与 .octos/KNOWLEDGE-DIGEST.md

### 禁止
- 其他板写入，改变 N3 包或 U2 内容，kill -9 appspawn-x 主进程
- 把未跑或无截图的 key 写成已亮

## 验收标准

场景: 授权与基线留档
  测试: n3_device_baseline
  假设 外环已放行且 cx-t0 持 61b 完整 key 锁
  当 首次写板之前读取 U3 与 JAR receipt
  那么 指纹是 0b81cdbe0ed9 且候选 SHA 与冻结门通过
  并且 保存原 boot 和包路径

场景: 控制与目标证据
  测试: n3_device_evidence
  审核: human
  假设 先完成 HW 与 ZigZag 控制
  当 收集目标与保护组运行结果或控制回退中止原因
  那么 facts 由 record 和进程表生成并列截图路径
  并且 首致命点与 N3 预测对应且 compare_runs 差异如实列出

场景: 回滚并释放
  测试: n3_device_restored
  假设 设备窗口结束或候选失败
  当 按部署器回滚再恢复原 JAR
  那么 U3 全路径 SHA 与指纹 0b81cdbe0ed9 恢复
  并且 记录解锁且窗口不超过 45 分钟
