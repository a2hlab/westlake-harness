spec: task
name: "Toutiao video dynamic playback and API delivery"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t2-minimal-repair, t4-player-observation]
tags: [media, waiting-for-p1-window, human-review]
---
## 意图
在61b（唯一RouteB同代板）于图标P0锁释放后的外环窗口验证候选实际播放，并与图标重开主任务合流。交付有声动态帧、暂停恢复退出证据与实现/构建/API表对照，不把一张封面或探针结果当头条通过。
## 已定决策
- 外环分配serial并持板锁，开窗前核只读身份与原回滚；5cd(run.sh 5a3aef63)与5ea均非RouteB同代，故只在61b验证，须在图标P0锁释放后另开窗口，先过t2候选的P1加载窗（candidate/OPERATIONS.md）再做播放周期。APK/视频内容/网络条件和runtime指纹均记录；run.sh由固定模板仅替换WL_PARENT_ID为实际WID，按派生前像/后像完整SHA核对，不以归一化SHA作采认。
- 两个周期各播放20秒、暂停3秒、恢复10秒、退出回feed并手点图标再次进入；120秒观察窗包含视频进入与回退，超出30分钟实验限时则保存未完证据并回滚解锁。
- 每周期采t0/t5/t10/t20及暂停/恢复/退出snapshot_display，记录视频内容ROI、播放时间与对应Surface；内容帧变化排除spinner/字幕/控件假动，声音须外部录音或人工听验具名回执，音频计数不能替代听到声音。
- 更新独立API增量表：精确API→源码blob/commit→构建配方→产物SHA→OH完整版本/ABI→APK SHA与targetSdk→实测范围与证据；生成与当前主表的合并清单，由外环统一出版，历史版本/unknown不改写。
- 失败保留运行目录/facts并按原基线回滚；没有第二个app验证同API时标unfrozen。正式合代码与远程发布由外环执行。
- r4部署执行器沿已验r5仅增加libttmplayer派生件，形成run/compat/mffmpeg/player四件；新后像未审定时UNAPPROVED必须在设备调用前拒绝。只读核父进程boot/birth、物理与private-view同inode、四件前像SHA及metadata；run/media/player三份完整备份都在首个swap前建立并验证。每个rename紧邻旧SHA/metadata CAS；回滚必须绑定原apply-plan及原boot备份，known pre/post可恢复、foreign拒绝，不删历史或父进程。apply/rollback后均fresh boot，30分钟窗口与原播放门不变。
- r5只作诊断时沿用已核r4四件，不新增运行时二进制；只有精确播放器REA证明JNI_OnLoad读取debug.ttplayer.log.enable并接受true、实际provider与OH参数恢复路径已绑定后，才允许在fresh boot后、真实图标启动前临时设置该单键true。先保存原值或明确absent（errNum106）及原始远端回执；禁用file日志模式，不改变安全策略。原absent必须在回滚fresh boot后再次读为absent，空串不算恢复；日志开关未读到true、诊断无结论或窗口到限也恢复四件与参数并核真实feed，诊断成功不降低两轮有声播放验收。
- r8为t4离线候选的独立短窗：player为0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471，compat为6e83e924aae709f0c90ba2a966910febb63471b7a9a6294c6dee585a73ff3b4b；run79275cf9与media d2882303模板不变。来源与原始构建日志见candidate-r8/archive-receipt.json，独立离线审查见video-1919-r8-elf-review。继承四件备份/CAS/原apply-plan回滚，未定后像仍在设备调用前拒绝；不部署链接输入liblog或OpenSL anchor，不改系统运行时。
- r8 fresh boot后先按r5精确参数路径启日志，再真实图标进入feed并触发视频；一次采齐实际player GOT0x471f88→本次compat+0x1aac、compat GOT0x3258→exact d8ad liblog+0x7450，以及映射SHA/inode/load bias。缺任一绑定时仅记unknown，不把DT_NEEDED或编译通过当运行时解析证明。沿现有child fd2收有界镜像，原始payload只在私有持久归档。镜像无输出不能证明播放器从未执行；按真实画面和原两轮声音门裁定，到限仍按原基线恢复与参数absent、feed核验后解锁。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/diagnostic-r5/**
- benchmark/2026-10-19-toutiao-video-playback/runs/**
- benchmark/2026-10-19-toutiao-video-playback/api-delta/**
- benchmark/2026-10-19-toutiao-video-playback/candidate-r8/deployment/**
- benchmark/2026-10-19-toutiao-rea-methods/video-r4-executor-draft/**
- specs/toutiao-video-playback/t3-playback-seal.spec.md
### 禁止
- 不夺板锁、不覆盖历史签认、不重签旧boot、不改冻结登记或主API表历史证据；不删用户数据。
## 完成条件

### Rule: evidence-before-verdict — 先绑定证据再判断
场景: 两轮有声播放暂停恢复退出
  测试: ttvideo_playback_receipt
  审核: human
  假设 61b serial已由外环分配且持板锁，只读身份及真实APK和候选SHA及原回滚均核对
  当 在120秒观察窗按两轮20秒播放3秒暂停10秒恢复及退出序列执行并保存t0/t5/t10/t20的snapshot_display与ROI和声音回执
  那么 两轮视频内容持续变化、声音与内容对应、暂停停止前进、恢复继续、退出显示feed且图标可再打开
  并且 保留按实际captured计数的facts而非计划截图数
场景: 封面冻结静音或服务拒绝拒绝通过
  测试: ttvideo_playback_receipt
  审核: human
  假设 只有封面变化或无听验或网络服务拒绝
  当 审查当前boot证据
  那么 记failed或external_blocked而非playback_pass并保留原始证据和facts回滚结果；30分钟超时同样回滚解锁
场景: 图标任务占锁与回归拒绝
  测试: ttvideo_playback_receipt
  审核: human
  假设 61b仍由图标任务占用或候选使图文入口回归
  当 准备61b发布
  那么 不写61b且前者等释放后重排，后者回滚并禁止封板
场景: API源码构建实测对应
  测试: ttvideo_playback_receipt
  审核: human
  假设 实测结论与候选源构建证据已定
  当 生成api-delta与主表合并清单
  那么 每个变化API有源码blob/commit、构建配方、产物SHA、OH完整版本/ABI、APK SHA/targetSdk和实测边界且只有单app时冻结状态为unfrozen
场景: 未批准后像与漂移拒绝部署
  测试: ttvideo_playback_receipt
  审核: human
  假设 四件执行器后像仍为UNAPPROVED或现场前像SHA与metadata或父private-view身份漂移
  当 请求部署候选
  那么 UNAPPROVED在设备调用前拒绝，其余漂移在目标写入前拒绝，并保留明确错误回执
场景: 部分执行失败的原基线回滚
  测试: ttvideo_playback_receipt
  审核: human
  假设 四件候选的run与media与player原件备份已验证且部分目标仍为known pre或post状态
  当 使用原apply-plan执行回滚
  那么 逐件CAS恢复原件并核metadata，移除仅有的已知compat，fresh boot后核原前像和真实feed
  并且 foreign目标或缺失备份拒绝自动覆盖，不声称任意中断都能恢复
场景: 日志开关必须绑定实际消费者与可恢复前像
  测试: ttvideo_playback_receipt
  审核: human
  假设 计划临时设置debug.ttplayer.log.enable以观察prepare后的真实播放状态
  当 核查REA读取时点和值、实际provider及原参数值或absent前像和恢复依据
  那么 任一项unknown时拒绝参数写入且保留static-only结论，不以日志缺失推断解码未启动
场景: 诊断日志不替代播放且恢复原参数缺失态
  测试: ttvideo_playback_receipt
  审核: human
  假设 r4四件已过只读检查并在独占30分钟窗口中临时开启日志true
  当 实际图标启动和视频操作后采集回调及原始日志并结束窗口
  那么 只按日志证明具体播放阶段，未见动态声音仍NOT_PASSED，并按原apply-plan恢复四件和fresh boot后原参数态
  并且 原absent须实际读回errNum106，恢复真实feed后释放板锁，空字符串或仅transport rc0不得冒充参数恢复
场景: r8诊断必须核实际双向绑定并保留播放判据
  测试: ttvideo_playback_receipt
  审核: human
  假设 r8离线来源与构建及回滚已复审且61b持独占锁
  当 fresh boot后真实图标进入视频并读取player到compat以及compat到liblog的实际GOT和映射身份
  那么 只有两跳精确匹配才记诊断接线成立，缺失则unknown；日志镜像不替代动态帧与声音，失败或到限恢复原四件参数和feed
## 排除范围
- 随机崩溃根因、安全机制改造、用户数据清理和自动远程推送。
