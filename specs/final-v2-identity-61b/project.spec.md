spec: project
name: "61b final v2 full identity and original full128 driver"
---

## 意图

继承主树 demo-baseline 的 t5-seal 与 t4-stability 合约，为 T4 的同一 Boat provider/完整 planned selfcheck 提供独立身份门和原 full128 driver 最小适配。

## 约束

- 61b 当前只读；本次零设备调用、零推送，所有源码与证据写在 T0。
- T4 负责 provider/原 missing-only 前置/restore；本实现不重写这些接口，不生产设备授权或签字。
- 原 v1 保留；完整319只允许4共享替换，完整 RouteB487/HAP 实际存在，不使用5ea absence 或任意排除。
- 默认 disabled；原128成员、121t10+7t20、8窗口、resolve/records/collect 与 Mac/Orb 边界保留。
