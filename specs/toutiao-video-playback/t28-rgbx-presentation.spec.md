spec: task
name: "T28 admitted RGBX2 presentation through OH12"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t26-yv12-presentation]
tags: [offline, rgbx, bounded]
---
## 意图
实际T26首geometry请求format2成功但物理OH11进入Mali精确入口返回NULL。补已准入player的RGBX2物理表示：OH12/RGBA存储，对caller保持RGBX2，有效像素alpha255。预计移走toutiao本次首致命点，不宣称全部EGL错误、视频或音频通过。
## 已定决策
- 从冻结fc58联合源派生T28独立副本，仅geometry的format2映射改12；成功记录的RGBX2请求才进入新分支。format0保持已记录请求；未知/evicted/非RGBX走原路径，不猜格式。
- 在既有r26_prepare位置核OH12/Android1、实际宽高/byte stride/size/指针及像素stride一致后，原bits/宽高/stride不变只向caller报告format2。无scratch分配，无provider加载，无ABI变化。
- 在既有before_unmap位置持ACTIVE事务，先完成全部尺寸/溢出/边界验证；然后逐有效像素只写第4字节255，不写RGB/行padding，不分配不调用provider，循环无失败分支。原Unmap/Flush顺序与次数保持。
- precheck失败整片未写，不Flush；沿原Unmap与允许时Abort，保首错/原始cleanup rc和FAILED资源。8槽alias互斥、EVICTING、额外引用、三GOT门不变。reset事务opaque标记避免复用残留。
- T26的YV12转换和其他格式保持，T27原源及同实例getter/create接线原样。只做一个联合候选，原始构建日志/依赖SHA持久保存。
## 约束
- 仅离线实现、真实C测试和生产重链；禁止HDC/设备/部署/push。旧T20/T23/T25/T26/T27冻结源只读。
- 原返回值和引用计数保持；不得伪报RGBX却任由RGBA alpha未定义，不降低三槽same-provider门，不消费eglGetError。
## 边界
### 允许修改
- benchmark/2026-10-20-t28-rgbx/**
- specs/toutiao-video-playback/t28-rgbx-presentation.spec.md
- tools/spec-checks/tests/toutiao_t28_rgbx.rs
### 禁止
- benchmark/2026-10-20-t26-yv12/**
- knowledge/frozen/**
## 完成条件
场景: 真实RGBX路由保持外部格式
  测试: ttvideo_t28_route
  假设 独立fixture使用真实shim到pair到R14和新RGBX分支以及已核player三槽
  当 请求format2且提供17x3和padding stride80的OH12
  那么 caller得到原bits/17x3/stride20/format2且原Unmap前每有效alpha255
  并且 RGB和padding不变，原返回值和引用计数保持；三槽same-provider门拒错误caller或任一槽，geometry0/3及Unmap/Flush各一次
场景: 格式历史和原行为不回退
  测试: ttvideo_t28_regression
  假设 已记录RGBX的format0和失败geometry以及unknown历史
  当 运行真实链和原YV12/其他RGB用例
  那么 仅成功RGBX请求被适配，原YV12布局与其他RGB输出不变
场景: 预检查与provider失败保持
  测试: ttvideo_t28_failures
  假设 OH11、短size、非4倍stride、溢出或Unmap/Flush失败
  当 执行prepare或提交前校验
  那么 校验失败无目标写且无Flush，原首错和cleanup结果保留且不重复操作
场景: alias与槽复用不越界
  测试: ttvideo_t28_concurrency
  假设 两个不同wrapper共享OH且实际pthread同步竞争
  当 RGBX事务占槽并尝试第二次锁和后续槽复用
  那么 同OH仅一个ACTIVE且8活动槽上限不变，完成后opaque状态清除且其他格式不受影响
场景: 冻结基线及生产ABI
  测试: ttvideo_t28_build
  假设 原fc58源与输入已钉且check_frozen通过
  当 独立OH构建并复现基线
  那么 仅离线实现、真实C测试和生产重链；HDC/设备/部署/push调用数0，旧T20/T23/T25/T26/T27冻结源SHA全等
  并且 基线字节全等，78导出/符号版本/依赖不漂移，两个实际consumer ABI通过且原始stdoutstderr rc持久
场景: 实板改善只能由未来窗口确认
  测试: ttvideo_t28_build
  审核: human
  假设 未来独立授权窗口和原计划回滚
  当 核真实请求2与物理12及caller2记录和最终原图
  那么 仅实际import返回和截图支持其范围，离线构建不冒称播放或永久封板
## 排除范围
不诊断随机退出，不改网络/音频/播放器ELF，不改其他EGL策略，不进行本轮设备操作。
