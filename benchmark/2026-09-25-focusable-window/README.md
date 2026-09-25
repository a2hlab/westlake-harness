# #34 首版：可焦点窗口与真实 InputChannel

状态 **ACK(blocked), R2=partially**。按 operator 进度要求先交代码和可部署产物；
真实通道已通，尚不能签头条物理点条目 <2s。仅板 `5ea34a4500000000000000001123012c`，
未写系统分区、未 push。源码 commit **237f1e5adca66596668929d461d7c6d28900e21b**，
VM worktree `~/a2hlab/ws/westlake-focus34`，分支 `feat/focusable-window-34`。

## 已交付

默认可焦点，create/show/首帧前台请求焦点；SceneBoard 使用普通客户端
RequestFocusStatus（成功），不使用系统专属 ISession::RequestFocus（返回8）。
MMI GetAgentWindowId → 真 AOSP 14 InputPublisher → 真 InputChannel，未自行命中。
保留 I5 downTime、I6 source、I9 指针 ID 压缩；接收端完整多指、正确 axis 编码。
私有 transport DSO 隔离 canonical Input.h 与旧 runtime C++ ABI；来源/hash 在源仓库。
WL_INPUT_LEGACY=1 反射回退，WL_FOCUSABLE=0 关闭焦点，i/c 自动化保留。
修正 SceneBoard Show/Hide/DestroySpecific，旧 legacy WMS 调用曾留下 MMI 幽灵窗口。

## 可部署版本

- 必须继续用 #14/out-touch21-wake framework + out-sp20 WebView（#17/#20，不含 #16/#23）。
- sscronet native/net 双参数，沿用 #30 19项 native targets；未混入 out-all0925。
- stage `/data/local/tmp/a2hlab-framework-focus34-v5`；完整 framework 报告在 evidence/framework-candidate。
- transport SHA256 `e2ef146892bb805ff01257eced37fea8ea2c4ff229226bdeca8f6e3819c2cdf4`。
- bridge SHA256 `326ca440ae8781bc22bea6461db430571cf3669a0612d497c43e1418ed74e0a0`。
- runtime SHA256 `f937885c87dac39141cf6d441557a63a7f9d182e3f36364f7c43126ab8c01dc1`。

VM `python3 ~/a2hlab/ws/westlake-focus34/tools/build_focus34.py` 增量重建；
`--test` 编译真实 socketpair 测试。所有 VM 命令用 `orb -m a2hlab bash -lc '<cmd>'`。
该脚本明确固定在已验底座；未声称已接入通用 all0925 构建。只重编依赖变化的 TU、
重链所属库，不变时全部 reuse；最后窗口生命周期变更只重编一个 TU + bridge。
新增 helper 需要与 bridge/runtime 三库一起部署。Ccache 链接未擅动。

## 第一批实测

|轮次|结果|证据|
|---|---|---|
|baseline-1|同底座信息流/真实图片；硬件点击未进详情，随后 i 注入出现 NewDetailActivity；文章后原有崩溃|frame-080.jpeg、actions.jsonl、child.stderr.gz、cppcrash|
|noice-candidate-3 (v4)|关闭 touchfwd 后 uinput，Welcome → Design your ideal environment|frame-072/108.jpeg，MMI/publish/receive|
|wiki-candidate-1 (v4)|关闭 touchfwd 后 uinput → Data & Privacy|frame-073/107.jpeg，MMI/publish/receive|
|toutiao-candidate-2 (v4)|真实信息流图片；popup320 的 Android channel 删除后仍被 MMI 命中，unknown target 被正确拒绝；tab/scroll 未通过|frame-096.jpeg、manual-actions.jsonl、child.stderr.gz|
|toutiao-candidate-3 (v5)|真实信息流图片；SceneBoard Hide/DestroySpecific rc0；UI 因 null Looper→Handler NPE 退出，滚动样本无效|frame-076/086.jpeg、ui-exit-tail.txt.gz|
|toutiao-candidate-4 (v5)|真实信息流图片；uinput 380,297 DOWN/UP 实际命中弹窗328，publish/receive 成功，未进入 NewDetailActivity|frame-078/089.jpeg、actions.jsonl、child.stderr.gz L12791–12796|
|toutiao-candidate-5 (v5)|加早的两次 uinput 未进文章；第一张仍是宿主，不能作有效条目点击验收；后续才出现信息流，最终116s bd_tracker_w:13 / liboh_android_runtime SIGSEGV（另有 work_thread SIGABRT 日志）|frame-061/088/111.jpeg、actions.jsonl、cppcrash|

v4 Noice/Wikipedia 不冒充 v5 完整回归。v5 transport 测试上板 PASS，
涵盖零轴坐标、source/downTime、多指 action/ID、拒绝非法 ID/seq。标准 InputPublisher
的真实 socketpair 消息与 canonical InputMessage 核对；不替代端到端多指验收。

### 仍未通过

头条 <2s 进入文章、分类 tab 内容改变、滚动刷新；物理按键/vsync 未测。
焦点被宿主抢回或无 AMS 锚点留给 #38，不在首版中继续扩展。
#30 已知 WebView 详情 SIGSEGV 与 ICU/free 崩溃没有修复，没进文章不代表其消失。
最后一轮 SIGSEGV fault address 0x88、PC offset 0xa2044；未定位因果，不归作 ICU 或 WebView 同签名。
最终任务 appspawn-x/touchfwd/article.news 进程列表为空，所有 stage/日志保留。
第一轮 noice-candidate-1 请求了系统专属焦点接口且画面黑，排除；
noice-candidate-2 / toutiao-candidate-1 尚有 ability-owned 早返回，排除新通道验收。
v4 无效的复合 uinput 滑动参数及其补 UP 保留，不作滚动成功证据。

## 证据与复核

`evidence/manifest.json` 记录每份原文件路径、原始 bytes/SHA256、压缩后 bytes/SHA256。
大文本无损 gzip，截图原样；原 VM 日志和部署保留。`python3 verify.py` 核哈希与解压字节，
`python3 verify.py --git` 再核 HEAD blobs。原始运行目录是
`~/a2hlab/board/5ea34a4500000000000000001123012c/focus34/`。
脚本 scripts 用于同板复跑；restart 清理的是该轮专属应用数据，不动系统/其他板。
首版 ACK 已追加主看板，不覆盖旧记录。R2 只声明上述具体证据，不声明完整任务完成。
