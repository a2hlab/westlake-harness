spec: task
name: "Real consumer methods differential host fixture"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: []
---
## 意图
以真实TU调用测量原顺序/状态/errno/异常，供CC直接复用；不替代生产ABI或设备绑定。
## 已定决策
- 校验设计source-pins中的两原源后直接include完整TU，JNI/OH仅外部seam；运行attach/detach/update及TextureView create/destroy方法。
- CLI接收--consumer-source-dir指定新版源，可显式追加真实logger source；原版先固定stdout行为，新版尚不存在时保持pending，不假stub logger。
- 记录各provider调用前errno及返回后errno、异常和字段写事件，调用数/顺序与状态直接比较，不以文本命中代替方法执行。
## 边界
### 允许修改
- benchmark/2026-10-20-t29-consumer-test-peer/**
- specs/toutiao-t29-consumer-test-peer/**
- tools/spec-checks/tests/toutiao_t29_consumer_test_peer.rs
### 禁止
- sources/api-implementations/bridge-d4fa-source-snapshot/**
- benchmark/2026-10-20-t29-window-observation/consumer/**
## 完成条件
场景: 两原TU真实编译并调用
  测试: ttvideo_t29_consumer_peer
  层级: integration
  替身: JNI/OH外部seam，业务TU保持原字节
  假设 原两源SHA与design/source-pins相同
  当 编译完整两TU并调用attach/detach/update正常与provider错误
  那么 provider调用数顺序、返回、errno与异常序列有实际stdout，成功才更新state且非零保留原状态
场景: 无效与release边界保持
  测试: ttvideo_t29_consumer_peer
  假设 null对象/null state/错误magic/null image/released state
  当 调用原consumer方法
  那么 真实GetState路径和早退规则被执行，update异常与attach/detach原规则分别核，不增加provider调用
场景: producer替换失败与alias不改义
  测试: ttvideo_t29_consumer_peer
  假设 old/new同对象、不同对象、空、released getter及ref/unref失败
  当 调用真实TextureView create/destroy
  那么 getter/字段写/ref/unref次数顺序保留原行为，异常与errno被测且不重复getter
场景: 新版待交或对照漂移
  测试: ttvideo_t29_consumer_peer
  假设 新版路径缺失或真实方法改变provider调用/状态/errno
  当 指定--consumer-source-dir运行同一fixture
  那么 缺文件或编译失败非零且保留原件，运行行为不等于baseline则拒绝PASS；未指定新版明确PENDING
## 排除范围
不实现日志预算或sink，不代替CC自有并发logger测试，不构建生产DSO或判断实板winner。
