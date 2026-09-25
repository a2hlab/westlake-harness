# #42 板上三臂对照（2026-09-25 夜，09-26 收尾）

两档 app AOT 均被 ART 接收。**性能验收 blocked；R2=partially**：完成三臂各三次正式启动尝试，但 verify 全部提前退出、speed 一次提前退出，未取得每臂三份有效点击。九次正式尝试均以 signal 11 结束。不能从两份 speed 存活样本推断 AOT 的稳定提速，更不能宣称文章页可用。

## 配置、部署与协议

板 `5cd1e3dd00000000000000000923012c`，Mac HDC，经 VM `hdc_mac.sh` 调用。独立框架 stage `/data/local/tmp/a2hlab-framework-aot42-{baseline,verify,speed}`。从本板既有 touch21 stage 克隆，再按 #38 v7 的文件哈希覆盖差异，307 个框架文件及 47 个系统固件文件核对；两档加入 3 个应用 AOT 文件，310 文件核对。参考、覆盖来源、哈希检查、preload 日志全部在 `device-evidence/framework-*`。初次 verify stage 哈希断言失败原件保留；随后同步并逐项重读比对通过，再部署应用，不将失败读回冒称成功。

APK SHA256 `a1112a0c…`；libart `009a08fb…`，BCP/boot 同 VM 冻结输入。应用路径 `/data/local/tmp/asx/toutiao.apk`；邻接 `oat/arm64/toutiao.{odex,vdex,art}`。baseline 无应用 oat；verify 映射只读 odex；speed 映射含约 483MB 的 r-xp 应用机器码，两档都有 `[IMG] Loaded …toutiao.art`。具体行号及 mappings 见 device-results。全局 `/data/misc/apexdata/... Could not check odex` 权限警告仍存在，**不表示邻接产物被拒绝**。未改权限或关闭校验。

使用 #38 idle-a1 的 launch-config、out-sp20 WebView、19 个 Android native targets（含 sscronet 及网络目标），完整参数与环境见每轮 launch-config.json、run.sh。没有应用源代码或运行时改动。正式轮复用同一臂的已部署 native 文件，但每轮删除并重建自己的 app-data/data/webview-t-data，记录 data-provenance；重启自己的 IME host 清除旧焦点/键盘状态。**不复用应用数据**。不清系统页缓存，因此不是磁盘冷启动实验；网络信息流内容可变化，也不是完全相同内容的配对实验。

正式顺序：baseline-r1 / verify-r1 / speed-r1 / speed-r2 / baseline-r2 / verify-r2（夹具超时，剔除）/ verify-r2b / verify-r3 / speed-r3 / baseline-r3。目录均带 `formal-` 前缀；baseline 正式目录名简写 `formal-base-r*`。

每轮截图确认同意按钮后物理 uinput；最后一次同意输入完成 **60s** 后点第一条新闻（380,297）。先确认无遮挡信息流，再放行预定点击；实际偏差由 HDC 命令耗时产生，五次成功输入均为 60.25–60.38s。不是按同意按钮的 queueMs 作为条目延迟。脚本通过 eventTime 与 uinput 前后 uptime 窗口关联 DOWN/UP，再关联对应 seq 的 dispatch end。每轮开始检查进程互斥，结束只杀 PID+starttime 一致的自己进程，未触碰 bionic43。

## 正式结果

单位：queue/dispatch 为 ms，其余为 s；“—”表示未测得，绝不是 0。ENTRY 是精确行首 `B47-SLA ENTRY …NewDetailActivity` 的轮询观测区间，不是文本子串命中。轮询 uptime 在读取日志前取得，区间为近似采样定位，包含命令/采样误差。RESUMED 是随后日志标记，不等于画面显示。

|正式轮|最后同意→输入|DOWN queue|DOWN dispatch|输入→ENTRY 观测|输入→后续 RESUMED|最终退出|
|---|---:|---:|---:|---|---:|---|
|baseline-r1|60.25|15|166|0.33–0.99|12.379|signal 11，点击后|
|baseline-r2|60.38|28|207|1.09–1.82|22.169|signal 11，点击后|
|baseline-r3|60.26|8|195|1.08–1.78|12.782|signal 11，点击后|
|verify-r1|—|—|—|—|—|signal 11，同意后、条目前|
|verify-r2b|—|—|—|—|—|signal 11，同意前|
|verify-r3|—|—|—|—|—|signal 11，同意后、条目前|
|speed-r1|—|—|—|—|—|signal 11，同意后、条目前|
|speed-r2|60.30|7|151|0.32–1.04|7.240|signal 11，点击后|
|speed-r3|60.32|7|109|0.30–1.04|5.833|signal 11，点击后|

baseline 的 dispatch 中位数 195ms，speed 两份为 151/109ms；后续 RESUMED 在 speed 两份更早，**只是幸存样本的描述，不是经 n≥3 验证的收益或因果结论**。baseline 的 queue 本来已很小，不能再把首轮同意按钮的 34571ms 和 speed 条目 7ms 做除法。

截图：五份可测条目的 after-5s 仍为信息流（baseline-r1 到 after-15s 已回宿主）。没有据此取得真实文章内容显示证据，尤其不能把 ENTRY/RESUMED 判为文章成功。原图保留在对应目录的 before.jpeg、after-2s/5s/15s.jpeg；进程先退出时不会伪造 45s 图。

## 同意→首屏：只能给观测上界

视图树首次出现 feed 的截图通常仍有退场遮罩。其 2.x 秒是**视图树启发式采样时间**，不能冒称无遮挡首屏。信息流在同意前就已在弹窗后加载，所谓“首屏”也不是从零开始的网络加载。下面以已人工确认的无遮挡截图给保守上界，未取得精确第一帧/first-present 时间；不能用它比较首屏提速。

|轮次|feed 视图树截图区间（同意后）|无遮挡 before 截图区间（同意后）|
|---|---|---|
|baseline-r1|2.25–2.68|35.04–35.60|
|baseline-r2|2.23–2.70|30.89–31.37|
|baseline-r3|2.15–2.51|31.99–32.52|
|speed-r2|2.16–2.55|30.73–31.10|
|speed-r3|2.12–2.58|30.63–31.03|

verify-r1、verify-r3、speed-r1 有视图树 feed 标记但在预定条目时间前退出；verify-r2b 无同意/首屏测量。它们不计作首屏提速成功。

## 崩溃分臂统计

|正式臂|尝试数|最终 signal 11|条目前 / 条目后|stderr work_thread SIGABRT|可确认 PatchUpdateMana→shadowhook→malloc|
|---|---:|---:|---|---:|---|
|baseline|3|3|0 / 3|3|未知（没有对应系统栈）|
|verify|3|3|3 / 0|1|未知（没有对应系统栈）|
|speed|3|3|1 / 2|2|未知（没有对应系统栈）|

verify-r2b 另有 stderr **TicketGuardNetw，SIGSEGV@0x28**；其余正式轮的最终 SIGSEGV 线程/调用链不能凭临近日志推出。work_thread SIGABRT 是单独签名，日志之后还在运行，不能和父进程的最终 signal 11 当作同一事件。正式轮 cppcrash 查找为空，收尾又重查一次仍为空；空间 34%、余 155G。没有擅自修改系统 faultlogger 配置，也不能猜测是容量或配额造成缺报告。

**预跑补充，不混入正式分母**：speed-1/2 的系统 cppcrash 均为 PatchUpdateMana，SIGSEGV@0，`toutiao.odex+0x6f0d7c0 → libshadowhook → libc_gwp_asan_calloc → __libc_malloc_impl+1332`，寿命 **105s/88s**，都在条目前。该签名两次重复 verified，但不足以证明 speed 独有或 AOT 引入。预跑 verify-1 的迟到系统报告已补取：**RenderThread，libwebviewchromium.so+0x26016f0，SIGSEGV@0，寿命219s**。这些是不同故障，不互相替代。

## 无效轮与证据边界

- baseline-1 条目时仍有第二个同意弹窗；34571ms 是同意 DOWN，不是条目。verify-1 条目距同意106.48s；baseline-2 点击也偏晚。这些不参与固定时点对比。
- formal-baseline-a 在人工确认90s期限到后由夹具停止；formal-baseline-a2 受旧的全局150s准备期限影响，且手工收起过残留键盘。这两次是夹具问题，不计应用崩溃。已改为每轮重启自己 HAP、同意后单独计时。
- formal-verify-r2 在截图确认期限到后由夹具停止，没有条目输入；不计应用最终退出，也不混入性能样本。重跑为 r2b，后者真实 SIGSEGV。
- 自动 result.outcome 中 `detail_lifecycle_seen` 只代表 ENTRY；预跑 verify-1 的 `not_measured` 是末尾旧版 view-tree 拉取超时所致，不能据这个字段否认已记录的输入/ENTRY。

## 复核与移交

VM 原件：`~/a2hlab/board/5cd1e3dd00000000000000000923012c/aot42/`。提交中 `device-evidence/` 是原件的无损副本，大文本用 gzip；`device-evidence-manifest.json` 同时列原字节和压缩文件 SHA256。三份含 APK/native 的 launch-inputs.tar 仅留 VM，哈希见 payload-references.json，不把分发包提交 Git。每份 child.stderr 在清场后重新拉回并与板上 sha256sum 核对，迟到 faultlog 也重查。父日志每轮启动时覆盖，所以保留各轮清场前拷贝，不以最后一轮日志覆盖先前证据。

工具：scripts/stage42.py 建隔离 stage；run42.py 单轮物理输入/清场；checkshot42.py 取图；refresh42.py 收尾复取；analyze_device.py 按行提取；verify_device.py 从归档重算并核对。stage/restart 依赖既有 #38/#42 原始部署目录，完整命令与哈希已留档；不是独立于西湖构建产物的一键安装包。

离线复核通过：906 份设备证据哈希，17 轮记录从原始日志重算一致；正式 3/3/3 次尝试、3/0/2 次点击、9 次 signal 11。VM 原有 18 份证据哈希与元数据检查亦通过。已知答案测试 69 项通过、2 skipped。无 runtime 改动，不重编整链。板最终进程检查留 final-processes.txt，无自己的头条/appspawn，也无 dalvikvm/linker64。只 commit、不 push。

建议保留同源 AOT 产物作为后续对照，不默认切 speed。先结合 #38 CPU 画像与详情/WebView 崩溃修复再测；需要每臂三份有效点击、精确画面呈现时间及可分类崩溃报告，才能解除本次性能验收阻塞。
