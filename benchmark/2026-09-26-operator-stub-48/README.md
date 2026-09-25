# #48 metasec 空壳五轮实验

用户指定harness `8fa3d5c`，独立worktree/分支`test/metasec-stub-48`，仅61b06572。空壳从交付源码单库重建，SHA `6e6b9aaad14c6b8e5762c062a3689f96e4c74b8b84b32665cb42b2b9a661a9a9`；真库SHA `c91fc2ee0f47c87da4723fd59eb8420ed616b409076310f28f3420771a1fab6b`。原件按SHA备份后覆盖runtime/lib/arm64-v8a/libmetasec_ml.so。上游断言空壳PASS、真库FAIL；该检查只证明指定native接口/链接形态，不保证Java包装层或服务端接受空结果。

保留完整闭包core `c9969638…`、A1 ART、shim85c789f4、mc46 bridge、npth8b8d559c、tt targets/LD_PRELOAD及map_count1048576。各轮七组件SHA前后核验，独立清空profile；真实uinput输入，原PID/birth绑定，守护替代实例不计存活。

五轮要求：信息流可见，真实uinput进入详情、正文可读，原实例详情RESUMED后至少180s；无metasec相关SIGSEGV、无main exit(1)。另检查信息流刷新、文章及登录页面（不提交登录凭据）；无法执行或发现异常均单列，不把未见崩溃等同无副作用。即使5/5通过也仅证明这些测试窗口，不证明无限期可靠。

测试进行中。
