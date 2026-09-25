# #30 缩略图配置在 5cd1e3dd 的复验

**缩略图修复在本板成立：__ndk1 缺符号行数从296降到0，截到真实视频封面和文章配图。** 候选首轮仍有既有null Looper导致UI退出，第二轮得到完整图片证据并在约185秒观察结束时仍存活。不宣称长期稳定或文章详情页已修复。原#30包含的完整可读文章页仍未验证通过。

本轮独立分支 `verify/feed-images-30-cx`，只改启动配置/验证夹具，不改native库或APK，不新增C++符号垫片，**零编译**，符合#36。复用codex-2先前提交`0232e09225b51879262f46d168de0005f1b5d447`审过的targets，在板 `5cd1e3dd00000000000000000923012c` 独立做前后对照。

## 固定底座和参数

使用本板 `integrate-14/framework/device-report.json`，来源 `out-integrate/{appspawn,native-runtime,framework-runtime,framework-boot}`，WebView为 `out-sp20/webview-candidate`。不混入out-all0925/#23 Sensor/属性修复，不添加metasec target；不修改ccache配置。launcher复用已有out-touch21/probe-local，只读取westlake-touch21源构建部署助手，不重编runtime。每轮全新目录/应用数据。

baseline三个targets是libvision_core.so、libc++_shared.so、libsscronet.so。full追加16个，合计19个；sscronet native/net双参数保持，观测环境WL_TOUCH_TRACE=1保持。精确argv在各launch-config.json，完整名单在[targets.json](targets.json)。无数据/环境伪装或应用逻辑改写。

本板实际读取OH libc++ SHA256 `1cdf4eaecdb990769edce8f35d72034affb76ce47e6d7a946d15b62f18969725`，__ndk1导出0；APK版`e8373ee43274541efd2d34fe0588d55bf953612e1417ad47cfd2c4bd1aa383d0`，导出1760。原始符号清单保存，含共享弱引用析构符号对照。当前138个APK库与先前ELF库存哈希逐项一致。#19真实shadowed_libraries推导器复算：15个已有失败库都在C++反向依赖闭包；ttheif_dec不在该闭包，是任务指定的HEIF解码依赖，单独列入，未把67库静态闭包全部盲加。

全部五轮的306个source_files及WebView报告完全相同；最终从板上复算306项framework文件和6项WebView文件SHA256，312/312匹配，见[final-provenance.json](evidence/final-provenance.json)。目录 `evidence/inputs/` 保留ELF清单、138项比对与推导结果。

## 实测与图像

|轮次|child|__ndk1缺符号行数|图像与终止状态|
|---|---:|---:|---|
|baseline-1|7520|296|信息流可见，视频灰色占位；99s CrBrowserMain/libhwui SIGSEGV|
|full-1|12825|0|信息流可见但图片未完成；null Looper导致UI退出，随后夹具停止进程|
|full-2|18495|0|真实视频封面、文章配图；观察起止约185.09s，结束仍存活，随后主动停止|

计数按原始日志**行数**，包含重试，非独立加载次数；观察长度不同，不作速率比较。日志完整保存，原文可能含无效UTF-8字节，gzip保留原始字节；行号解析采用errors=replace。

- [基线frame-067](evidence/baseline-1/frame-067.jpeg)：多条信息流标题正常，大视频封面灰色。
- [候选full-2/frame-095](evidence/full-2/frame-095.jpeg)：篮球比赛真实视频封面，带播放按钮。
- [候选full-2/frame-137](evidence/full-2/frame-137.jpeg)：上半为真实视频封面，下半为“去世仅1天，人民日报对游本昌的称呼变了……”文章的人物配图；同屏满足两类图片。

这是实际网络返回内容，不是我们替换的图片；标题只是界面证据，不为新闻真实性背书。推荐内容随轮次变化，不声称同一图片的固定离线重放，也未抓取逐张文件证明所有配图格式都是HEIC。

三轮均通过同意并出现信息流；c通道同意动作及VT在案。full-2在约100秒后注入上滑，滚动后仍有真实图片；约169秒补充`i 380 1280`点击文章，日志L87193启动`ArticleInflowActivity`，L87474到BEFORE scheduleTransaction。最后截图仍非可读详情页，且本轮到预设观察上限后主动停止，不能宣称文章加载失败根因或文章通过；不得把最初MainActivity的B47-SLA当作点击后的新Activity证据。

## 未隐藏的异常

baseline-1进程99s崩溃：faultlog为CrBrowserMain、libhwui、SIGSEGV地址0x8。完整faultlog留存，不用faultlog表面相对pc推断跨库同因。

full-1在L18355起INITCHILD-FAIL，L18359为Handler读取null Looper；链为X.DEv → X.DPS → X.DPb，与先前#21族一致。full-1/frame-104只剩host界面，**排除图像验收**。这是候选首轮失败，不能隐藏，也没有本轮新的受控证据排除配置关联；不从第二轮成功外推所有轮次稳定。

三轮均有work_thread SIGABRT日志，分别L12665/L9966/L13370，不能写成零fatal。还有Chrome_ProcessLauncherThread的child-service元数据异常；候选另有platform-back-handler加载app_lib/libmetasec的errno13。它们不是__ndk1缺符号，保留为独立缺口，未在缩略图配置任务修改。full-2有这些日志后仍得到图片和后续Activity启动记录，不把任一fatal行自动等同于主进程已经死亡。

## 对照和验收范围

Noice child24358：真实i点击Welcome→Design your ideal environment，额外观察65.1366s；两条既有mainActivityPi NPE在L587/L613，非零异常。Wikipedia child27454：真实i点击进入Data & Privacy，额外观察65.1159s；[最终截图](evidence/control-wikipedia/after-settled.jpeg)。两者只声明启动/翻页烟测，不宣称完整应用功能。

本次用户列出的缩略图验收：缺符号清零、视频封面/文章配图、同意/信息流路径、Noice/Wikipedia对照分别留证。图像功能可采认；若按原黑板#30的“完整文章页不回退”条件，全项仍不能报通过。无需也未在本轮修WebView/线程异常。

## 证据与复验

原始VM输出：`~/a2hlab/board/5cd1e3dd00000000000000000923012c/images30cx/`；脚本：`~/a2hlab/ws/out-images30cx/`。所有VM命令经orb -m a2hlab bash -lc。只用本板；另板#30仅引用已归档的配置/ELF清单，未连接它。

提交包含targets、采集夹具、原始截图/VT/日志/faultlog和manifest。未提交第三方.so/APK二进制，未改共享out/或运行时代码。截图人工查看，脚本语法/证据哈希/日志计数与提交对象逐项复核；未重编。按loop规程执行宿主已知答案测试：69项，OK（2 skipped）；133份证据哈希、日志行号及VM原始日志逐字节回读校验通过。只commit未push。

离线复验：`python3 benchmark/2026-09-25-feed-images-cx/verify.py --git`。**R2=partially（整体）**：本板图像修复verified；稳定性/完整文章页未通过或未覆盖，详见逐轮记录。

收尾按PID、exe和starttime核验后停止本轮touchfwd；本轮应用/父进程已由采集夹具停止。最终相关进程列表为空，部署目录和原始证据保留；见[final-cleanup.json](evidence/final-cleanup.json)。未修改网络配置。
