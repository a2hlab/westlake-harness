spec: task
name: "AudioTrack effective ring size single native implementation"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t17-5cd-network-reuse]
tags: [audio, static, owner, human-review]
---
## 意图
T17实际头条AJVoice.initAudioTrack遇到native_get_buffer_size_frames()I未实现。只在原AudioTrack owner补该方法，预计移走首个JNI异常墙的key为toutiao，不承诺实际声音或视频完成。
## 约束
- 仅使用已核d4fa owner中cap/bytesPerFrame的有效ring写入上限；不是空余帧、Java申请值或OH硬件容量。
- 保持现有getShim和mu路径；不新建DSO按猜测偏移读对象、不改变owner分配/释放或ring写入行为。既有并发release生命周期保证未证，不声称本任务解决它。
- 仅一条()I注册，走原逐项RegisterNatives；禁止UnregisterNatives、set_size/capacity/loop和MediaPlayer注册变化。
- 无对象或无合法完整帧/结果溢出时抛IllegalStateException，保留原pending exception，不能伪造正数或静默常量成功。
- 本轮是源码与离线编译准备。原d4fa整库producing closure仍unknown；对象编译或host测试不代表可部署，必须先补全整库构建来源与ABI/frozen门、原始构建日志和独立验收。
## 已定决策
- 以独立include实现getter，精确SHA派生owner源码及一条注册；原source-profile不修改。
- host测试编译实际include，替换JNI/lookup接口以注入边界；必须标明这是host seam，不冒认ART/实板生命周期验证。
## 边界
### 允许修改
- benchmark/2026-10-20-t18-audiotrack-size/**
- specs/toutiao-video-playback/t18-audiotrack-effective-size.spec.md
- tools/spec-checks/tests/toutiao_t18_audiotrack_size.rs
### 禁止
- 不改既有冻结文件、主树、设备、运行中进程；不构建生产DSO、不推送。
## 完成条件
场景: 实际getter正常值及申请值区分
  测试: ttvideo_t18_audiotrack_size
  假设 owner的cap为16384且bytesPerFrame为4，Java申请值可以不同
  当 host seam调用实际getter并改变当前已用字节
  那么 仅使用已核d4fa owner中cap/bytesPerFrame的有效ring写入上限；两次均返回4096且owner字段不改变
  并且 保持现有getShim和mu路径；不新建DSO按猜测偏移读对象
  并且 仅一条()I注册，走原逐项RegisterNatives；禁止UnregisterNatives
场景: 失败与异常保留
  测试: ttvideo_t18_audiotrack_size
  假设 缺owner、停止中、无完整帧、非法bytesPerFrame、结果超过jint或原有异常
  当 调用实际getter
  那么 无对象或无合法完整帧/结果溢出时抛IllegalStateException，保留原pending exception；返回负值
场景: 交付与部署分界
  测试: ttvideo_t18_audiotrack_size
  审核: human
  假设 源码profile局部语义与精确ELF一致
  当 审核配方与输入SHA
  那么 本轮是源码与离线编译准备。原d4fa整库producing closure仍unknown；host检查不签运行态或音频输出
## 排除范围
- 本任务不部署、不修ANW、随机退出、AudioTrack容量调整、release并发协议或其他JNI方法。
