spec: task
name: "Prepare original collector argv and preview disabled final consumer interfaces"
inherits: project
---
## 意图

交独立final61b-seal-capture-v2的原collector参数和disabled消费者，避免128结束才发现接口缺口。

## 已定决策

- 原collect/adapter源码全SHA复用，只派生groups/两个extra package与local binding。
- RouteB历史source8589和24控制rollback显式pin且保留9f历史；Boat3989 source与49d7实际enabled角色单enable差异，绑真实backup。
- 原collector recording用实际既存raw，仅记录argv，在snapshot转换前终止；真实outer admission不可用draft代替。

## 边界

允许修改: benchmark/2026-10-14-final61b-v2-collector/**、specs/final61b-v2-collector/**、tools/spec-checks/tests/final61b_v2_collector.rs。
禁止修改: 已归档approved-execution、原collector/adapter/build_seal、主树、原V1、任何设备。

## 验收标准

场景: 原collector参数机械完整
  测试: final61b_v2_collector
  假设 原实际stage954和冻结collector可读
  当 离线运行原函数的recording到snapshot转换前
  那么 记录181设备argv但实际设备调用0且824文件130包954完整
  并且 独立输出路径不在已归档目录且不产生snapshot或errors数组

场景: 未签admission拒绝且旧路径不跨角色
  测试: final61b_v2_collector
  假设 RouteB487和Boat18及真实source/backup/UI证据pin均已确定
  当 原overlay消费端预演未签字段
  那么 pending admission拒绝而shape-only PASS明确不是实际准入
  并且 历史RouteB boot不改且Boat disabled和enabled角色独立
