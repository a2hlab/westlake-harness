spec: task
name: "Prepare isolated native-window lock module offline"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-static-evidence]
tags: [offline, bounded, human-review]
---
## 意图
R10精确shim已证固定-19，R13因应用提前退出未采到对象。并行准备可复用窗口lock/unlock的离线源码和错误路径测试；只为未来对象/实例被正面确认后减少构建等待，不假定头条传入wrapper，不发布部署候选。
## 已定决策
- 只新建candidate-r14-offline下模块、明确的输入ops接口、测试和配方；不修改任何已有运行时/冻结件，不调用板、HDC、进程调试、APK或player派生，不推送。当前预计可帮助的key仅toutiao且以实际wrapper/实例/路由证据为条件，不报移墙完成。
- 源码依据main中source-build-native691/westlake的f12c5c921bdff7df8ea2f955b1de69eed2e4cec12fc7b830028027f30572a02a窗口闭包；参考benchmark/2026-10-20-window-candidate-preflight/EDGE-CONTRACT.md及其SHA索引。不得整体复制shim、audio、JNI、fts或loader。明确记录相对donor的错误处理改动，不称逐字复用。
- [platform-specific] 生产动态resolver/命名空间/调用者路由尚未准入。本阶段模块仅经显式ops取得unwrap/request/handle/conversion/map/unmap/flush/abort/clock/poll/close能力。测试注入独立假后端；不内置dlsym，不构造OH窗口，不直接解引用任意wrapper，不把NULL当raw指针。将来真实unwrap必须与d4fa实际契约绑定，本阶段绝不伪称已连接。
- lock/unlock配对，独立8槽；保留wrapper和精确OH window所有权。同OH的不同wrapper别名须互斥；CLAIMED、LOCKED、COMPLETING及失败保留态都不得被第二次lock/unlock消耗。slot锁不覆盖阻塞provider调用，但窗口预留持续到操作终止。wrapper acquire/release不在本模块。
- lock仅在请求返回成功/非空buffer、fence完成、conversion及Map成功并有bits、format/尺寸/stride校验通过时发布输出；沿donor格式映射且核stride单位/整除/溢出，静态断言Android Buffer/Rect布局。拒绝virAddr回退；失败输出清空。dirty区域采用完整buffer，仅是离线接口约定，不证明实板geometry。
- fence使用单一monotonic总deadline，EINTR/EAGAIN不延长预算；仅POLLIN且无ERR/NVAL/HUP才可通过，-1表示无需等待；确属本次request的非负fd关闭一次。timeout/HUP-only/错误不Map不发布bits。
- Map/Unmap只对实际成功的Map配对；成功Map后的格式/尺寸拒绝先Unmap。正常unlock只一次Unmap再一次flush，flush成功才释放槽。失败清理不假定Abort rc0证明底层已释放；不确定所有权保留并拒绝重用，记录尝试和错误，不双取消/双flush，不把错误返回当呈现。
- 构建先check_frozen，仅在新持久输出目录执行host测试/可选OH交叉编译静态对象，不生成可自动部署的共享库，不重建运行时。原始命令/stdout/stderr/rc、源/工具链输入SHA和真实产物SHA保留；公开文档不嵌个人路径。用真实pthread barriers与独立事件journal检验并发，不只测试实现内部字段。
- 发布状态只能OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE。后继上线仍需实际对象/实例、provider ABI、caller-scoped lock/unlock成对路由、实际构建ABI门及独立限时窗口；本任务不替代这些准入，不更新冻结/播放通过声明。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/**
- tools/spec-checks/tests/toutiao_window_offline_module.rs
- specs/toutiao-video-playback/t9-window-offline-module.spec.md
### 禁止
- 不修改其他候选、生产源码、运行时、冻结项、部署脚本、主窗口、图标守护、网络和用户数据；不调用设备，不生成部署admission。
## 完成条件
### Rule: offline-paired-window-module — 离线配对和失败保留
场景: 正常lock与成对提交
  测试: ttvideo_window_offline_pair
  假设 独立假后端提供可解析wrapper和合法窗口buffer且每个provider返回成功
  当 lock后unlock
  那么 journal证明Request、fence、Map、Unmap、Flush有序且恰好一次，像素stride与结构布局匹配，只有成功flush才可再次lock
场景: resolver与request及映射拒绝
  测试: ttvideo_window_offline_failures
  假设 缺能力、未知wrapper、request失败、空buffer、conversion失败、Map错误含非空bits或非法格式尺寸
  当 调用lock
  那么 返回负值且无可用输出，按真实成功阶段清理，不raw回退、不virAddr回退、不错误flush
场景: fence预算与错误清理
  测试: ttvideo_window_offline_failures
  假设 fence为-1、POLLIN、超时、EINTR连续、EAGAIN或HUP-only以及ERR/NVAL
  当 等待本次request的fence
  那么 总截止时间不被重试延长，失败不得Map，所属fd恰好关闭一次且-1不close
场景: 失败提交与同窗口并发
  测试: ttvideo_window_offline_concurrency
  假设 Unmap或Flush失败、8槽耗尽、同OH别名并发、COMPLETING期间lock或重复unlock
  当 用pthread barrier交错调用
  那么 独立journal证明同窗口provider不重叠、无双消费、失败所有权不清空、新请求明确拒绝，其他窗口可独立操作
场景: 可复现离线交付与部署拒绝
  测试: ttvideo_window_offline_receipt
  审核: human
  假设 原始构建日志和源输入哈希齐全且正反例实际执行通过
  当 外环审查模块配方与产物
  那么 仅登记OFFLINE_MODULE_ONLY_NOT_DEPLOYABLE，缺实际对象/实例/ABI/路由证据禁止当成部署候选，视频与声音仍未通过
## 排除范围
- 真实动态绑定、窗口创建、几何修复、播放器派生/路由、上板、随机退出诊断、API冻结及远程推送。
