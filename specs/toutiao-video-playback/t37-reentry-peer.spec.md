spec: task
name: "T37 independent reentry and manual video acceptance review"
inherits: project
depends: [t35-manual-playback-state]
satisfies: [REQ-TTVIDEO]
---
## 意图
独立审查T36宿主重建候选，并提前准备真正桌面手点重开和视频卡进入播放的验收路径，减少实现后的串行等待。没有候选时先从生产源码建立反例，不等待空转。
## 已定决策
- 只读T34完整payload与T35真实白屏证据，区别活child暖返回、child退出、host重建三种事件；不以暖返回成功覆盖冷重入。
- 在独立目录回放生产函数，挑战活child、PID复用、枚举失败、socket陌生listener、停止失败、inode变更和两次点击。每个结论引用精确文件/SHA/回执，不只看作者PASS。
- 验收矩阵包含正常关闭后手点图标进feed、点视频卡后动态帧至少20秒、暂停3秒恢复10秒、退出重进；agent注入点击与真实human观察分别标记，不假称人工已测，不再重复要求声音确认。
- 仅离线，不设备、不REA、不重试已拒绝环境读取，不改作者源码；20分钟首片，候选后自适应复验。
## 边界
### 允许修改
- benchmark/2026-10-21-manual-video-regression/host-reentry-peer/**
- tools/spec-checks/tests/toutiao_host_reentry_peer.rs
### 禁止
- 不改T36文件、冻结项、历史签认、设备和主树，不push；缺实际证据写unknown。
## 验收标准
场景: 生产装配独立审阅
  测试: toutiao_host_reentry_peer
  假设存在T36候选或现行r3源码
  当按真实entry到spawn路径回放
  那么报告精确审查SHA、实跑反例和阻断项，未有候选不宣称候选通过
场景: 不同验收范围不得互替
  测试: toutiao_host_reentry_peer
  假设已有暖返回或历史声音证据
  当整理人工重开和视频卡验收矩阵
  那么未执行项保持待验证，视频画面需实际动态截图，不以进度条或alive代替
场景: 不明对象拒绝
  测试: toutiao_host_reentry_peer
  假设identity或socket归属或枚举失败
  当对候选执行边界回放
  那么不会停止陌生进程或双启，失败保留原日志和反例
## 排除范围
部署、上板操作、实际视频播放与用户确认。
