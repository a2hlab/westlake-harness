spec: task
name: "Update only NATIVE-173 full128 evidence and regenerate portable views"
inherits: project
---
## 意图

消费outer权威受限ACCEPT回执，将315底表的NATIVE-173补充full128和原947恢复证据，保持原314逐字段相等。

## 已定决策

- 复用原atlas/已land增量生成链，只修改NATIVE-173五个证据范围字段。
- 机器JSON/CSV/中文表/中文HTML同源，英文HTML共享相同canonical315行，仅翻译展示。
- APK分支与原947现存数据跨boot复现只支持非f28特有，不升级Snotz/Toodoo功能或宣称因果实验。

## 边界

允许修改: benchmark/2026-10-13-api-progress-r6-full128/**、specs/api-progress-r6-full128/**、tools/spec-checks/tests/api_progress_r6_full128.rs。
禁止修改: 原API包、原314行、atlas源码、frozen登记、运行时、设备、主树。

## 验收标准

场景: 单行受限证据和所有视图同步
  测试: api_progress_r6_full128
  假设 已land315底表与权威full128回执的完整SHA固定
  当 原生成链离线生成并检查各视图
  那么 只有NATIVE-173五个范围证据字段变化且原314逐字段一致
  并且 原CSV/Markdown/HTML一致性和四负例通过

场景: 版本冻结限制与跨树链接不升格
  测试: api_progress_r6_full128
  假设 full128和原947恢复真实rc0且受限startup nonregression采认
  当 检查机器行与中英文HTML的状态及移树生成
  那么 OH只6.1.0.31且Androidunknown和API未冻结V2未封保留
  并且 英文HTMLcanonical315底表不变且全部证据pin及固定逻辑链接可复验
