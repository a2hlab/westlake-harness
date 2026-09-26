# #48 细化空壳，五轮新鲜启动

独立分支`test/metasec-refined-48`，继承JIT目录修正47f0576；仅operator板61b06572。使用claude-3交付`bfc09a1`二进制，SHA `1021a0582e360ceafb49aa1162ee5d024104a73504ba0801927aaaa8bf2e706f`。旧null桩`6e6b9aaa…`按SHA备份；更早真库c91fc2ee原备份保留。除metasec及已授权JIT目录0700外，BASELINE七组件固定，不安装AOT。

新源码重建得到2fc993a8…，与交付SHA不同，准备阶段在覆盖/spawn前被校验拦截。保留失败准备`refined-r1`，它无child、不计正式轮次。改用共享worktree中的交付二进制，精确SHA及更新的上游断言通过，记录provenance；未将重建称为字节复现。正式轮次safe-r1…safe-r5。

每轮重新备份并清空三组profile，重新parent，app namespace内预建JIT目录UID/GID20010053、0700、非软链。真实uinput，原PID/birth约束，守护恢复不算原实例存活。原始日志/异常/失败轮完整保留。

主验收为正文可读且原实例详情RESUMED后>180s，无metasec SIGSEGV、Boolean-null NPE或main exit(1)；另测刷新、登录页、点击布局。五轮有限窗口通过也不证明无限期可靠，更不能仅凭通过断言所有功能不需Bionic。主任务完成后才跑匿名/文件JIT A/B各3轮。

测试进行中。
