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
- r4（2026-10-19 r3 上板后真实首崩溃的确定性修复）：r3 加载墙已过（libmffmpeg d2882303、libttmplayer+libvcbasekit 在 android ns 加载无 __ndk1 错）；child 6662 在 player 线程 async_video_pla 崩 SIGSEGV SEGV_ACCERR，PC libttmplayer 0xde714（按 load-bias 调和，非帧报告 +0x21a6714），store x0,[x9]，x9=GOT 0x473e58 被 OH provider FUNC 抢占到 libEGL 代码页。根因=libttmplayer 的 GLES3/EGL proc-loader 缓存槽以 OBJECT GLOBAL DEFAULT 定义在 .bss（105 个 gl*/egl*），其 GLOB_DAT 在 OH musl（do_relocs L1389 只对 STB_LOCAL 直绑 self，st_other/DT_SYMBOLIC/DEEPBIND 不命中）被 provider 同名 FUNC 抢占。最小候选=单件派生 libttmplayer.so（精确 b427 输入），把这 105 个族 GLOB_DAT 改为 R_AARCH64_RELATIVE、addend=各自 .bss st_value（musl L1452 *slot=base+addend，自绑回本 .bss 写槽）；派生门：输入 SHA/尺寸锁定、仅转换 OBJECT GLOBAL 且 st_shndx==.bss 且 名以 gl/egl 开头者、数量==105、显式排除 4 个 C++ vtable（_ZTVN6vcloud8ttplayer…E，.data.rel.ro）、除这 105 条 reloc 的 r_info+r_addend 外零字节变化、符号表/hash/代码/段权限不变、输出固定点 SHA。保留 OH EGL/GLES FUNC 语义与 P0，拒绝输入漂移，拒绝放宽代码页写权限/mprotect。R4 只新增 player 派生，r3 三件（run 79275cf9 + compat 9f558aaf + mffmpeg d2882303）原样保留，不整代烘焙；部署为四件（executor=cx-seal CAS r6 draft），libttmplayer 单件 backup+回滚，物理前像/metadata 按 video-r4-readonly（b427, 4662040B, 644:20011206:20011206, appdat, 同 inode）。被否方案记录：STV_HIDDEN（musl 不看 visibility，无效）、STB_LOCAL（需 dynsym 重排+sh_info+hash 一致，影响面大）、DF_SYMBOLIC/DEEPBIND（musl 不命中）、Surface 窗口包装（非本因，暂不走）。
- 离线门：导出仅两个IID、DT_NEEDED含libOpenSLES.so、不导出libc类符号、用t1 reproduce.sh闭包加入该库后libttmplayer未解析集为空。
- 保留相同namespace/ABI与未改行为（r2/r3 例外：libttmplayer 由 ns0 移入既有 android-native namespace 是本次核准的路由修复；r3 对 libmffmpeg 仅做 DT_INIT_ARRAYSZ 8→0 的单字节派生，去掉 bionic 本就跳过的空 init 槽，不改导出符号/代码段/ABI/其它构造器——已 strings 外其余字节逐字相同）（r4 例外：仅把 105 个 GLES/EGL proc-loader 缓存槽的 GLOB_DAT 改成自绑 RELATIVE，符号表/导出/代码段/hash/段权限不变，只改 .rela.dyn 该族 105 条的 r_info+r_addend）；构建前check_frozen、逐部署件strings/class/open-site对照、工具链哈希和原始stdout/stderr及rc=0都入回执。
- 功能检查按真实修复API增加正例、拒绝例和释放/生命周期测试；不以返回OK、空数据或注册成功代替视频解码/呈现。
- r9（2026-10-20 r8实际media连接-97后静态追踪）：仅派生run配置（79275cf9→b5625757）：NET_TARGETS保留libsscronet.so并加入libmffmpeg.so；ANDROID_NATIVE_INHERIT原列表追加现有netcompat f6c354d1，不改其源码/二进制；PRELOAD原样保留（它是单一路径，不能冒号追加）。r8 player0b4d/compat6e83/media d288全部复用，新增运行时编译为0。静态证据：mffmpeg TCP读取addrinfo ai_addr+32，OH libc原布局+24，既有netcompat提供转换但旧caller选择/命名空间配置未覆盖media；这是候选动机，尚非已证实际provider根因。上板必须读取mffmpeg getaddrinfo/freeaddrinfo实际GOT成对等于精确netcompat函数，任一不匹配就失败回滚；不要用配置存在代替符号绑定。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/candidate/**
- benchmark/2026-10-19-toutiao-video-playback/candidate-r2/**
- benchmark/2026-10-19-toutiao-video-playback/candidate-r3/**
- benchmark/2026-10-19-toutiao-video-playback/candidate-r4/**
- benchmark/2026-10-19-toutiao-video-playback/candidate-r9/**
- tools/spec-checks/tests/toutiao_network_config.rs
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
场景: r9配置最小化与复用产物身份
  测试: ttvideo_network_config_receipt
  审核: human
  假设 r8三个运行时二进制已归档且网络静态路径已定位
  当 仅派生NET_TARGETS与INHERIT两行并核所有输入SHA
  那么 PRELOAD与所有其余配置逐字不变且三个二进制不重编；检查只证明离线输入，不证明实际网络provider或播放
## 排除范围
- 随机崩溃根因、安全机制改造、用户数据清理和自动远程推送。
