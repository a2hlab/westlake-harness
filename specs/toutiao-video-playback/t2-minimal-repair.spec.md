spec: task
name: "Toutiao video first-blocker minimal repair"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-static-evidence]
tags: [media, ready, opensles-iid]
---
## 意图
仅在t1把当前首阻断API归属到精确消费者与提供方后，制作独立可回滚候选；优先移植已验证实现，保持已封板的主窗口和图标路径。t1已确认首阻断：61b boot 8f7f12bf child 9290 中 libttmplayer.so 在 namespace 0 重定位缺 SL_IID_ANDROIDSIMPLEBUFFERQUEUE（selected-change.json）。本任务只解决该加载阻断，不宣称播放。
## 已定决策
- t1的selected-change.json必须绑定input SHA、源码blob、允许文件列表、预计移走首致命点的key与已验证来源；外环确认后才开建，unknown或external_blocked禁止开建。
- 只在candidate下复制并修改获准的源码单元，不改冻结原件；需要不同文件时先修订契约再lint。
- 获准源码仅两件，逐字复制不改：opensles_android_compat.c（sha256 cf45ad430a08cbe090f030357a346be7a0bac49f48c06196a11c7818de3f9351）与link_only_stub.c（sha256 fa47585b8fb702e8da05c52d732c9c964b5ec50a34edfa6815dea7f962898e13），配方为westlake build.sh 0d8e4f43第89至93行，经dockbuild.sh cc用OHOS clang 15.0.4 feef13a3编出libopensles_android_compat.so。
- 部署输入仅两件：新增/data/local/tmp/asx/libopensles_android_compat.so，以及run.sh第33行LD_PRELOAD末尾追加该路径（d3518cef→ea98494255b05699ca24b134e6ada8849b023b4ab59d3d7e291194cfa8425f73），libttmplayer保持namespace 0；回滚为恢复d3518cef并删除该库。
- r2（2026-10-19 实板新首阻断：namespace 0 中 libttmplayer 依赖的 libvcbasekit 绑定到 OH libc++_shared 缺 std::__ndk1，见 static/selected-change-r2.json）：不新增源码、不重编；只在 candidate-r2 下产出 run.sh，相对 P1 候选仅改两行——WESTLAKE_ANDROID_NATIVE_TARGETS 追加 libmffmpeg.so:libttmplayer.so，WESTLAKE_ANDROID_NATIVE_INHERIT 追加 libopensles_android_compat.so:libOpenSLES.so；P1 证据与候选原样保留。r2 静态门须对 libttmplayer 递归依赖闭包按实际 namespace 与 provider 优先序求解，未解析集为空方可送审。
- r3（2026-10-19 外环+cx-seal 静态否决 r2 后）：r2 的 run.sh（79275cf9）原样复用，新增单一派生件——把物理 $RT/lib/arm64-v8a/libmffmpeg.so（fecf91e1）按 RouteB SanitizeInitArray 完全相同语义与字节派生为 d2882303（仅 DT_INIT_ARRAYSZ@0x48aca8 8→0，去掉那个 bionic 本就跳过的空 init 槽），使 libttmplayer 的 by-name DT_NEEDED 与 Java 显式加载共用同一 file/inode、不再撞 musl do_init_fini 空槽。派生件只允许在 candidate-r3 下由 derive_mffmpeg.py 产出，带输入/输出 SHA、固定点、非零槽拒绝、输入漂移拒绝与原始 rc=0 回执；大二进制不入库（持久目录+hw益镜像），源码/配方入库。实际部署三件 run+compat+mffmpeg，单件 backup+回滚，前像/metadata 按 video-r3-readonly。闭包门不得改为全通过：已证 loader 规则与未证 provider 绑定分列，未证项作小窗验证项（load-experiment-card.md），不要求预测全部播放阶段。
- 离线门：导出仅两个IID、DT_NEEDED含libOpenSLES.so、不导出libc类符号、用t1 reproduce.sh闭包加入该库后libttmplayer未解析集为空。
- 保留相同namespace/ABI与未改行为（r2/r3 例外：libttmplayer 由 ns0 移入既有 android-native namespace 是本次核准的路由修复；r3 对 libmffmpeg 仅做 DT_INIT_ARRAYSZ 8→0 的单字节派生，去掉 bionic 本就跳过的空 init 槽，不改导出符号/代码段/ABI/其它构造器——已 strings 外其余字节逐字相同）；构建前check_frozen、逐部署件strings/class/open-site对照、工具链哈希和原始stdout/stderr及rc=0都入回执。
- 功能检查按真实修复API增加正例、拒绝例和释放/生命周期测试；不以返回OK、空数据或注册成功代替视频解码/呈现。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/candidate/**
- benchmark/2026-10-19-toutiao-video-playback/candidate-r2/**
- benchmark/2026-10-19-toutiao-video-playback/candidate-r3/**
- specs/toutiao-video-playback/t2-minimal-repair.spec.md
### 禁止
- 不上板、不改冻结文件、不改主窗口几何、图标watchdog、启动器或应用数据；不替换完整运行时世代。
## 完成条件

### Rule: evidence-before-verdict — 先绑定证据再判断
场景: 绑定首阻断的可复现候选
  测试: ttvideo_build_receipt
  审核: human
  假设 t1已审查确认且selected-change列出精确允许源码
  当 在candidate目录仅改获准源码、运行check_frozen与namespace扫描后重建并执行API正反例及释放生命周期测试
  那么 记录输入输出SHA、工具链、原始stdout/stderr成功日志、源码差异及未改ABI，产出单变量部署和回滚输入
场景: 未绑定或漂移输入拒绝
  测试: ttvideo_build_receipt
  审核: human
  假设 首致命点unknown或输入SHA与selected-change不同
  当 请求构建
  那么 拒绝发布候选且保留失败回执
场景: 行为桩不冒充修复
  测试: ttvideo_build_receipt
  审核: human
  假设 实现只返回OK或仅有JNI注册且无帧输出
  当 审查行为与差异
  那么 拒绝认定播放修复且不进入成功封板
## 排除范围
- 随机崩溃根因、安全机制改造、用户数据清理和自动远程推送。
