spec: task
name: "Bind observed ANW wall to minimum production prerequisites"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t18b-audiotrack-production, t18c-owned-observer-outer]
tags: [static, native-window, human-review]
---
## 意图
依据T18实际249次lock失败，复用R14/R15和精确桥源码，限定下一次对象观察及生产接线门槛；不重复已知锁地址分析，不把离线适配器当可部署修复。
## 已定决策
- 仅核dca530一个unwrap函数对旧d4fa的指令字节，复用历史REA；日志只公开短技术摘录和原字节位置。
- R14/R15保持原字节；实际factory、wrapper所有权生命周期、OH实例、paired入口路由缺一即保留unknown。
- 下一实际观察复用T18已审工具，限单child120秒与既有4加4事件，无新设备执行授权由本交件自行使用。
- 用户明确确认同视频“家住65楼”音频，外环已绑定5cd本窗，保留音频通过事实；不把音频或未见JNI字符串冒认动态视频通过。
## 边界
### 允许修改
- benchmark/2026-10-20-t19-anw-integration-readiness/**
- specs/toutiao-video-playback/t19-anw-integration-readiness.spec.md
- tools/spec-checks/tests/toutiao_t19_anw_readiness.rs
### 禁止
- 不改生产源码、冻结项、R14/R15、旧原件；不调用设备、不构建、不推送。
## 完成条件
场景: 精确静态证据
  测试: ttvideo_t19_anw_readiness
  假设 新bridge及已有生产源和旧unwrap证据明确
  当 复核持久LLVM原件与仓内索引
  那么 15条指令逐字一致且全部输入SHA可核，源行为不升级为runtimewinner
场景: 下一最小观察门
  测试: ttvideo_t19_anw_readiness
  审核: human
  假设 外环另行执行已审T18观察工具
  当 审核实际factory返回和lock输入及选定模块证据
  那么 缺失事件或未知生命周期不冒认通过，单窗有限且保持既有恢复约束
场景: 生产接线限界
  测试: ttvideo_t19_anw_readiness
  审核: human
  假设 离线R14和R15源码及编译回执已齐
  当 审核最小入口与可信unwrap任务卡
  那么 明确对象所有权与实例路由是先决条件，不输出可部署或封板结论
## 排除范围
- 本轮设备观察执行、随机退出诊断、生产实现、冻结登记、动态播放签认。
