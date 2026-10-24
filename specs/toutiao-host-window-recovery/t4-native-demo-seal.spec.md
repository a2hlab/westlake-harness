spec: task
name: "Native host recovery retained demo qualification"
inherits: project
satisfies: [REQ-TTHOST]
depends: [t3-native-window-validation]
tags: [native, window, demo, human-review]
---
## 意图
在t3真实短窗验证通过且已回滚闭窗、受支持方式恢复执行通道之后，验证61b普通软件重启后的头条首开与宿主重建，并最终保留已验证候选。两个独立软件boot的真实可操作画面和恢复依据才构成演示留板资格；离线测试和t3临时成功后回滚均不构成封板。
## 已定决策
- 前置证据是t3实际候选加载和UI图审通过、精确基线回滚及闭窗回执，以及执行通道经受支持方式恢复的可核证据。CC的reasoning_extraction停止仍有效；支持发送、自动回复或请求人工复核都不是恢复，不改权限、不换模型或入口重试停止动作。
- 仅61b0657200000000000000000324012c，由外环固定唯一持锁执行方与计划SHA。候选沿用通过t3的完整SHA及源码、真实构建、审查链；当前候选3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819，若变更必须重新通过t3，不用旧158c构建或fixture替代。
- 写前fresh核boot、host/parent/child的PID/birth/UID、目标maps dev/inode与process-root SHA、backing绝对路径及metadata、电源/屏幕设置、非目标指纹。仅更新t3已证的应用liboh_adapter_bridge.so payload；root系统8ab库不变。保存精确b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4回滚原字节、SHA、uid/gid/mode/标签与原子恢复步骤。冻结门既有红灯不得静默放宽。
- 至少两个独立普通软件重启产生不同boot ID；每个boot重新核实际新child加载候选。启动流程覆盖payload则实验不成立并恢复，不改控制器应对、不反复换库。软件boot不得写为物理断电验证。
- 每个boot按顺序验桌面单击首次feed并正常滑动、Home后同host返回、Recent正常关闭宿主后桌面单击新host旧child重开。每阶段至多一次图标点击；新host以PID/birth身份变化证明，旧child必须保持同boot/PID/birth/UID，newchild不是重关联通过。保留APK数据、网络、权限和正常启动逻辑，不用shell启动替代桌面操作。
- 每阶段沿用t3最多120秒观察界限，保存实际点击、截图、首个feed及触控耗时，不称性能SLA。两boot均需人工核feed可触控、正常内容输入响应与候选运行的视频实际画面推进及音频输出。优先复用已有可用采证通路，不默认每轮重复向用户询问声音；音频证据必须绑定本候选SHA、boot、播放阶段及实际观测方式和限制，旧版本用户实听确认不得替代新候选实听。无法观测音频或只有输出接口状态时音频保留结论为pending，不称全部行为保留；仅静态视频帧、READY或存活不能代替视频/音频/输入证据。同host返回的资源身份缺证写unknown，不由截图推导producer未变。
- 每窗单调LOCK起点后900秒停止新增试验，1200秒前开始失败恢复或成功闭窗核验，1800秒内结束释锁；若需分两窗，每窗独立准入、闭窗和交接，未完成两boot前不得宣布最终封板。全部阶段通过后最终保留实测候选，核当前运行件SHA、非目标件、原电源设置和最终图审，记录实际留板状态及可执行的精确回滚依据。
- 任一实质失败、身份漂移或未知写结果即停止新增动作；未知写先只读核实，不重复提交。失败恢复b0e及原metadata，必要时仅按已核方案普通恢复重启，核实际基线映射后闭窗。恢复失败写recovery_required并交接唯一锁；候选失败但回滚成功只算已恢复，不算白屏修复或封板。
- 原argv/start/end/transport与remote rc/正文错误/截图和facts持久保存，视频画面推进和音频输出证据及观测限制分别记录；公开脱敏索引和SHA，图审署明审核者与图像SHA。收据真实性、设备结果、恢复、视觉和留板状态分列，synthetic fixture不得升级实际验收。
## 边界
### 允许修改
- benchmark/2026-10-24-native-host-window-recovery/demo-seal/**
- tools/spec-checks/tests/host_window_native_demo_seal.rs
### 禁止
- 修改project/t1/t2/t3及已冻结计划、运行时实现、其他板、HAP/JAR/APK数据、系统bridge、停止控制器/执行器/配置及等价重试、权限/例外表、REA、物理断电、推送。
## 验收标准
场景: 前置或执行恢复证据缺失
  测试: host_window_native_demo_seal_receipts
  假设只有离线测试或支持自动回复或t3未实际通过并回滚闭窗
  当评审留板准入
  那么状态为blocked且不得启动设备窗口或将支持请求当执行恢复
场景: 两个软件boot的普通UI验收
  审核: human
  测试: host_window_native_demo_seal_receipts
  假设两个不同boot均持锁并证实际child加载同一已签候选
  当逐boot核桌面首开Home返回及Recent新host旧child重开的原件和输入视频图审
  那么三个阶段均有可操作feed及候选视频画面推进音频输出和输入保留证据且实际耗时逐项记录而不声称性能SLA或物理断电通过
场景: 重开身份或映射错误
  测试: host_window_native_demo_seal_receipts
  假设重开换了child或host未重建或新boot实际映射不是候选
  当核PID/birth/UID与maps对象
  那么该阶段失败或不成立且不以newchild或磁盘SHA报重关联成功并进入恢复
场景: 白屏或视觉证据不足
  审核: human
  测试: host_window_native_demo_seal_receipts
  假设阶段120秒内无可操作feed或视频只有静态帧或音频仅有旧版本实听确认或无法观测或只有synthetic截图和READY
  当核图像SHA与人工操作审核
  那么拒绝对应项通过并保留实际时长和缺项且音频无法观测保持pending而不称全部保留或以回滚成功替代修复
场景: 超时或未知写结果
  测试: host_window_native_demo_seal_receipts
  假设命令结果未知或窗口达到900秒或出现身份漂移
  当结束新增实验
  那么不重发未知写且按1200秒恢复起点和1800秒闭窗边界核实际收据并保留超时偏差
场景: 最终候选留板与失败恢复分离
  审核: human
  测试: host_window_native_demo_seal_receipts
  假设两个boot完整通过或其中一个失败
  当核最终运行SHA非目标指纹电源图审及锁释放
  那么仅全通过且最终保留候选才记录sealed_software_boot_validated否则记录restored或recovery_required并保留回滚材料
## 排除范围
本轮仅写规划不执行设备；该Rust选择器尚未实现为pending，后继实现只能检查收据，fixture和parse/lint不证明实板。随机退出归因、停止对象、系统重构和冻结新API不在本任务范围。
