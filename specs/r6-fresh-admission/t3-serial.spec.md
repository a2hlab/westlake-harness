spec: task
name: "Thin original smoke10 full128 finally retained-recovery dispatch"
inherits: project
depends: [t2-actual-run.spec.md]
---
## 意图

仅串行调用原十控首plan/prelock与原full128八窗driver，finally调用原retained恢复链。

## 已定决策

- 原件逐SHA不变；root提供enabled副本、新batch授权与marker。
- handoff/events是固定路径，运行时核实际author和实际handoff SHA，避免签名循环。
- 无锁走原独立恢复runner；本批cx-t0锁走原同锁恢复、HWZZ、verify与按owner解锁；异主保锁报root。

## 边界

允许修改: benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/r6-serial-dispatch/**、specs/r6-fresh-admission/t3-serial.spec.md、tools/spec-checks/tests/r6_serial_dispatch.rs。
禁止修改: main/T4/BMS、原件pin、原driver和身份层、设备、授权或marker。

## 验收标准

场景: disabled实际CLI与最小原入口串行调用
  测试: r6_serial_dispatch
  假设 root实际四执行副本与fresh337/GAME_PASS已pin
  当 preview或mock执行串行入口
  那么 原十控prelock和runner后才调原八窗driver
  并且 默认零设备且不改原件或128门禁

场景: 原失败收尾保持owner且不重取锁
  测试: r6_serial_dispatch
  假设 十控失败或finally时无锁或cx-t0锁或异主锁
  当 mock运行原恢复入口协议
  那么 无锁独立runner与同锁recover/HWZZ/verify/unlock按原owner执行
  并且 异主保锁拒绝且失败不会继续full128
