spec: task
name: "T26 bounded YV12 scratch and RGBA conversion successor"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t25-geometry-unwrapping]
tags: [offline, yv12, source-reuse, implementation-authorized]
---
## 意图
补齐已确认的YV12输出契约：exact player保持expected YV12，而原R14成功format集合不含YV12，因而不能进入该配置的视频writer。以独立单元复用既有YVU scratch与RGBA转换，保留T20资源生命周期和T25真实geometry结果；本缺口与EGL create-null根因分开。外环已授权本树独立离线实现与真实host测试；与T27统一一次候选生产重链，不以离线通过代替视频验收。
## 已定决策
- `yv12.c/h`只复用已钉legacy converter的Y/V/U平面与clamp整数算术；不继承其私有ring、TLS singleton、猜指针、fallback map或dlopen策略。exact player配置/比较/expected字段原REA证据必须先钉SHA，不能以日志字段或相似源码替代。
- `dispatch`复用exact player调用域与0x472490/0x472760/0x472048三槽同候选lock/unlock/geometry门，拒绝mixed765；原Android ABI和符号版本保持，新helper隐藏。T20/T23/T25及R14/R15原件只读，接线只能在T26明确派生副本。
- `request_cache`最多8项，每项单独持有可信owner引用，geometry成功才commit请求；失败保留旧请求，format0不重置格式。在同mutex内原子IDLE→ACTIVE或IDLE→EVICTING，胜者独占引用；外部release在锁外调用，随后锁内转FREE/FAILED，EVICTING不重用。active不能evict，外部quiescent destroy同规则。unknown/no-history/evicted历史走原RGB通路，不新拒绝、不猜YV12；原player mismatch分支可重新geometry建立cache。
- `prepare_output`必须在实际player GOT→shim导出lock/unlock→T20 pair→派生R14 glue全链内，以真实导出入口C测试证明不可被旁路；位于真实map和layout通过之后、LOCKED/out发布之前；`before_unmap`位于unlock取得独占transaction之后、原Unmap之前。只对已记录YV12且实际OH12/Android1 packed buffer建立scratch，返回实际宽高/YS/format842094169；不能返回请求尺寸冒充实际尺寸。非YV12的旧RGB返回与操作journal不变。
- `layout`采用YS=align_up(W,16)、CS=align_up(floor(YS/2),16)、CH=ceil(H/2)，V=bits+YS*H、U=V+CS*CH；exact0b4d helper1fa3e4已由S1原件核准，CS来源1fa630–1fa68c、CH来源1fa644–1fa66c、planes来源1fa6d8–1fa6f0。源copy宽ceil(sourceW/2)、无crop行min两者ceil(H/2)。对本模块返回YS此CS等于align_up(ceil(W/2),16)，含正奇数；host奇数布局不代表设备奇数支持。每项运算checked。每项scratch上限32MiB、全局reserved上限64MiB且最多8并发项，分配前原子预留，失败回收预留；目标byte stride及size分别验证，转换不写padding。
- `cleanup`保留原fence预算、request/map/Unmap/Flush/Abort及owner release语义；输出发布前失败沿原cleanup，不截断仍映射内存。转换第一字节前完成全部layout/dest/capacity/overflow检查；转换循环无分配/provider/失败分支。precheck失败目标逐字节不变，禁止Flush，FAILED状态只执行一次Unmap，成功才按原允许状态Abort，不确定则retained；保留首错及各cleanup rc。转换完成后才原Unmap/Flush各一次；不确定失败保留FAILED及owned资源不伪称FREE、不重试flush/close。缓存引用与原pair调用引用分别计数。
- `evidence`必须实际C TU和真实dispatch/glue调用测试，不以字符串断言替代；构建前check_frozen，原始argv/stdout/stderr/rc、源码快照、工具链及依赖SHA持久。生产后像与设备均不由本草案授权。
- `physical_target`仅YV12 geometry映射由OH11改OH12/RGBA8888，其他RGB映射保持；Mali-pins.json钉e0cb入口精确静态证据。转换输出R,G,B,255；OH12只绕过本入口拒绝，不证明后续import成功，不回填T25实际format。
- `joint_observation`由本lane独占T26 derived的R14/R15/CPU及R23/platform观察接线；CC只交observer.c/h及host验证。复用原actual create指针单次调用，GetConfig走SDK准确二参void原型；带下划线FromNativeWindowBuffer保持原int32二参，观察旧无下划线转换仅void*单参。仅已保留handle的同provider符号可调用，否则UNKNOWN，禁止新增provider加载或eglGetError。
## 约束
- 本轮授权本树实现、host测试、OH编译及可复现基线/候选重链；候选生产构建等T27同一代聚合，不重复构建多代。禁止设备、部署、HDC、重启、应用数据写入和push。
- 未来实现仅可在T26目录产生源码、测试、配方、原始receipt及独立Rust选择器；不得改旧冻结文件、播放器ELF、网络或音频；旧T23 EGL import原文件不改，仅同代T26 derived观察接线，不改变create/destroy行为或错误态。
- 无任意wrapper解引用、raw尾读、新provider加载、无条件成功、尺寸修正或eglGetError消费；getter观察仅同已验证provider实例，GetConfig无rc且usage仅low32，不冒充完整64位。
## 边界
### 允许修改
- benchmark/2026-10-20-t26-yv12/**
- benchmark/2026-10-20-t25-observation-blueprint/**
- specs/toutiao-video-playback/t26-yv12-presentation.spec.md
- tools/spec-checks/tests/toutiao_t26_yv12.rs
### 禁止
- benchmark/2026-10-20-t20-provider-link-slice/**
- benchmark/2026-10-20-t23-egl-import/**
- benchmark/2026-10-20-t25-geometry/**
- benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/**
- benchmark/2026-10-19-toutiao-video-playback/candidate-r15-provider-offline/**
- knowledge/frozen/**
## 完成条件
场景: YVU layout及真实转换像素
  测试: ttvideo_t26_layout
  假设 已钉exact writer stride/plane/oddheight证据且实际yv12.c/h及独立像素oracle有576x1024、1920x1080、1x1、3x5、17x3输入
  当 prepare_output返回scratch后填写不同Y/V/U值并执行before_unmap
  那么 仅支持集合内返回format842094169、实际宽高和已核YS，Y/V/U偏移与writer一致；不支持尺寸在发布前明确拒绝
  并且 黑白和非中性色整数像素等于独立oracle，目标padding和canary未改，X为255
场景: 溢出尺寸与预算拒绝
  测试: ttvideo_t26_bounds
  假设 输入零负尺寸、SIZE_MAX运算溢出、32MiB越界、64MiB总预算耗尽或第9项
  当 真实C路径计算layout并预留资源
  那么 返回明确非零错误，不截断尺寸、不发布out、不越界写且分配预算无泄漏
场景: 分配与native布局失败保留首错
  测试: ttvideo_t26_failures
  假设 allocator失败、OH格式非12、目标stride不足或size不足
  当 prepare_output在真实map后执行失败
  那么 不发布LOCKED或scratch输出，沿原清理顺序保留首错误和每个清理rc
  并且 不把失败当成功frame、不重复cleanup，所有已取得引用可追溯
场景: 错调用者与三槽漂移零provider调用
  测试: ttvideo_t26_route
  假设 真实dispatch收到wrong caller或lock/unlock/geometry任一槽与候选不符
  当 调用geometry及lock入口
  那么 owner与OH调用数均为0，不猜wrapper布局且不新dlopen
  并且 正确三槽经真实shim导出→pair→派生R14进入prepare_output和before_unmap，计数证明调用独立TU而非孤立gate
场景: 请求cache与引用并发失败
  测试: ttvideo_t26_ownership
  假设 8项request_cache以及两个wrapper指向同OH，原caller有合法引用
  当 交错geometry失败、format0、idle eviction、active eviction、double unlock及quiescent destroy
  那么 只有成功geometry提交请求；unknown/no-history/evicted历史走原通路，active eviction和同OH重叠拒绝
  并且 真实pthread barrier证明ACTIVE/EVICTING原子胜者独占，外部release不持全局mutex，槽不提前复用；缓存与pair引用分别释放或FAILED retained
场景: Unmap和Flush失败不洗白
  测试: ttvideo_t26_failures
  假设 转换前layout/dest precheck失败，或已转换事务的Unmap或Flush或owner release分别返回失败
  当 执行unlock及重复unlock
  那么 precheck失败目标全字节不变且Flush次数0，实际cleanup按明确FAILED状态；原始rc保留且不重用，转换和成功或失败Flush均不重复
  并且 不以free scratch或释放缓存引用冒充provider已恢复，不触发任意Abort
场景: 旧RGB和ABI保留
  测试: ttvideo_t26_regression
  假设 非YV12以及unknown/no-history/evicted请求对应原Android1/2/3/4/5/22/43及原T25导出版本
  当 经实际shim导出lock/unlock→pair→派生R14完整C调用链
  那么 bits/format/stride/rc与provider journal同原路径且scratch分配及转换均为0
  并且 旧导出tuple/符号版本/NEEDED无移除或漂移，新helper隐藏，旧原件SHA不变
场景: 缺证据拒绝及可复现构建
  测试: ttvideo_t26_receipt
  假设 构建先核冻结且使用已钉T23/T25持久输入
  当 缺exact player比较及writer stride/oddheight证据或源/工具/依赖SHA或原始rc0日志，或check_frozen不通过
  那么 receipt明确拒绝，不能以事后清单补成通过
  并且 完整输入时先重链T25基线byte-identical再生产独立候选，原始失败日志保留
场景: 离线输出不升级播放签认
  测试: ttvideo_t26_receipt
  审核: human
  假设 上述真实C和构建证据完成而实际新窗口尚未授权
  当 外环审核蓝本与receipt
  那么 结果最多OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED，实际writer/EGL结果保持unknown
  并且 不称视频PASS、不改历史API等级；后续若授权仍按project真实有声动态周期验收
## 排除范围
- 设备观测、部署、播放器修改、EGL null归因、色彩空间扩展、任意YUV格式支持、随机退出诊断与长期封板。
