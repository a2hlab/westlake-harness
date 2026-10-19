spec: task
name: "Prepare typed OH window provider adapter offline"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t9-window-offline-module]
tags: [offline, bounded, human-review]
---
## 意图
把已核精确OH接口和字段契约接到R14显式ops，提前消除函数签名、字段宽度和Region传参错误，减少后续实验等待。此任务仅离线适配与验证，预计帮助toutiao有条件，实际窗口来源和播放仍须实测；不追查随机退出。
## 已定决策
- 新建candidate-r15-provider-offline，引用主树R14源码而不修改或复制改写其实现；保留原49用例结果。以static/r14-provider-next-review及provider-abi/exact-surface*为证据，记录来源SHA。
- [platform-specific] C11，显式注入有正确OH原型的provider函数和可信unwrap能力；用普通typed thunk实现R14回调，不把OH函数指针直接cast成R14函数，不内置dlopen/dlsym、进程探测、全局替换或任意wrapper解引用。一个adapter与一个R14实例覆盖同一所有权域，明确外部quiescence和借用生命周期。
- handle函数只从provider契约保证有效稳定的前24字节，按offset4/8/12/16/20分别memcpy到int32_t再扩展width/stride/height/size，format保留int32。不读usage/virAddr/尾部，不将handle cast成r14_handle，不假称能验证任意指针。stride字节与size容量是选定provider输入契约，保留R14正数、整除、乘积和范围校验。
- flush将R14 LTRB校验后转成OH Rect(x,y,uint32 width,height)，Region按值传递且rectNumber=1、fence=-1，保持真实buffer和window。用SDK签名/布局编译断言核OH ABI；host独立记录接收到的值，不只比较本模块内部结构。
- request/conversion/map/unmap/flush/abort保持原始公共rc，借用conversion不加减引用；正常路径不重试或额外调用Map。原始provider rc、adapter错误、调用/抑制次数分开记录。公共Abort=0不记成底层释放，失败R14槽仍保留。
- 用至多8条有互斥保护的adapter记录关联精确OH/window-buffer/native-buffer与清理风险；不得持全局锁跨阻塞provider调用，不绕过R14同OH别名互斥。空间耗尽在任何新provider副作用前拒绝；不确定或失败记录不重用，只有正常成功flush才可回收。跨OH重复buffer/native身份拒绝发布并禁止猜测清理。
- Map原始rc0且bits全1时，保留raw rc0、输出NULL使R14进入mapped失败分支；对应Unmap thunk返回显式合成错误且不调用下层，R14据此跳过Abort并保留。request非零或矛盾输出不得据错误返回假定无副作用，相应Abort抑制；Map非零的潜在副作用不假定无映射：相应Abort thunk抑制下层并返回合成错误；禁止通过伪造成功清空记录。rc0/NULL普通路径只调用一次公共Unmap，依真实rc决定是否允许公共Abort；不把内部两次Map当作两次显式Map。
- host假后端需独立两层journal区分公共调用与内部模拟行为，验证二次内部Map和Abort吞rc仍不产生虚假释放。构建前check_frozen，host执行和OH ET_REL编译只用新持久目录，保存完整原始命令/stdout/stderr/rc、源码/工具链/依赖SHA；不生成共享库、不链接生产、不上板、不推送。
- 状态固定OFFLINE_ADAPTER_ONLY_NOT_DEPLOYABLE。缺真实factory/object/provider/调用者成对路由的候选不准部署；完整handle尾部和未消费HDI细节不纳入阻塞门。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/candidate-r15-provider-offline/**
- tools/spec-checks/tests/toutiao_typed_provider_adapter.rs
- specs/toutiao-video-playback/t10-typed-provider-adapter.spec.md
### 禁止
- 不修改R14、其他候选、冻结项、生产源码、部署器、API历史等级或设备；不创建admission，不新装工具链。
## 完成条件
### Rule: typed-provider-boundary — 字段与ABI正确且失败不伪装释放
场景: 真实类型的正常配对
  测试: ttvideo_typed_provider_pair
  假设 假后端提供稳定24字节handle和合法buffer与就绪fence
  当 通过adapter的R14实例执行lock和unlock
  那么 独立journal收到正确window/buffer与按值Region，显式Map和Unmap各一次且成功flush后才复用记录，conversion无引用计数操作
场景: 短前缀边界与有符号字段
  测试: ttvideo_typed_provider_layout
  假设 测试仅提供24字节有效前缀且有正数、负一、INT32边界和stride不整除或容量不足组合
  当 复制字段并执行锁定
  那么 int32先解释再扩展，未读前缀外字节，非法输出无bits且无flush，正常像素stride正确
场景: ABI和区域拒绝
  测试: ttvideo_typed_provider_layout
  假设 LTRB反向或宽高差溢出以及合法非零原点区域
  当 转换区域并调用typed flush thunk
  那么 非法区域在provider调用前拒绝，合法区域保持xywh及按值Region且OH编译签名和布局断言通过
场景: Map异常与清理风险
  测试: ttvideo_typed_provider_failures
  假设 公共Map返回rc0和NULL或全1，以及非零rc和非空地址
  当 R14经adapter处理失败
  那么 全1不发布且下层Unmap与Abort均抑制，非零Map抑制Abort，普通rc0/NULL只Unmap一次并按其返回决定Abort，raw与合成错误分开且失败记录保留
场景: 二次内部Map与取消吞rc
  测试: ttvideo_typed_provider_failures
  假设 公共Map模拟第二次内部Map失败后rc0/NULL，公共Abort模拟下层失败却rc0，或Unmap与Flush返回失败
  当 检查两层journal及下一次lock
  那么 adapter不额外重试Map，不把Abort零当释放，失败窗口拒绝重用，无重复flush或错误取消
场景: 并发身份和容量拒绝
  测试: ttvideo_typed_provider_concurrency
  假设 同OH别名交错、不同窗口并发、8条占用、第9请求及重复buffer/native身份
  当 用pthread barrier阻塞provider并再次调用
  那么 同OH无重叠副作用，不持全局锁阻止独立窗口，容量或身份冲突不发布且保留已有记录，只有成功flush回收
场景: 可复现离线产物与准入边界
  测试: ttvideo_typed_provider_receipt
  审核: human
  假设 全部明确选择器通过且原始构建与输入证据齐全
  当 外环独立重建并核验
  那么 原始stdout/stderr/rc和机器可读receipt逐件可核，R14源码SHA不变；只交host可执行测试与OH静态对象，状态OFFLINE_ADAPTER_ONLY_NOT_DEPLOYABLE，未声称实板provider绑定或播放通过
## 排除范围
- 实际动态resolver、窗口工厂、生产caller路由、几何策略改造、播放器派生、设备实验、随机崩溃、安全机制、API冻结和推送。
