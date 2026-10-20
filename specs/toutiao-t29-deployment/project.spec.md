spec: project
name: "T29 offline deployment data"
satisfies: [REQ-TTVIDEO]
---
## 意图
复用已审六件CAS事务，预备bridge与shim双产物参数；当前没有新产物，不构造部署授权。
## 约束
- executor.py逐字复用693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb；不改原T28、设备、主树或冻结API。
- 仅离线数据与拒绝测试，未知SHA/bytes/offset/receipt必须null，fresh身份与approved_by保持null。禁止HDC/部署/push。
- 四件run/compat/media/player与T28相同；bridge/shim各自独立候选，不将旧T26 reused baseline视为T29 fresh baseline。
