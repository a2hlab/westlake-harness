spec: task
name: "Reuse native-buffer EGL import in the paired shim"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t20-paired-anw-candidate]
tags: [egl, native-buffer, source-reuse, production-candidate]
---
## 意图
针对T21头条真实首fatal Invalid GrBackendTexture，复用native691与R77既有EGL导入修复，在原T20同shim内加入独立单元；预计移走首致命点key=toutiao为条件预测。本任务只构建可审候选，画面是否恢复须另由外环真机确认。
## 已定决策
- 复用三EGL入口，将可信HWUI的OH NativeBuffer转换为OH window buffer，tracked import仅将target3140转换为34E1；没有raw-pointer布局猜测。
- GL/nativeFence分支已有exacta11c调用证据，同批加入dup fence的同display派发；不改sync创建销毁、不关闭返回fd。
- display只接受唯一current-display匹配，tracked destroy固定创建时display和implementation；不消费eglGetError，拒绝不冒称生成标准EGL错误。
- 每槽按FREE、RESERVED、CLIENT、CREATING、IMAGE、DESTROYING转换；满表创建前拒，重复create不得透传，destroy失败保留引用供重试。
- 保留原T20 CPU pair及原网络/音频件；新TU同DSO，不增PRELOAD。foreign调用参数和返回透传原下一函数。
## 约束
- 先通过冻结检查再构建；源码、工具链、依赖SHA与原始stdout/stderr/rc持久保存，新增exports单列，原exports不删除。
- OH provider必须绑定可信AHB来源的实际实例，不以同名库或同SHA多映射代替。未知绑定拒绝；不新增随意namespace加载。
## 边界
### 允许修改
- benchmark/2026-10-20-t23-egl-import/**
- specs/toutiao-video-playback/t23-egl-import.spec.md
- tools/spec-checks/tests/toutiao_t23_egl_import.rs
### 禁止
- 不改T20、R14/R15历史文件，不改冻结项，不执行设备、部署或推送，不修随机退出。
## 完成条件
场景: 实际导入生命周期
  测试: ttvideo_t23_egl_import
  假设 主机fixture编译实际EGL单元和明确provider seams
  当 创建clientbuffer、创建image并销毁
  那么 OH window buffer恰好创建销毁一次且target转换为34E1，同display同implementation
场景: 并发和失败保留
  测试: ttvideo_t23_egl_import
  假设 已存在CLIENT或IMAGE槽
  当 重复create、满表、错误display、destroy失败与重试
  那么 重复调用拒绝且不透传，不提前释放buffer，成功重试后引用归零
场景: provider与foreign拒绝边界
  测试: ttvideo_t23_egl_import
  假设 provider来源未知、display无匹配或多匹配
  当 请求tracked import或foreign透传
  那么 tracked路径拒绝而foreign仅调用一次原入口，不消费eglGetError
  并且 dup fence仅在唯一display匹配时用同implementation且不关闭fd
场景: 真实构建保留CPU行为
  测试: ttvideo_t23_egl_import
  假设 原T20成功CPU源码与精确构建输入已钉
  当 构建新增TU并链接同一个PIC DSO
  那么 原T20源码SHA不变，原exports不删，新增exports单列，原始命令和stdout/stderr/rc可定位
  并且 先通过冻结检查再构建；源码、工具链、依赖SHA与原始stdout/stderr/rc持久保存，新增exports单列，原exports不删除。
场景: 真机首墙和动态画面仍待验
  测试: ttvideo_t23_egl_import
  审核: human
  假设 外环另有部署与回滚窗口
  当 核对实际EGL绑定、导入结果、连续帧与已确认音频
  那么 仅实际动态图像可签视频通过，静态候选和host seams均不得冒认真机通过
## 排除范围
- 本任务上板、geometry/getter族、damage/terminate、全APK回归、未知指针解引用、模拟成功日志。
