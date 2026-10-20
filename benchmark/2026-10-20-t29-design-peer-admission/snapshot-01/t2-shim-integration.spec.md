spec: task
name: "T29 shim observation and single production integration"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-consumer]
tags: [design-only, shim, integration]
---
## 意图
T4观测T28真实CPU路由的早退与输出，并唯一整合CC consumer logging生产包。预计补齐toutiao切换首错的证据，不预计本候选直接修复黑屏。
## 已定决策
- 从冻结T28 geometry/window_module/provider_adapter/pair及缓存源另派生，覆盖cache-begin/lock-entry/prepare-output/lock-return/flush-return/geometry-return六phase；原始request/Map/Unmap/Flush/Abort及cleanup raw rc取现有report/call-local，不重复调用provider。
- geometry_begin失败也记录；拒绝caller/slot时wrapper仅opaque且OH unknown，0新增owner/OH调用；output只在已经成功准备的原local上取字段，不读未初始化输出。格式请求/history与实际layout分列，unknown不冒充YV12。
- 固定预算按project：CPU key为可信wrapper/OH配对，unwrap前为wrapper加OH未知；不能因OH从未知变已知重复耗尽identity。新wrapper独立预算，既有key的实际geometry配置变化开epoch，逐帧token generation不重置epoch。same-wrapper无可见transition不保证新增覆盖，明确unknown不得假报。
- 观测不移动原发布线性化点、业务锁/引用/FAILED资源；锁内仅复制当前合法值，写日志在锁外。未知/错误日志不触发修复、retry或新的unwrap/GetConfig。
- CC consumer最终pins收齐后一次联合生产：T18原对象闭包只替两个consumer对象加hidden logger，shim复用T28链仅改观测。check_frozen先行；原89b9/dca基线分别复现，若重建两个未改consumer TU不能字节等于旧对象则保留差异并要求独立语义/ABI审查，不假报全源历史重现。
- 实际两个consumer/JNI表/78 shim导出版本/bridge导出和DT_NEEDED核非空对照；新hidden logger不外泄。生成新GOT/调用PC精确索引供外环只读绑定，旧偏移仅为定位起点。
## 约束
- 当前仅设计；T4独占shim和production，CC仅consumer目录。源、依赖、SDK实际输入和原始stdout/stderr/rc全部持久；后续device授权另行，不能由测试绿升级。
- 保持T28 RGBX2/YV12/其他RGB与3slot gate、8槽alias、cleanup、额外ref和原EGL调用次数；不读取任意ptr或消费eglGetError。
## 边界
### 允许修改
- benchmark/2026-10-20-t29-window-observation/shim/**
- benchmark/2026-10-20-t29-window-observation/production/**
- benchmark/2026-10-20-t29-window-observation/design/**
- specs/toutiao-t29-observation/t2-shim-integration.spec.md
- tools/spec-checks/tests/toutiao_t29_observation.rs
### 禁止
- benchmark/2026-10-20-t28-rgbx/**
- benchmark/2026-10-20-t18-audiotrack-production/**
- knowledge/frozen/**
## 完成条件
场景: 实际路由早退可见且无额外provider
  测试: ttvideo_t29_cpu_route
  层级: integration
  替身: 外部OH provider与sink，保留真实shim/pair/R14
  假设 fixture调用真实派生shim到pair到R14而非只调用logger
  当 注入wrong caller/任一GOT mismatch/cache-begin EBUSY/无空槽/prepare失败及正常输出
  那么 每条原路径保留返回和errno且错误有phase/valid_mask，拒绝caller新增owner/OH调用数0
场景: flush失败保留资源和原始错误
  测试: ttvideo_t29_cpu_cleanup
  层级: integration
  替身: 外部OH provider错误注入
  假设 conversion/Unmap/Flush分别失败以及retained资源
  当 执行真实unlock及cleanup路径
  那么 原顺序/次数/ref/首错/FAILED状态与T28相同且记录各实际调用rc，禁止新增Flush/Abort
场景: 原格式行为和并发不改变
  测试: ttvideo_t29_cpu_regression
  假设 RGBX2/YV12/unknownRGB及两个wrapper同OH的实际pthread竞争
  当 运行原T28路由和并发用例并开启观测
  那么 输出字节/格式/stride/alpha/引用及8活动槽上限与对照一致，观察不改变业务发布点
场景: 早期全局热循环不吞新wrapper
  测试: ttvideo_t29_cpu_budget
  层级: integration
  替身: 受控provider与write，真实并发计数
  假设 首wrapper调用10000次后切到第二wrapper并返回旧OH但新wrapper
  当 运行真实锁和geometry路径以及最终budget满/日志短写
  那么 新identity首调用各phase保留、旧token逐帧不reset预算、单DSO3104条/2383872B上限且未知或超限明确，原errno不变
场景: 基线与生产输入缺失拒绝
  测试: ttvideo_t29_production
  假设 CC最终源pin或T18对象/SDK/原始执行日志缺失、修改或仅空ABI输出
  当 执行独立生产准入检查
  那么 拒绝出可部署签认且保留原失败；完整时复现89b9/dca基线并记录新双产物非空ABI/JNI/GOT及每条原始rc，stdout/stderr分文件且JSON回执绑定文件SHA
场景: 真实切换首错仍需实际运行判定
  测试: ttvideo_t29_production
  审核: human
  假设 新代码entry和原provider绑定及真实切换截图尚无回执
  当 离线测试与生产构建完成
  那么 状态仅OFFLINE_OBSERVATION_CANDIDATE_NOT_DEPLOY_AUTHORIZED，不把UNKNOWN改PASS或宣布黑屏根因
## 排除范围
不改格式/播放器二进制/网络/音频/随机退出处理，不更换系统provider，不直接操作板、提交API等级或推送。
