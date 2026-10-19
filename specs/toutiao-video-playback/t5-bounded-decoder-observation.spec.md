spec: task
name: "Bounded decoder observation successor"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t4-player-observation]
tags: [offline, observability, human-review]
---
## 意图
r9 retry的256条镜像在video resetCodec处耗尽，后续缺日志无法判定解码结果。制作独立r10观测件，仅扩大有界镜像预算，保留未知后续消息；本契约不授权上板，也不以日志代替动态画面与声音验收。
## 已定决策
- [platform-specific] 从candidate-r8/ttplayer_log_mirror.c SHA3becb0f688e9dba9f5626a8453756848dd51e2f5347c4688672de0fbe3384e8e复制到candidate-r10，仅将MIRROR_ATTEMPTS从256改4096，源码其余字节不变。保持每条1024总字节、饱和原子计数、fd2单次write无重试；每provider实例至多4MiB尝试写入。现有write可能阻塞，增加次数会扰动运行，报告必须保留此限制。
- 不做事件过滤、运行时重置或全局liblog改动。原样转发每次恰好一次，参数、返回值、后端errno与原函数一致；镜像使用入口errno，危险格式/%n/别名拒绝行为不变，超限仍转发。
- 独立复制既有host oracle并适配4095/4096/4097边界，加入并发饱和检查；混合参数/长格式/%m/%n/位置参数/别名既有用例继续覆盖，原测试文件不改。
- 复制并调整已验证r8构建配方，只重编compat。固定原OpenSL源码cf45ad43、link-only锚点、真实liblog d8ad及原工具链，源码新SHA显式钉住。player0b4d95c5及105重定位、media d2882303和r9 run b5625757原样复用；不重新派生这些件。
- 构建前check_frozen；原始命令/stdout/stderr/rc当场落持久位置。先交源码/recipe/host oracle供独立复核，外环认可后才执行生产构建；输出实际新compat SHA、导入导出比较与构建哈希清单。没有构建就明确not built。
- 构建机挂载不可用时，可在candidate-r10另加本地Docker运行器，配方显式选用它并记录脚本SHA；仍用原镜像与逐件同SHA工具链/sysroot，读写挂载或docker cp传输仅显式SOURCE_REPO、OH_NATIVE和OUT；copy模式可复用外环专用无挂载容器，必须核镜像身份并保留每阶段同步与执行rc。不得改共享dockbuild、重启VM或改变编译链接参数；环境替代不算源码构建失败。
- 对接收据写独立检查器，Rust选择器转调Python和真实host oracle。构建验收仍需人工审实际日志；动态provider及播放明确unknown。公开材料不含原始URL/账户/用户数据。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/candidate-r10/**
- tools/spec-checks/tests/toutiao_decoder_observation.rs
- specs/toutiao-video-playback/t5-bounded-decoder-observation.spec.md
### 禁止
- 不改r8/r9历史源码产物、冻结项、系统liblog/runtime、其它worktree或API历史表；不执行设备命令，不推送。
## 完成条件
### Rule: bounded-transparent-observation — 有界镜像保留原行为
场景: 单常量变化与原输入身份
  测试: ttvideo_decoder_observation_source
  假设 原r8镜像源码与复用的三个运行输入具有指定SHA
  当 检查r10源码差异与构建入口
  那么 差异仅为256到4096常量且配方选中r10新源码与新SHA，原历史文件未改变；可选本地Docker运行器仅替换挂载或文件传输方式且工具链哈希和编译参数不变
场景: 饱和边界及并发不越界
  测试: ttvideo_decoder_observation_forwarding
  假设 独立参考后端与r10镜像已链接
  当 执行4095、4096、4097次调用及多线程并发饱和用例
  那么 镜像尝试不超过4096且每条不超过1024字节，全部调用都恰好转发一次且返回值与errno保持
场景: 危险格式与超限仍保留转发
  测试: ttvideo_decoder_observation_forwarding
  假设 存在混合参数、长格式、百分号m和百分号n含位置参数与别名输入
  当 在预算内与超限后执行独立参考用例
  那么 原后端参数和可见副作用一致，危险格式不会在镜像中先求值，stdout没有镜像输出
场景: 构建输入漂移或缺执行收据拒绝
  测试: ttvideo_decoder_observation_receipt
  假设 源码、工具链或输入SHA漂移，或缺原始rc0执行日志
  当 请求接收候选
  那么 检查器非零拒绝，不输出部署通过或播放通过
场景: 实际生产构建审查
  测试: ttvideo_decoder_observation_receipt
  审核: human
  假设 独立host oracle通过且外环已复核配方
  当 复核新compat构建rc0原件、工具链和导入导出比较
  那么 只有compat重编且复用的player/media/run SHA不变，观测扰动和动态绑定未验证写入报告
