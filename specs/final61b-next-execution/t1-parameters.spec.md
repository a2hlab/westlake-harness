spec: task
name: "Audit original61b installed input guard and prepare disabled final V2 bindings"
inherits: project
---
## 意图

核真实同61b原128record与原工具完整SHA，落命令链和新V2824文件+130包消费者模板；实际未知字段保持null。

## 已定决策

- 原driver/identity/source-map/编译器全部精确复用，不改冻结件。
- 用户新授权只做APPROVED/approved_by字段映射，保留权威源SHA和原scope/exclusions。
- 实际composition/UID/newboot/WMS/deployment/128/signoff都等真实回执，不造成功或跨板借信。

## 边界

允许修改: benchmark/2026-10-14-final61b-next-execution/**、specs/final61b-next-execution/**、tools/spec-checks/tests/final61b_next_execution.rs。
禁止修改: 主树、T4、冻结API包、原V1、原driver/compiler、设备。

## 验收标准

场景: 原安装输入守卫和授权映射通过
  测试: final61b_next_execution
  假设 实际user授权和原同61b128安装records可读且完整SHA匹配
  当 原输入validator与离线参数checker核验
  那么 128record原serialAPKsuccess保持且用户scope不扩大
  并且 824文件130包以及原954与128成员门保留

场景: 借板漂移缺项与未到字段拒绝升格
  测试: final61b_next_execution
  假设 用外板serial错误APK缺key或错误recordpin扰动原索引
  当 原validator离线拒绝并检查disabled模板
  那么 四负例拒绝且实际未知字段null不宣称live954或新128PASS
  并且 原argv选项精确匹配原CLI含R5委托参数
