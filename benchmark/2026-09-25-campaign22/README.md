# campaign22:全修复合流后的 100 app 全量重扫(板 C,2026-09-25)

## 构建(git 验收①)
worktree `~/a2hlab/ws/westlake-campaign22`,分支 `integrate/campaign-22`,基于 `5f9a435`(integrate/toutiao-4fix,#8/#11/PM/#10),cherry-pick #16 全部 4 commit(`156488c` 报告、`88f541e`/`ff1d660`/`3e3af18` 代码,即原 `8b0c28c`/`3e1a865`/`f8e077b`/`d1ce0d2`)。构建 `out-campaign22`(native-runtime 全链,`BUILD_DONE`,`NATIVE_LINK_FAILED=0`,未碰共享 `out/` 与其他 out-*)。stage:`~/a2hlab/board/61b06572…/campaign22/framework` PRELOAD_PASS(framework/boot=out-integrate,resources/data=共享 out/,appspawn+native-runtime=out-campaign22)。WebView:`--source-webview-build out-sp20/webview-candidate`(SC no-op 表+single-process)+锁定 `--webview-input`(probe 要求对照)。#19 推导目标并入 corpus `extra_args`(90 app、2214 对旗标,toutiao 133 对含 libsscronet native+net)。

## 运行(验收②)
`runs/campaign22/`:SUMMARY 末行 `total 100: done=99, launch-failed=1`(fd-mpv,libharfbuzz_ng.so 推送失败=传输层瞬时,同 scan1 co-booking 字体签名)。存储:首轮曾把板写到 232G/232G 致 29 app `no space left on device`,runner 已补存储清尾(post 按报告定向删 stage+runtime;pre 扫 `a2hlab-app-*`/`a2hlab-source-*`;framework 目录结构性不匹配)后全量重扫,全程 3-8% 水位。每 app 启动前+收尾双清进程+存储。

## 对比 verify2(15/100 → 14/100;验收③④,点亮=四阶段全过)
- **新点亮(1)**:markor(SIGTRAP 崩溃消失)。
- **回退(2,逐一说明)**:fd-app(SIGABRT native 崩溃,本轮 faultlog 在案,属间歇崩溃族非本合流引入)、fd-libre(P3 掉:本轮日志含显式 `Unable to start activity ComponentInfo`,是 P3 判据的正判非误判;已加回归钉子测试 `063ff5a`)。另 P3 掉 3 个(fd-fluffychat/fd-kitchenowl/localsend,同显式 activity 失败正判)+fd-mpv P2 掉(launch-failed 传输层,非代码)。
- **阶段推进(8,非点亮)**:anki/co-duolingo/fd-tasks +P2;co-shopping/fd-tutanota +P3(fd-tutanota 另 +P4b);anki 另有首阻塞更替。
- **首阻塞变化(39 app)**:#16 的 12 方法旧阻塞全部消失(antennapod/co-AlipayGphone/co-pinterest/co-cash/co-mm/co-mediaclient*/co-p2pmobile*/co-client/co-discord*/fd-api/fd-binaryeye/fd-feeder*/fd-im-vector-app*/fd-meet*/fd-tasks*/termux 等,*=前进到下一层);新浮现下一层族:`AAssetManager_fromJava`(burgerking/co-candycrushsaga/co-discord)、`__system_property_read`、EGL `eglGetDisplay`、app 层 RuntimeException/ClassNotFoundException。mcdonalds 出现 `ProcessEnvironment.environ`(归因待查,首阻塞从 None 变化,阶段未回退)。

## 板上写
仅板 C(授权独占);runner 三处增强见 feat/board-loop `1c606d1`/`0569d44`/`53c27c3`/`063ff5a`,只 commit 未 push。
