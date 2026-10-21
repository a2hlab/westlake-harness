spec: task
name: "T36 host recreation reentry candidate"
inherits: project
depends: [t35-manual-playback-state]
satisfies: [REQ-TTVIDEO]
---
## 意图
修复已由源码确认的宿主重建后缺少重新绑定路径，使关闭头条后再次点击图标具备正确重入能力。本卡交离线候选和生产函数故障回放，不把缺失现场parent环境证据的推断升级为已证根因。
## 已定决策
- 来源为T35 whitescreen-01和T34 reentry-retirement-01/deploy-package-r3-root/payload，原件只读；新目录制作候选。原guardian正常退休child但无新spawn；当前父进程WID未知，不再尝试遭安全拒绝的环境读取。
- 当前没有已验证运行中rebind：watchdog和spawn两次核parent窗口，real-spawn仅发送固定request；只删WID门不能修复。优先复用已有启动助手，在严格无child条件下切换一次parent epoch。发现缺少安全实现前提则给精确缺口，不制造成功。
- 停止旧parent只可针对本guardian记载且经boot/PID/birth/namespace/exe哈希/run inode核定的exact对象，不能把现有只读parent_owned升级成通用kill。全部直系child与owned window必须已证为空，枚举失败为unknown；活child加新host不杀不重建。
- 固定socket必须证明旧epoch所有权、旧parent退出且无替代listener才处理残留；init提供或归属未知不得unlink。先旧parent退出再改run.sh，sed换inode不得破坏旧身份核查。新parent身份读回、epoch更新和spawn分类在当前shell持久记录。
- 保留桌面到图标单次触发、双child防护、原暖返回、视频版本和用户数据。新增拒绝reason日志避免永久静默other；失败/unknown不循环强杀或重启。20分钟首片，最终源码/patch/可执行回放/原始日志与SHA齐全。
## 边界
### 允许修改
- benchmark/2026-10-21-manual-video-regression/host-reentry-candidate/**
- tools/spec-checks/tests/toutiao_host_reentry_candidate.rs
- 私有$HOME/.local/share/westlake/manual-video-regression-20261021/host-reentry-candidate/**
### 禁止
- 不设备、不REA、不读取被拒绝的环境字段、不改旧签认及冻结源、不清数据、不push，不修改其他agent文件。
## 验收标准
场景: 已验证新宿主且旧child退出
  测试: toutiao_host_reentry_candidate
  假设旧epoch和socket归属完整且全部child与窗口为空
  当生产函数接收桌面到新宿主事件
  那么只切换一次parent epoch并绑定当前WID，单次spawn，新身份持久读回，旧退休tuple保留至新adopt
场景: 活child与未知身份拒绝
  测试: toutiao_host_reentry_candidate
  假设活child或枚举失败或PID复用或socket归属不明
  当收到新host事件
  那么不发停止信号、不删除socket、不重建parent且给确定reason
场景: 部分失败不双启
  测试: toutiao_host_reentry_candidate
  假设旧parent停止失败或新parent启动返回未知或持久化失败
  当执行故障注入回放
  那么拒绝重复启动并保留旧新identity及失败日志，不把unknown记为通过
场景: 暖返回和历史能力保持
  测试: toutiao_host_reentry_candidate
  假设旧host与child仍存活且窗口匹配
  当正常桌面返回及反复图标事件
  那么不更换parent不重复spawn，原r3退休与单次重入测试保持通过
## 排除范围
设备部署与截图验收另卡；随机崩溃、反虚拟化、视频解码改动不在本卡。
