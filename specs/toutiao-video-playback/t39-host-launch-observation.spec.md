spec: task
name: "T39 host launch callback observation candidate"
inherits: project
depends: [t37-reentry-peer]
satisfies: [REQ-TTVIDEO]
---
## 意图
为快速关闭后重开漏采焦点的问题补充实际宿主启动回调的可保留证据。只交源码可追溯的离线观察候选，后续才能判断启动请求来源；不将观察器或模拟测试当作白屏修复或设备验收。
## 已定决策
- 复用 sources/api-implementations/source-build-host/westlake-java/apps/imehost/EntryAbility.js 的精确 git blob 与 SHA，原件只读；新目录生成候选和可复现补丁，不修改冻结源。
- 候选只在 onCreate(want, launchParam) 与 onNewWant(want, launchParam) 记录启动回调。原窗口、前后台与页面行为保留；不启动应用、不发信号、不写 guardian 状态、不授予重入资格。
- 启动记录与 window-state.json 分离，避免后续 foreground/stage-event 覆盖；每次进程实例和递增序号区分回调，时间戳不充当唯一身份或启动授权。原子替换失败不得把未写成功的记录声称成功。
- 只保留有界白名单字段：回调名、实例标识、序号、时间、数值 launchReason、已知 launchReasonMessage 分类、home action/entity 分类。未知或缺失字段标 unknown，不记录 URI、任意 Want.parameters、caller 个人信息。LaunchReason 与 onNewWant 均不证明人工点击，记录 manual_origin=unverified、eligible_for_reentry=false。
- 以真正候选 EntryAbility.js 在 Node vm 中加载，mock requireNapi/UIAbility/fs/hilog/window；测试调用生产回调而非另写同构模型。原始 argv/stdout/stderr/rc 持久留存，Rust 测试选择器转调该离线检查。
- 不请求设备或网络权限、不用 REA、不调用设备、不构建签名 HAP、不编写或重跑 T38 部署/编排及已拒步骤。此卡只在现有允许的本地文件权限内执行。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-host-launch-observation/**
- tools/spec-checks/tests/toutiao_host_launch_observation.rs
### 禁止
- 不修改 sources/、T36/T37 原件、T38、冻结项、历史签认与其他 agent 文件，不 push，不修改权限配置。
## 验收标准
场景: 两次启动回调与前台事件保持独立
  测试: toutiao_host_launch_observation
  假设精确基线生成了候选且文件系统 mock 正常
  当依次调用 onCreate、onForeground、onNewWant、stage-event
  那么启动序号递增且最新启动记录不会被窗口记录覆盖，原窗口回调行为保持
场景: 缺失及非人工启动原因不授权
  测试: toutiao_host_launch_observation
  假设参数缺失或原因是恢复、自动启动、未知、普通 startAbility
  当生产回调记录该事件
  那么 unknown 明确保留且 eligible_for_reentry 始终 false，无应用启动或 guardian 操作
场景: 敏感及畸形输入不外泄
  测试: toutiao_host_launch_observation
  假设 Want 带 URI、任意参数或超长非白名单字符串
  当记录启动回调
  那么只输出有界白名单字段，不在文件或日志包含输入中的私有哨兵字符串
场景: 写入失败与重复时间戳
  测试: toutiao_host_launch_observation
  假设文件打开、写入或替换失败或者两个回调时间相同
  当执行生产回调
  那么失败可见但不破坏窗口生命周期，不把部分写入当成功，成功事件仍以实例和序号区分
场景: 源码来源与重生成一致
  测试: toutiao_host_launch_observation
  假设基线源码哈希正确或被更改
  当运行候选生成检查
  那么正确基线可重生成逐字相同候选，错误基线拒绝且原始源码未变
## 排除范围
实际点击来源认定、guardian 消费协议、自动恢复、运行时部署、实机画面与声音验收、原神调试均不在本卡。
