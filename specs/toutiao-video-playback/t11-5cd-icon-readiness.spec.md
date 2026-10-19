spec: task
name: "5cd normal-icon readiness without runtime changes"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-static-evidence]
tags: [diagnostic, bounded, human-review]
---
## 意图
在5cd现有独立基线上确认普通图标是否能形成可观测的头条业务进程及真实feed，为后续视频任务补设备身份；不把61b计划迁移过去。此任务只确认就绪条件，不修视频、不调查随机退出、不认证播放。
## 已定决策
- [platform-specific] 唯一设备5cd1e3dd00000000000000000923012c，外环持独占锁，锁窗最多600秒，验证外环window-start后固定剩余monotonic预算；执行前核只读凭证BASE20/alternate-board-readonly/20261020T062401/5cd及最新boot，当前凭证boot为0525bb05-f714-42ad-90f0-ecdb10356c4f。原project允许空闲5cd，不更改61b限定的t8。
- 仅允许外环正常桌面图标启动一次及snapshot_display截图；若外环亲读真实feed且同child仍活，可按实际截图一次普通视频tab/打开可见视频，无未知坐标猜测；最多一轮普通UI流程，没feed立即unknown收口。不shell启动、不自动重试UI、不部署、不重启、不attach、不写进程内存、不改设置/应用数据。仅允许本窗独占设备目录中的uitest dumpLayout JSON和snapshot临时文件，不写其他文件；不调用修改屏幕超时的power-shell命令；未知业务状态不得触发恢复脚本或停止现有服务。
- 当前run为5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79，cfg为19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152；运行时路径及源码文件SHA取该板凭证profile，不引用61b控制目录。UID20011300，不是20011206；PID3966/birth3839的entry.sh不是业务parent。
- `collect.py`默认本地preview，必须显式execute才读白名单设备。首次采集未启动的ps/maps状态，外环单图标后最多一个新child；ps完整NAME使用com.ss.android.article.news，stat按PID/birth/PPID校验，不用截短comm发现。第二次after-ui采集必须用--identity-receipt绑定第一次回执的parent/child PID、birth、UID，拒绝另选实例。记录新parent/child UID、exe SHA、boot前后及真实WID原始窗口证据，WID29是旧run值不得默认当前。
- 五角色player/android/shim/bridge/hwui逐个记录当前maps、私有文件SHA/device/inode、已证ELF加载偏移；磁盘存在不等于映射。本版执行禁止GOT读取，--player-elf仅离线preview可用，execute指定则拒绝；GOT明确unknown。后续独立版本若读GOT仍须本板精确ELF、slot可读映射及文件身份前后夹验，不能复用本版单次maps；不读取对象、不沿未知指针追踪。精确输入缺失、未加载或多实例歧义均为unknown，不套61b地址或provider偏移。
- 无业务进程、退出、身份变化、模块缺失、网络/服务拒绝、命令错误或到限保存原始命令/rc/失败并结束；本契约禁止回滚式重启，保持设备现状并释放本任务锁，需额外恢复由外环另行决定。原凭证及本次采集落持久目录，公开摘要不含媒体URL或用户数据。
- 机械测试只核离线选择/拒绝/回执结构，截图与WID归属由独立human审核；lifecycle strict未签认保持pending_review。机器rc0、进程存活或READY不代表feed，更不代表有声动态视频。
## 边界
### 允许修改
- benchmark/2026-10-20-5cd-icon-readiness/**
- specs/toutiao-video-playback/t11-5cd-icon-readiness.spec.md
- tools/spec-checks/tests/toutiao_5cd_icon_readiness.rs
### 禁止
- 不改project、t8、原observer、冻结源码、运行时、已有原始记录或其他板；不推送，不作随机退出根因研究。
## 完成条件
### Rule: isolated-current-readiness — 本板身份先于结论
场景: 离线预览与精确设备拒绝
  测试: ttvideo_5cd_readiness_admission
  假设 profile来自5cd原凭证且命令为preview或指定错误serial、UID、run或cfg
  当 校验collect.py输入与输出计划
  那么 preview设备调用为0，错误输入拒绝且不启动或写入设备
场景: 新业务身份及只读证据
  测试: ttvideo_5cd_readiness_identity
  审核: human
  假设 外环已持5cd锁且一次正常图标后出现新业务child
  当 采集完整ps名称、stat前后、UID、exe、maps及WID证据
  那么 parent与child依据当前PPID和birth绑定，entry.sh不冒认业务parent，五模块只按本板证据记录，本版GOT保持unknown
场景: 身份漂移或未知地址拒绝
  测试: ttvideo_5cd_readiness_identity
  假设 boot或birth变化、多child、UID错误或GOT槽不在当前可读映射
  当 尝试继续采集或execute传入--player-elf
  那么 停止相关读取并记录unknown或refused，不解引用未知对象，不另选child或重启
场景: 缺模块无进程与到限保留事实
  测试: ttvideo_5cd_readiness_receipt
  审核: human
  假设 单次图标未产生child、模块未映射或600秒到限
  当 结束窗口并保存命令rc与截图回执
  那么 缺项明确unknown且无attach部署重启或第二次启动，释放锁并保留失败原件
场景: 真实feed与单轮视频UI独立审核
  测试: ttvideo_5cd_readiness_receipt
  审核: human
  假设 已保存snapshot_display截图与当前WID归属证据，外环确认feed且同child仍活
  当 外环按实际截图做一次视频tab或打开可见视频并独立审核原始采集记录
  那么 feed亮不等于player准入，实际模块与日志另记；机器通过仅pending_review，播放与声音仍unknown，没feed或child退出立即结束不再点图标
## 排除范围
- 视频修复/播放认证、公共API修复、runtime统一态迁移、调试器、对象字段探测、数据清理及远程推送。
