# #48 metasec 空壳五轮实验

用户指定harness `8fa3d5c`，独立worktree/分支`test/metasec-stub-48`，仅61b06572。空壳从交付源码单库重建，SHA `6e6b9aaad14c6b8e5762c062a3689f96e4c74b8b84b32665cb42b2b9a661a9a9`；真库SHA `c91fc2ee0f47c87da4723fd59eb8420ed616b409076310f28f3420771a1fab6b`。原件按SHA备份后覆盖runtime/lib/arm64-v8a/libmetasec_ml.so。上游断言空壳PASS、真库FAIL；该检查只证明指定native接口/链接形态，不保证Java包装层或服务端接受空结果。

保留完整闭包core `c9969638…`、A1 ART、shim85c789f4、mc46 bridge、npth8b8d559c、tt targets/LD_PRELOAD及map_count1048576。各轮七组件SHA前后核验，独立清空profile；真实uinput输入，原PID/birth绑定，守护替代实例不计存活。

五轮要求：信息流可见，真实uinput进入详情、正文可读，原实例详情RESUMED后至少180s；无metasec相关SIGSEGV、无main exit(1)。另检查信息流刷新、文章及登录页面（不提交登录凭据）；无法执行或发现异常均单列，不把未见崩溃等同无副作用。即使5/5通过也仅证明这些测试窗口，不证明无限期可靠。

测试进行中。

首轮12880：最后采样活180.46s、185.05s检查已死；parent exited(1)。metasec引发platform-back-handler的Boolean.booleanValue null NPE（ms.bd.c.p2.d→MSManagerUtils.init），证明包装层并不普遍接受null；另点击进入ArticleInflowActivity后main抛Layout: -79 < 0。后者不能据时序直接归因于stub。feed/真实配图出现且推荐内容变化，未取得正文>180s或登录页，第一轮失败。继续相同候选余轮，保留失败不抵消。

第二轮19769：最后采样活178.37s、182.36s检查已死。再次Boolean.booleanValue null NPE，随后X.DEv null Looper使ActivityThread.main返回，parent exited(1)。NewDetailActivity曾RESUMED，但正文未取得180s窗口；两轮均不能交付。

## 用户叫停旧空壳，待细化版

07:59:10–07:59:13 CST按指令清理61b06572：停止守护26870，保留stop标记；结束第三轮原child26828及parent26789。清理前原实例仍活，第三轮未执行同意/条目输入，未完成验收。原始监测在人工kill后记录dead，该结果明确标作用户中止，汇总排除，不当自然崩溃或成功。只完成前两轮，两轮均失败；第4/5轮未启动。

清理后pidof头条无存活进程、绑定parent无存活、守护不存活；stage和原件备份/实验日志保留，当前库仍是旧空壳，未声称已部署细化版。停止方法已实际执行：touch /data/local/tmp/operator45/stop，再终止guard.pid对应守护。等待细化版交付，不继续旧空壳试验。
