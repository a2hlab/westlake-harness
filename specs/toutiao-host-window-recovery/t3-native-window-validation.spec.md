spec: task
name: "Native host window recovery bounded device validation"
inherits: project
satisfies: [REQ-TTHOST]
depends: [t2-native-session-recovery]
tags: [native, window, validation, draft]
---
## 意图
在61b一次可回滚短窗中验证已采认native候选的实际加载、正常桌面打开与最近任务关闭宿主后重开的信息流及触控。先核当前应用实际消费的单库payload、候选来源与精确回滚，再以新boot和新child的maps及SHA验生效；本契约的起草和lint不构成设备执行或候选签认。
## 已定决策
- 2026-10-25 外环具名准入例外 `idle-app-same-boot-restored-object`：T136恢复窗已核baseline-s30的真实maps/process-root/backing，之后同boot子进程退出，不再要求故障应用先启动才允许普通单库维护。仅当当前child数量恰为0、boot与host/parent的PID/birth/UID均和这份已恢复收据一致、目标fresh stat全部字段及完整SHA与原收据对象一致时，允许以`mapping_now=not_running`准入；收据文件SHA须固定进外环执行签认，持锁后再次核同一条件。若存在1个child仍走原严格maps检查，超过1个或任何身份/对象漂移均拒绝。本例外只适用于部署前，绝不替代新候选新boot新child实际maps验证、截图验收、冻结门或精确回滚。依据：T136 execute-20261025-024115-2e76dc/baseline-s30-binding.json及execute-20261025-024653-611cef fresh身份原件；当前未运行不宣称当前已映射。
- 前置为t2最终源码manifest、真实构建日志、库完整SHA与CC/外环采认回执一致；候选以最新snapshot02的3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819和最终审查为准，未齐时保持candidate_pending，不把旧build01的158c1740填为新候选。执行前外环另固定单写者、实际计划SHA及恢复材料。
- 仅61b0657200000000000000000324012c；写前fresh核设备、锁、boot、host/parent/child PID及birth/UID、maps、目标stat/SHA/标签、挂载来源、原电源/屏幕态与可恢复基线。旧child22035/b6535369仅是来源证据，不作为后继命令固定PID。
- 已采child映射路径为/data/local/tmp/asx/liboh_adapter_bridge.so，SHA b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4；mountinfo指向/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d。该来源下同名库仅是待fresh绑定的发布目标，必须和child映射对象dev/inode及SHA相符；root的/system/android/lib64/liboh_adapter_bridge.so为8ab85446，不在替换范围。
- 本次明确授权的范围是普通库payload单件部署与精确回滚，不新增用户审批。既有发布/恢复metadata仅用于核定目标与恢复依据；写前落实原字节备份、同文件系统原子替换步骤、原metadata回读和回滚步骤。若发现具体既有门禁拒绝或实际操作必须触及停止对象，保留证据并停止该动作；不阅读停止控制器/执行器/.env，不伪造批准/owned state，不改门禁或权限。
- 核冻结门的登记源和实际映射artifact；0 checked不算内容验证，已有红灯保留并交外环。仅对已fresh绑定的当前库payload做同文件系统临时文件校验后原子rename；先持久保存精确b0e原字节及uid/gid/mode/SELinux标签和恢复路径，按已批准metadata赋权回读，不原位覆盖已映射inode，不改其他库/JAR/HAP/boot镜像。
- 上游正常安装/启动流程是否覆盖payload是本次受控重启要回答的运行时未知，不要求先证明不会覆盖才准许实验。正常软件重启一次后，重新绑定boot及新child身份，核maps dev/inode、process-root路径stat/SHA及实际候选读取/恢复普通日志；候选SHA不在实际新child映射中即activation_failed并判实验不成立，停止候选UI验收并走恢复，不靠重复替换、改启动流程或root磁盘SHA报通过。
- 普通UI按顺序进行：桌面图标首次打开；Home后同一宿主正常返回；Recent向上关闭自有宿主后再次桌面打开。每阶段至多一次图标点击，先核可见桌面/窗口，截图与日志使用实际时间；须有新host出生且旧child身份保持才算重关联测试有效。若child退出或更换，只记录该事实，不分析退出原因、不把新child启动当旧child恢复。
- 每阶段图标后最多观察120秒，采5/30/60/120秒截图或实际提前结束帧；首次信息流后仅正常滑动和一篇内容/视频的已批准普通触控核验，不登录、不清数据、不改网络/权限。窗口/READY/进程存活不能替代外环目读的信息流与操作后截图。同host返回不更换渲染资源，新的host关联须记录逻辑/实际ID和已有普通候选日志；资源身份不可观察时明确unknown而不宣布producer保持已实证。
- 唯一持锁方以单调时钟记LOCK起点：900秒停止新增实验，1200秒前开始恢复，1800秒内完成闭窗解锁。单命令使用既有有界入口，未知写结果先停止发新写并只读核实，不重复提交；身份漂移/首个实质失败立即提前恢复，不等满观察时限。
- 本验证窗无论通过或失败均按已核定的回滚步骤恢复精确b0e payload及原metadata，需要清除候选映射时仅进行一次正常恢复软件重启；核恢复后新child实际加载基线、非目标manifest项未变、原电源/屏幕设置恢复、最终截图并释放锁。恢复本身失败或身份不明时保留recovery_required及单写者交接，不假报健康或自动并发救援；候选长期保留和物理断电验收另派。
- 每条实际命令先持久argv/start，再写end/rc/stdout/stderr，区分transport和remote结果及正文错误；facts从真实截图/进程表生成。原始日志私有持久存储，公开仅脱敏摘要、原件SHA与路径别名；离线收据检查不自动执行设备命令。
## 边界
### 允许修改
- benchmark/2026-10-24-native-host-window-recovery/device-plan/**
- benchmark/2026-10-24-native-host-window-recovery/device-validation/**
- tools/spec-checks/tests/host_window_native_validation.rs
### 禁止
- 本次起草阶段设备或远程调用、部署脚本；后续未经外环固定执行计划的设备写入。
- 其他两板、root系统bridge、其他runtime件、APK数据、HAP/Java/JAR、原冻结源、停止的控制器/执行器/配置及其等价重试、REA、hook、进程信号、权限和例外表修改、推送。
## 验收标准
场景: 已恢复同对象在应用退出后允许普通部署准入
  测试: host_window_native_validation_receipts
  假设实际已恢复映射收据被完整SHA固定且fresh child恰为0
  当同boot和host及parent身份不变且目标stat全字段及SHA一致并持锁后重复核对
  那么只登记idle-app-same-boot-restored-object准入且mapping_now为not_running并且候选仍须另取新boot真实加载和图审证据
场景: 应用未运行例外不得容许来源或对象漂移
  测试: host_window_native_validation_receipts
  假设来源收据SHA不符或boot及host或parent漂移或目标对象字段改变或child多于1个
  当检查idle-app-same-boot-restored-object例外
  那么拒绝发布且保留具体差异并且不得用历史maps冒充当前映射
场景: 候选或发布前置缺失时拒写
  测试: host_window_native_validation_receipts
  假设候选来源审查未齐或目标backing身份或精确原像回滚步骤缺证或冻结门不符
  当核只读准入与原件引用
  那么报告具体缺项且设备写操作为0并且不生成虚构签认
场景: 正确单库替换与精确备份
  测试: host_window_native_validation_receipts
  假设候选已采认且精确回滚已核定并持有61b唯一锁完成fresh绑定
  当核实际发布收据
  那么只允许已绑定应用payload原子替换且b0e备份和metadata可回读并且系统8ab及非目标件保持原指纹
场景: 重启覆盖或映射身份不符
  测试: host_window_native_validation_receipts
  假设重启后磁盘为候选但实际新child映射为原库或其他SHA或身份无法夹持
  当核新boot的maps与process-root对象
  那么判activation_failed及实验不成立并停止候选UI验收且不重复替换或修改启动流程
场景: 桌面首开与正常重开图审
  审核: human
  测试: host_window_native_validation_receipts
  假设新child已证加载候选且三个普通UI阶段身份和时间证据齐全
  当外环核首次信息流同host返回及新host旧child重关联后的截图与触控结果
  那么仅实际可操作feed及内容验证记录为通过并且逻辑实际ID与资源观测缺项仍单列unknown
场景: 白屏或child更换不假通过
  审核: human
  测试: host_window_native_validation_receipts
  假设某阶段120秒内无可操作feed或旧child退出更换或只有READY与进程证据
  当核实际截图与身份序列
  那么该阶段失败或不成立且保留首个错误并提前恢复而不归因退出原因
场景: 未知写结果与窗口超时
  测试: host_window_native_validation_receipts
  假设写入结果未知或已经达到LOCK后900秒
  当窗口停止新增动作
  那么不重复提交未知写且1200秒前进入恢复并在1800秒闭窗或明确recovery_required
场景: 精确恢复与最终闭窗
  审核: human
  测试: host_window_native_validation_receipts
  假设候选观察结束或失败且原回滚材料可用
  当核恢复后新child映射基线非目标指纹原电源设置和最终截图
  那么仅证据完整才报告已恢复并释锁且缺项或超时不能写成全流程PASS
## 排除范围
本次起草不实现收据检查器或部署执行器，不实际运行设备测试；测试选择器由后续执行任务实现，parse/lint通过不等于选择器已运行。系统WMS修改、控制器改造、全部bridge源码重建、随机退出归因、物理断电与永久封板不在本窗范围。
## 问题
- 当前payload的精确宿主可见路径、inode/标签与回滚原像还需同窗fresh证据；mountinfo推导不替代实际文件绑定。
- 正常软件启动是否重拷或校验覆盖该payload由本实验回答，不是写前阻塞或额外审批；仅以新child真实maps/SHA判生效，不修改停止对象应对。
- 最新snapshot02的3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819完整SHA、来源构建和最终采认须在执行plan中逐项固定；旧build01只作历史。
