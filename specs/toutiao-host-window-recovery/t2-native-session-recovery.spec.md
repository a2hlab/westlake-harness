spec: task
name: "Native session recovery preserving the rendering producer"
inherits: project
satisfies: [REQ-TTHOST]
depends: [t1-window-record-reader]
tags: [native, window, recovery]
---
## 意图
在精确Ability38/Focus34基线的独立源码候选中，接通宿主窗口更换后的正常SSM子会话重建。保留Android逻辑session及已有渲染资源，更新鸿蒙实际会话与输入映射；先形成真实接入生产调用路径的可编译候选，部署验收另立任务。
## 已定决策
- 来源为Ability38 WMC源1844e81b、已归档Input源码及T29现役bridge b0e5602a的构建输入；每个新增修改对象均核来源，未知映射列明，不能用较老base对象替换。只在独立candidate源码目录派生，不改冻结原件。
- 只为精确头条包的成功初始会话启用正常窗口记录观察；复用t1生产reader。路径来自已证同应用模块数据路径，核实际UID/GID，不读取控制配置、不创建额外进程或发信号。root路径可见不算child读取通过。
- 普通记录来自同UID/GID私有模块文件，只是同应用候选来源。通过对应OH普通GetParentMainWindowId接口核candidate为当前main；只有WM_OK且返回id等于candidate才接受。旧parent仍有效、查询拒绝/结果未知或记录无id时不重建。不申请权限，不绕过系统调用门禁，不将这些检查称为SSM宿主owner证明。
- 现有成功记录的host父ID与新候选不同才尝试；每1000ms至多一次检测，读取和IPC遵守实际API的有界机制；每个候选文件身份至多一次在途事务，结果未知停止该事务且不得紧循环重建。普通前后台和重复记录不更换producer。
- 新SSM子会话提交原APP_WINDOW节点；保留其内容node、ProducerSurface、NativeWindow、Java逻辑session与SurfaceControl关联。不得走现有完整destroySurface或destroySession来准备重连。
- 显式分离逻辑session与实际persistentID；Java/Surface查询保留逻辑ID，focus、SSM销毁、remote操作、子窗口父关系使用实际ID。MMI输入在GetAgentWindowId后先翻译实际ID到逻辑ID，再复用原publisher；旧实际ID拒绝，不能因activeSessionId更新就宣称触控恢复。
- 新remote与实际ID先暂存，创建及必要连接步骤成功后提交映射。失败不发布已恢复，不释放原producer；仅清理本事务新会话，未知IPC结果保留证据停止而非再次创建。旧callback不能清除已提交新关联，callback身份与并发顺序显式处理。
- 代码须接入候选WMC/Input真实调用位置，并提供原始源码SHA、补丁、构建输入差异和真实测试日志。单独mock模型或没有生产调用的helper不算候选完成。
## 边界
### 允许修改
- benchmark/2026-10-24-native-host-window-recovery/session-recovery/**
- tools/spec-checks/tests/host_window_session_recovery.rs
### 禁止
- 修改原冻结源、现役产物、HAP/Java/JAR、设备、启动/杀进程/信号、控制器执行器配置、权限、REA和推送。
## 验收标准
场景: 新host事务保持渲染身份
  测试: host_window_session_recovery_fixtures
  假设逻辑session53及其两层node和producer存在而旧host32失效且候选62为main
  当生产协调代码通过受控SSM端口创建实际session63并提交
  那么逻辑53仍查询到同一渲染资源且focus和销毁发送实际63而输入63映射回逻辑53
场景: 同host与重复记录
  测试: host_window_session_recovery_fixtures
  假设host未变或候选记录被重复读取
  当观察路径处理记录
  那么不创建新会话不重建producer且每代最多一个事务
场景: 候选或旧父不满足准入
  测试: host_window_session_recovery_fixtures
  假设缺id或候选不是main或旧父仍有效或查询拒绝
  当生产协调代码核准入
  那么不发起创建并保留当前逻辑关联
场景: 部分失败或IPC结果未知
  测试: host_window_session_recovery_fixtures
  假设创建或后续接入步骤失败或返回结果未知
  当事务退出
  那么不发布新关联且原producer不被释放并且未知结果不触发重复创建
场景: 输入与迟到旧回调
  测试: host_window_session_recovery_fixtures
  假设新实际session63已提交到逻辑53且旧实际53已退役
  当输入63和旧实际53事件以及旧代回调到达
  那么63使用原publisher而旧事件不清理新关联且无全局输入监听新增
场景: 生产接线与未验证边界
  测试: host_window_session_recovery_fixtures
  假设候选源与当前对象差异清单齐备
  当核验候选WMC和Input的真实调用接线并编译测试
  那么没有未接入helper或始终通过的认证stub且报告明确child读取节点接纳和可操作feed仍需实机验证
## 排除范围
本轮上板与封板、冷启动延迟优化、随机崩溃根因、系统WMS修改、APK修改；这些排除仅限定本任务，REQ-TTHOST与主目标继续有效。
