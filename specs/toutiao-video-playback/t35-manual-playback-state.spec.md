spec: task
name: "T35 preserve manual video freeze on 5cd and 61b"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
用户报告5cd及61b手点视频后进度条移动、画面停封面或首帧。先保留当前人工操作现场，判断当前视频帧与播放链状态，核对与已签认视频版本的差异；不把历史自动操作成功解释成人工路径已覆盖。
## 已定决策
- 仅5cd1e3dd00000000000000000923012c及61b0657200000000000000000324012c，只读观察；先核板在线/锁/boot与现存child身份，遇别的写任务不竞争。原神5ea与G08离线分析继续。
- 不点击、不唤醒、不重开头条、不改变播放/音量/网络/前台，不重启或部署，不调用REA、不调查随机崩溃。snapshot_display写入唯一诊断文件后接收属于观察，其他设备配置和app状态不写。
- 每板按现状采三张间隔至少2秒的实际截图，保存原始argv/rc/时间/哈希，root读图；若锁屏/不在视频或用户已切换，记录现场不可观测，不自动恢复现场。不能以进度条变化或进程存活判视频帧正常。
- 采同boot/PID/birth夹持的进程、WMS、已存在日志和实际相关player/compat/graphics运行件maps及进程根文件SHA；日志有界、不清空日志、不新增hook。与该板最新视频签认的实际加载代逐件比较，缺身份或回执写UNKNOWN，不用同名物理文件替代child实际视图。
- 15分钟首片，先回两板现状及第一项可证差异，不等长报告。CC执行普通只读工具；必要REA由Codex后继接。原始文件持久私有，公开证据脱敏；不再向用户重复询问声音。后继人工路径复现/修复另按实际结果派单。
## 边界
### 允许修改
- benchmark/2026-10-21-manual-video-regression/**
- tools/spec-checks/tests/toutiao_manual_video_state.rs
- 私有$HOME/.local/share/westlake/manual-video-regression-20261021/**
### 禁止
- 不改运行时、冻结项、签认历史、设备设置和app数据；不操作5ea，不启动任何自动点击/播放/恢复脚本，不把unknown升级为pass。
## 验收标准
场景: 保留两板人工现场
  测试: toutiao_manual_video_state_receipt
  审核: human
  假设两板可读且无竞争写任务
  当按现状采样截图和进程身份
  那么每板记录三次实际画面或明确不可观测原因，截图时间和真实SHA可复核，操作记录没有输入点击或配置写入
场景: 播放与画面分离判定
  测试: toutiao_manual_video_state_receipt
  审核: human
  假设用户报告进度变化但画面停首帧
  当比较采样画面及身份匹配的已有日志
  那么分别报告时间轴、视频区域变化与日志覆盖，缺帧或网络原因未经证实则标UNKNOWN，不用alive推视频正常
场景: 基线差异及失去现场
  测试: toutiao_manual_video_state_receipt
  审核: human
  假设存在历史签认但当前boot或加载代可能变化
  当核对实际加载文件并检测用户是否已离开视频页
  那么给逐件版本差异与证据，现场已失去则保留观察结果并停止自动动作，不声称复现或修复完成
## 排除范围
本卡不执行修复、自动重开、随机崩溃调查或声音问卷；取得现场后继续解决人工播放回归，不以只读报告代替修复。
