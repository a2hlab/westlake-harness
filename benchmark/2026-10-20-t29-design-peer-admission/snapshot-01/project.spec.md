spec: project
name: "T29 bounded window observation"
satisfies: [REQ-TTVIDEO]
---
## 意图
对T28 surface切换黑画面作一次最小调用观测，区别producer复用、consumer重接与CPU早退。T28同child后续可恢复播放；首因未定，不将观测写成修复或视频封板。
## 约束
- 当前状态DESIGN_ONLY_PENDING_OUTER_ACCEPTANCE：本轮仅改本规格、design蓝图和证据索引；外环采认前禁止源码/测试实现/构建。下述实现场景是待执行义务，不冒充已通过。
- 即使采认也仅授权离线实现/测试/一次联合生产；禁止HDC/设备/部署/push。原T18/T20/T23/T26/T27/T28及knowledge/frozen只读。
- 不改format策略、三槽same-provider门、未知RGB回退、YV12转换、alpha、slot/ref/ownership/fence/cleanup或异常策略。不诊断随机退出，不改变媒体/网络/音频/其他runtime。
- 记录仅使用现有可信unwrap/GetState及当前函数已验证local/handle；地址可作不解引用的opaque标识。不得新增任意ptr读取、wrapper解引用、对象retain/unref/getter/provider调用、dlopen/dlsym/provider替换或eglGetError。
- 观测故障不影响原操作：保持原调用顺序/次数/返回/异常/errno；每原调用前恢复原incoming errno，原调用后立即保存其errno，日志后恢复；early-return保持未观测版本errno。不要吞provider原错或日志write错误，不重试write。
- 记录复制在原有对象/slot有效区及原mutex内完成，日志在原mutex外；不延长对象生命周期，不保存jobject为跨调用身份、不新增JNI globalref，不在日志中访问已释放对象。
- 两DSO各自预算固定：16个不解引用identity槽、每槽最多8个transition epoch、每epoch每phase最多2条正常+2条异常记录，phase最多6个；3072条+32条独立invalid/overflow/cap告知，每条最多768B且单次fd2 write，最大2383872B/DSO。固定诊断槽不驱逐业务槽；诊断满只停日志不拒业务。
- 初始视频的frame/update重复不新建epoch；新wrapper或consumer producer/attach/detach变化拥有独立epoch预算。无变化的重复失败不重置预算。承诺只在16identity/8epoch边界内，超出须明确COVERAGE_EXHAUSTED，不能报完整覆盖。
- actual call与provider binding分列：新代码入口记录self-PC/phase，静态核新JNI表和调用/GOT；外环未来同boot/PID/birth+ELF SHA/maps/前后slot读取才能指认provider实例。命名导入/模块在场不是实际winner；缺证据保持UNKNOWN。
## 已定决策
- CC只拥有consumer派生件；T4拥有shim派生件及唯一集成生产，交付协议见design/BLUEPRINT.md和interface.json。实现可并行，集成依赖consumer最终pins。
- T18 dca完整对象/源/依赖/SDK配方复用：仅替换两处consumer TU及新增hidden日志TU；shim以T28 89b9为基线仅增加观测，合为一次联合候选批次（bridge+shim），其他运行时字节不变。
- 所有原始argv/stdout/stderr/rc、源码/工具/依赖SHA持久保存；公开日志无媒体URL/token或个人路径。新的编译记录不得称历史构建日志。
