spec: task
name: "T29 consumer call logging"
inherits: project
satisfies: [REQ-TTVIDEO]
tags: [design-only, consumer, observation]
---
## 意图
CC独立派生已核dca的SurfaceTexture/TextureView两TU，仅记录现有调用和producer替换，不实施生命周期修复。exact dca调用PC update11f24c/detach11f46c/attach11f4f0及JNI表已证，运行绑定仍unknown。
## 已定决策
- 从source-pins钉定的oh_surface_texture_jni.cpp及oh_texture_view_jni.cpp另存consumer/derived；原件只读。日志记录entry/return、原state/image/OH、released/detached/texName有效位、原call是否执行及raw rc；void update记录既有异常分支，不新增ExceptionClear/异常检查副作用。
- TextureView只记old field/new getter返回、原ref/unref分别记录ref_called/ref_rc_valid/ref_rc及unref_called/unref_rc_valid/unref_rc（以已钉原型为准，void则各自valid=0），不再调用getter或attach；jobject仅call-local地址，关联用可信native window及调用序号，不以jobject地址判对象复用。
- 现有GetState校验不变；invalid state/image/released早退只记已安全取得字段和valid_mask，零新增解引用。观测复制后不访问原对象。attach/detach结果与state成功更新规则保持。
- 固定预算按project；consumer六phase为attach/detach/update/producer-replace/producer-destroy/invalid。consumer transition以可信state或TextureView操作域记录epoch；没有可信state时保持unknown，不为关联新增GetState调用。
- 交T4的接口仅hidden本DSO日志函数及值类型record，详见interface.json；不导出新API，不提供可执行设备入口。最终对象编译由T4唯一生产任务完成。
## 约束
- 采认前仅DESIGN_ONLY；批准后真实host测试调用派生方法本体和fake现有OH/JNI seam，不用填写JSON代替方法执行。
- 恢复errno且provider调用一次，零额外ref/字段写/对象销毁；正常/异常日志均不含媒体地址。诊断sink与保留cap额度严格继承project。
## 边界
### 允许修改
- benchmark/2026-10-20-t29-window-observation/consumer/**
- specs/toutiao-t29-observation/t1-consumer.spec.md
- tools/spec-checks/tests/toutiao_t29_consumer.rs
### 禁止
- benchmark/2026-10-20-t28-rgbx/**
- sources/api-implementations/bridge-d4fa-source-snapshot/**
- benchmark/2026-10-20-t29-window-observation/shim/**
## 完成条件
场景: attach detach及update真实调用透明
  测试: ttvideo_t29_consumer_calls
  层级: integration
  替身: 仅OH/JNI外部provider，执行真实派生方法本体
  假设 fixture执行派生JNI方法本体且provider分别返回0和非0并设置errno
  当 运行attach detach update正常及错误路径
  那么 原调用次数顺序/返回/errno/异常与对照相等且记录raw rc与实际call标志
  并且 恢复errno且provider调用一次，零额外ref/字段写/对象销毁；正常/异常日志均不含媒体地址
场景: invalid与已release对象安全早退
  测试: ttvideo_t29_consumer_invalid
  假设 原GetState拒绝或image空或released为真
  当 进入派生方法
  那么 现有GetState校验不变，invalid state/image/released早退不新增对象读取和provider调用且保持原异常或负返回，记录未知字段valid_mask为0
场景: producer替换不改变引用规则
  测试: ttvideo_t29_consumer_producer
  假设 old/new为同对象、不同对象、null及getter失败
  当 运行真实TextureView create/destroy派生方法
  那么 ref/unref/字段写次数顺序与原版一致且无新增consumer attach或getter调用
  并且 记录old field/new getter返回及两个独立ref/unref called/rc_valid/rc；不同返回值不得互相覆盖，void结果各自unknown
场景: 热循环后切换仍有独立预算
  测试: ttvideo_t29_consumer_budget
  假设 首state update循环10000次并用实际pthread并发调用日志
  当 发生另一producer及attach/detach transition并最终超过16identity或8epoch
  那么 边界内切换首调用有记录，边界外明确COVERAGE_EXHAUSTED且业务结果不变，每DSO最多3104条和2383872B；先填满30 invalid仍有独占FINAL_EXHAUSTION，耗尽热路径format/time/write次数0
场景: regular sink及日志失败不改变原errno或返回
  测试: ttvideo_t29_consumer_sink
  层级: integration
  替身: 实际logger与真实regular-file/pipe子进程fixture，write故障另注入
  假设 fd2为真实pipe且read端已关、或regular-file被替换、或短写/EINTR/EPIPE注入及字段超过768B
  当 运行真实日志出口及方法路径
  那么 pipe在write前被拒且子进程不收SIGPIPE，regular sink持有独占dup的原file-description不随fd2重绑转向pipe；身份漂移禁观测且coverage unknown
  并且 每条至多一次write不重试、不改signal，截断有标记，原errno/返回/异常不变且日志失败独立计数
场景: 源码与hidden交付边界
  测试: ttvideo_t29_consumer_pins
  假设 从source-pins派生oh_surface_texture_jni.cpp及oh_texture_view_jni.cpp
  当 核对consumer补丁和对象符号
  那么 原文件SHA全等，interface.json中的record为值类型且logger为hidden无新增导出
  并且 采认前仅DESIGN_ONLY；批准后真实host测试调用派生方法本体和fake现有OH/JNI seam，不用填写JSON代替方法执行
场景: 新运行consumer绑定待真实证据
  测试: ttvideo_t29_consumer_pins
  审核: human
  假设 source/old ELF/JNI/GOT证据与未来新ELF已钉
  当 仅有离线测试或未取得未来entry及provider slot原件
  那么 不宣称已命中consumer或已证明实际provider，不签播放或根因
## 排除范围
不接管T4生产、不构建其他runtime，不修改SurfaceTexture/HWUI策略，不实现或运行设备reader。
