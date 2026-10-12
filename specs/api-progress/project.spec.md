spec: project
name: "Evidence-backed Android API implementation atlas"
---

## 约束

- 全程离线读取现存源码、冻结表与实测记录；不访问板、VM或远程构建机，不构建运行时，不修改冻结项、部署件或 #91 封板判据。
- 粒度为可解释的 API/能力组，members 列精确符号/类/接口；占位、缺口、真实实现分列，导出符号存在不能冒充功能实现。
- Android 源码版本、API level、APK targetSdk、实际 Android 对照版本、OH 实测版本分开。没有直接证据填 unknown，不从 AOSP 14 或 OH 6.1 单点外推兼容范围。
- 每项声明附仓库相对路径及 SHA256；不同工作树引用用 $WORKSPACES/<tree>/...，不可用个人绝对路径。冻结版本、历史验证版本、当前部署版本分别记录。
- APK 证据按 t20_ui、wall_shift、functional、unit、static、reported 分级；引用历史截图判定须写 reported，不冒称本轮重新看图。日志过墙不等于整个 APK 可用。
- 三个 shard 使用 benchmark/2026-10-12-api-progress/row-template.json 的字段。没有证据保留 unknown 与 gaps，不制造成功状态。
- 只在自己的工作树交件，landing-paths.txt 明确文件；不推送。主表由外环汇总，禁止覆盖其他 shard。

## 已定决策

- 冻结记录及横切能力由 registry shard 负责；Java/JAR/系统服务/安装授权由 java shard 负责；native/JNI/NDK/Bionic/图形音频由 native shard 负责。冻结项允许与功能 shard 交叉引用，最终以 ID 关联不重复计数。
- 覆盖范围是当前仓库已记录的实现与缺口，不声称遍历 Android 全部 API。source-coverage 清单记录检索范围、入选、未分类与缺失材料。
- 人类读物用中文，机器底表 JSON + UTF-8 BOM CSV；benchmark README 用英文，说明历史知识碎片化问题及本次证据规则。
