spec: task
name: "Own 5cd T18 observer staging and cleanup"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t18b-audiotrack-production]
tags: [diagnostic, outer-only, human-review]
---
## 意图
复用已核R13/T16观察器，为5cd候选窗装配受控外环server和forward，获取实际ANW对象证据。工具自身不修改运行时、不启动业务进程、不代替播放验收。
## 已定决策
- 默认preview零设备调用；执行需外环本窗admission和120秒内fresh T17实际profile回执。
- 五模块均核实际private SHA与maps dev/inode；boot、holder、父子及host身份全核；只用已核SDK15 host和NDK server。
- 先本次唯一目录stage，再启动自有server；从实际PID/birth/UID/exe/cmdline/socket建立所有权，再完整T18 validate并运行120秒硬件观察。
- server启动前已进入finally；所有失败清理自有host/server/forward，清理后业务child须同身份TracerPid0且非停止。未知交外环恢复，不重启第二server。
- 240秒工具预算及30分钟外环截止并存，1200秒前观察结束，恢复只在1800秒总窗内；拒绝挤占恢复余量。
## 边界
### 允许修改
- benchmark/2026-10-20-t18-observer-outer/**
- specs/toutiao-video-playback/t18c-owned-observer-outer.spec.md
- tools/spec-checks/tests/toutiao_t18c_observer_outer.rs
### 禁止
- 不改R13/T16/T18观察器、不改生产运行时、不触61b、不上板、不推送。
## 完成条件
场景: 默认与未准入拒绝
  测试: ttvideo_t18c_observer_outer
  假设 默认CLI或外环admission未批准
  当 执行本机检查
  那么 默认零设备且未批准输入在导入设备模块之前拒绝
场景: 所有权和有限清理
  测试: ttvideo_t18c_observer_outer
  假设 自有host没有按TERM退出或端口存在相似前缀
  当 执行实际清理helper及端口解析反例
  那么 只匹配精确端口且所有wait都有截止，未知不冒认成功
场景: 实际观察与恢复
  测试: ttvideo_t18c_observer_outer
  审核: human
  假设 外环持有本窗5cd锁并批准真实fresh profile
  当 外环独立执行wrapper及核原始回执
  那么 五模块和身份门通过后才attach，观察与detach清理各自有真实证据；不把指针观测当动态播放或声音通过
## 排除范围
- 修复ANW、随机退出分析、业务UI、运行时部署和播放签认。
