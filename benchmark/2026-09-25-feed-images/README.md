# #30 信息流图片：Android ABI target 配置

缩略图修复已实测成立；总验收仍 blocked、R2=partially，因为文章点击后的可读详情页未通过。

本轮只改启动配置：`targets.json` 在原有三个 native targets 上添加 16 个库，保持 `libsscronet.so` 的 native/net 双参数；不改 APK、framework、native 二进制，不添加 C++ ABI 符号垫片。独立分支 `fix/feed-images-30`，只 commit、不 push。

完整候选的 [原始截图 full-1/frame-101.jpeg](evidence/full-1/frame-101.jpeg) 同时显示“沪宁高铁”视频真实封面与“9月24日24时国内成品油调价”文章的真实配图。基线 [baseline-2/frame-109.jpeg](evidence/baseline-2/frame-109.jpeg) 的视频和小视频仍是灰色占位。联网推荐内容会变化，这不是同一张图片的离线重放对照；对照控制的是同 APK、同构建、同板、fresh 数据与相同网络条件。

## 配置与根因

固定板 `5ea34a4500000000000000001123012c`。从这块板实际读取 `/system/lib64/libc++_shared.so`，`llvm-nm -D --defined-only` 计数：OH 版 `__ndk1` 导出 **0**，APK 版 **1760**。见 [libcxx-providers.json](evidence/libcxx-providers.json) 与两份 exports 清单。OH 版 SHA256 `1cdf4eaecdb990769edce8f35d72034affb76ce47e6d7a946d15b62f18969725`，APK 版 `e8373ee43274541efd2d34fe0588d55bf953612e1417ad47cfd2c4bd1aa383d0`。

先仅增加 `libbdheif.so`、`libttheif_dec.so`、`libgifimage.so`，`images-1` 已显示 Tesla/长三角两张小视频封面且 `__ndk1 … symbol not found` 为 0。再按 #26 已归档日志补齐 15 个实际同因失败库，去重后新增 16、合计 19 个 native targets。`libttheif_dec.so` 自身没有 `__ndk1` 未定义符号，是明确指定的 HEIF 依赖。

#19 的真实 `shadowed_libraries` 推导器复核：15 个失败库均在 C++ 依赖闭包；完整静态闭包为 67 个库，不能推断它们都在此场景加载，未直接全部加入。原始失败行和 ELF DT_NEEDED/SHA256 见 [published26-archived-failures.json](evidence/published26-archived-failures.json)、[elf-and-errors.json](evidence/elf-and-errors.json)、[target-derivation.json](evidence/target-derivation.json)。#26 来源是 VM 上已有离线归档，未连接或操作另外两块板。

## 构建与实验身份

运行时源基线 `b3dae7aed16f10ba492e2bd6c7a02bc17b2bbf58`，包含 #11/PM；采用 #14 集成 lineage 的 `out-touch21/wake`、framework/boot 与 `out-sp20/webview-candidate`，直接复用 #25 的 `framework-wake/device-report.json`。本任务不混入 #28 新 framework。APK SHA256 `a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395`。

[部署来源](evidence/runtime-provenance.json) 比较各轮 `source_files` 全部 306 个静态文件哈希，必须零差异。启动参数记录在每轮 `launch-config.json`；fresh 复跑明确清理本部署的 app-data/data/webview-t-data。日志、截图、maps、输入动作、faultlog 都保留；没有清空板上公共日志。

同意用已建立的 `c 600 1273` performClick 通道；文章使用 `i 380 297` 真实 DOWN/UP。截图前前台化宿主并等待 1 秒。`full-2` 在首个 ≥85 秒截图后点击；后续 article 对照改为首个 ≥70 秒截图后点击，避免错过生命周期。截图周期约 10 秒，时间从 child 启动后 watcher 开始计，不是精确应用启动耗时。

`baseline-1` 的早期黑图源于宿主前台化时机，排除视觉验收，采用修正采集方式后的 baseline-2。baseline-2/images-1 的晚到手动点击发生在进程已停止后，mailbox 创建失败，绝不计为文章点击成功。`full-1` 的滑动后出现登录推广页，不计为文章进入。

## 实测结果与验收边界

`__ndk1 … symbol not found` 按原始 stderr 的**行数**统计，包含同一次类初始化失败的重试，不当作独立 dlopen 次数；完整可重算结果见 [results.json](results.json)。

| run | native targets | 错误行数 | 图像／页面结果 |
| --- | ---: | ---: | --- |
| baseline-1 | 3 | 1568 | 早期黑图排除；只保留日志计数 |
| baseline-2 | 3 | 1486 | 灰色视频封面，后有既有 nullLooper UI 异常 |
| baseline-3 | 3 | 600 | 真点击启动详情，随后 WebView RenderThread 崩溃 |
| images-1 | 6 | 0 | 真实小视频封面，后有既有 nullLooper UI 异常 |
| full-1 | 19 | 0 | 同屏真实视频封面及文章配图；约 300 秒观察后主动停止 |
| full-2 | 19 | 0 | 96 秒 ICU/free 崩溃，点击未消费，不算通过 |
| full-3 | 19 | 0 | 真实篮球视频封面；真点击启动详情，随后 WebView 崩溃 |

所有头条日志仍有一条 `[WESTLAKE-ICU] u_setDataDirectory symbol not found`，不是 `__ndk1` ABI 错误，未在本任务修复。每轮另有 `work_thread` 的 SIGABRT 日志；即使 full-1 后续 UI 仍可见，也不把它藏成“零 fatal”。详细 fatal 行、UI 异常、该 PID faultlog 分开列入 results。

**文章页阻塞**：baseline-3 和 full-3 都有真实 `TOUCH21 post/run/return-handled`，都启动 `com.ss.android.detail.feature.detail2.view.NewDetailActivity`，但均未截到可读文章详情页。两份 faultlog 的 `pc` 减映射起始地址加映射文件偏移，均为 `libwebviewchromium.so + 0x1e006f0`，线程 RenderThread、空地址 SIGSEGV。faultlog 顶帧自报相对地址不同，不能直接拿其 `#00 pc` 比较；`results.native_faults` 保留归一化步骤。此对照支持“不是本轮才出现”的判断，不宣称完整文章流程已通过。要解除阻塞，需要修复此 WebView 故障并复跑真实点击、截到文章页。

full-2 另有 `ReferenceQueueD → libicu_jni/libicui18n/libicuuc → musl free/get_meta` 故障（96 秒），原因未定；本轮没有足够证据排除其与新增目标的关系，也没有证据把它归因于该配置。保持单独记录，不用基线的 WebView 同签名为它免责。

Noice 真点击至 `Design your ideal environment`，UI/进程身份观察 **66.513s**；Wikipedia 真点击至 `Data & Privacy`，截图人工核对，观察 **66.803s**。两者无 fatal/UI 返回/该 PID faultlog。Noice 原有两条 `mainActivityPi` NPE 仍在日志 **L708/L734**。这只是启动/翻页烟测，不是完整应用功能验收。

因此 #30 条款①错误清零、②真实两类图、③同构建、⑤两控制烟测、⑥仅提交均有证据；④同意和信息流通过、点击已触发详情但可读文章页未通过，**ACK(blocked)，R2=partially**。没有为通过验收而改 SDK 行为、跳过验证、替换图片或修改 native 代码。

## 复验

离线重算与证据/提交对象检查（宿主，无板操作）：

```sh
python3 benchmark/2026-09-25-feed-images/scripts/verify30.py --git
```

上板脚本必须从 VM 包装入口运行，且一次只跑一个 UI 应用。示例（新 run 名，避免覆盖已有证据）：

```sh
orb -m a2hlab bash -lc 'python3 /Users/zhaoyue/orca/workspaces/westlake-harness-images30/benchmark/2026-09-25-feed-images/scripts/watch30.py review-full full --article'
```

`launch30.py` 的 full 模式读取 `targets.json` 并传给既有 probe；完整精确 argv 见证据。图片格式未通过抓取逐张判定，因此不称文章小图本身一定是 HEIC。未证明所有 19 库都实际执行，maps 中实际映射名单见 results.json。
