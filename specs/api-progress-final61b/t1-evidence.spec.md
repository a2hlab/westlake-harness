spec: task
name: "Append actual61b scoped full128 evidence to NATIVE-173"
inherits: project
---
## 意图

在独立兄弟包复用原atlas生成与校验链，补充NATIVE-173的实际61b验证来源，让用户从同一表看到本板实测范围。先准备原消费者接口，实际输入由outer完成128审定后提供。

## 已定决策

- 固定已land315底表完整SHA；原314行逐字段相等，NATIVE-173只更新oh_tested、route_generation、validations、gaps、evidence五个证据字段。
- 消费实际outer128回执的路径与SHA，核61b完整序列号、086d boot、f28运行时、128唯一key、121t10及7t20、原256截图和受限接受判词；不要求先完成封板签字。
- 复用现有JSON、CSV、中文Markdown与中英文HTML生成方法及固定逻辑路径链接校验；不另造API表架构。
- API表不签V2、不新增冻结条目、不把首屏或空态升格为功能验证。

## 边界

### Allowed Changes
- benchmark/2026-10-14-api-progress-final61b/**
- specs/api-progress-final61b/**
- tools/spec-checks/tests/api_progress_final61b.rs

### Forbidden
- 原API包、原314行、frozen登记、运行时、设备、原round、主树。内环仅在自己的worktree交付。

## 验收标准

场景: 同61b实际受限证据进入单行与全部视图
  测试: api_progress_final61b
  假设 原315底表与实际outer128回执完整SHA固定且同61b128和逐key档位完整
  当 复用原生成链生成独立兄弟包并校验
  那么 原314行逐字段相等且仅NATIVE-173五个证据字段变化
  并且 JSON和CSV和中英文HTML共享315条内容且最终逻辑链接逐一存在

场景: 错板或未完成回执拒绝发布
  测试: api_progress_final61b
  假设 输入为5ea回执或缺少实际outer回执或不足128key或SHA不一致
  当 执行正式生成入口
  那么 返回非零且不生成标作通过的正式视图
  并且 合成负例与准备态不能作为实际验证证据

场景: 版本与功能范围不升格
  测试: api_progress_final61b
  假设 同61b128仅受限首屏不退化接受且原有空态和失败应用保留
  当 校验更新后的NATIVE-173与其他314行
  那么 Android未知字段和实现成员和API未冻结保持原值
  并且 不增加功能级验证或V2签认结论并保留既有NOT_LIT和随机崩溃边界
