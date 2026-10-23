spec: task
name: "T80 Android APK and runtime identity versus successful evidence"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t78-current-host-package-binding]
---
## 意图
宿主 HAP 一致不代表头条 APK 与 ART/JAR/native 运行时一致。对照当前 61b 与 T34/T61B/T72 成功画面绑定的制品证据，先判断是否存在可验证的部署版本漂移；不把版本相同等同于运行行为相同。
## 已定决策
- Codex A 车道仅离线读取 T77 引用、T34/T61/T70/T72 既有制品记录及持久证据，列头条 APK、ART、BCP JAR、主要桥接 native 的实际路径、SHA、来源和成功样本绑定强度。缺 SHA 或版本绑定就 unknown，不从“未部署”措辞推导相同。5 分钟首交 A/results.json 与 expected-files.json，不访问设备或 REA。
- CC B 车道只对白名单 61b0657200000000000000000324012c 先查锁/boot；复用 T70 及既有 runtime-fingerprint 的已知路径，从只读包/运行时目录和链接定位当前实际制品，最多 40 个精确文件 SHA。可读普通进程命令行辨别部署代，但不读取内存、maps、故障、guardians/watchdog/reentry 实现。8 分钟首交 B/results.json 和原始命令回执，不启动 app、不改设备。
- 两车道分别写 A/ 和 B/，外环交叉核路径与哈希，不互改文件。路径或指纹缺失不能猜；读取失败停止该项，保留原文，不改权限。文件名匹配不能代替实际位置，备份件不能充当前件。
- 最终表逐项分类 match/different/unknown；确定差异须附成功版本来源与当前真实路径，不自动回滚、不将差异推为根因。没有差异则明确这轮未产生修复候选。原神和全量 APK 暂停。
- A 交路径不重试 git ref；B 只提交 analysis/t80-runtime-identity 的 B 报告，不推送。证据存持久目录，公开报告不含凭据、账号或个人数据；人工验收，不声明未实现测试通过。
## 边界
### 允许修改
- benchmark/2026-10-23-apk-runtime-identity-comparison/A/**
- benchmark/2026-10-23-apk-runtime-identity-comparison/B/**
- 私有 $HOME/.local/share/westlake/apk-runtime-identity-20261023/**
### 禁止
- 运行时改动、部署、重启、点击、故障/内存/反虚拟化分析、T71/T74被停止源码诊断、其他板、网络或权限变更
## 验收标准
场景: 成功记录与当前制品存在绑定明确的差异
  审核: human
  测试: apk_runtime_identity_comparison_review
  假设成功样本记录了同角色制品的路径和 SHA
  当离线 A 与只读 B 对齐实际部署对象
  那么逐项提供来源回执和 different，不将同名备份误作当前对象或自动回滚
场景: 匹配或缺少可信绑定
  审核: human
  测试: apk_runtime_identity_comparison_review
  假设制品 SHA 一致、历史证据不足或当前读取失败
  当对照表收口
  那么分别记 match 或 unknown，保留失败回执，未定位原因不声称修复或封板
## 排除范围
第三方崩溃原因、守护程序源码分析、修复构建、上板验收和任何安全策略修改。
