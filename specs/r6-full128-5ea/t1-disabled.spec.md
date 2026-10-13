spec: task
name: "Derive disabled5ea R6 proof smoke and original128 windows"
inherits: project
---

## 意图

消费实际5ea原337 proof和最终T4三件计划，最小改绑identity与原driver，生成可运行离线prepare和八窗预览。

## 已定决策

- 原r4 proof和旧W3 plan/freeze独立逐SHA校验；新三件source/table/worker只形成四对象delta。
- 保留全部只读check/parse/runtime/boot失败函数，不创建新部署框架或私有app安装。
- 原实际5ea Noice72 installed index及manifest/tiers精确绑定，不借5cd或61b回执。

## 边界

允许修改: benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/r6-full128-5ea/**、specs/r6-full128-5ea/**、tools/spec-checks/tests/r6_full128_5ea.rs、README.md、.octos/KNOWLEDGE-DIGEST.md。
禁止修改: T4/main/BMS程序、旧冻结目录、设备、私有数据、原索引。

## 验收标准

场景: 原真实CLI生成完整disabled候选八窗
  测试: r6_full128_5ea
  假设 最终同板三件计划与原proof及128index逐SHA匹配
  当 离线compiler和原driver真实CLIprepare
  那么 完整337及typedABSENT保留且仅四对象SHA更新
  并且 原128和121t10加7t20八窗disabled且无transport

场景: 任意掉guard或串板或扩delta拒绝
  测试: r6_full128_5ea
  假设 原333项或319或ABSENT或successor前像或plan/programpin有一项漂移
  当 静态校验与recording执行
  那么 原失败门拒绝且没有候选执行授权

场景: 原driver与运行失败函数保持
  测试: r6_full128_5ea
  假设 原已跑5ea driver和原Reader/helper有固定全SHA
  当 AST比较和模拟错误回执
  那么 runtime/boot/parent/version/marker与records收集异常门保持
