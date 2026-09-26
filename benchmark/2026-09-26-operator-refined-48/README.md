# #48 细化空壳，五轮新鲜启动

独立分支`test/metasec-refined-48`，继承JIT目录修正47f0576；仅operator板61b06572。使用claude-3交付`bfc09a1`二进制，SHA `1021a0582e360ceafb49aa1162ee5d024104a73504ba0801927aaaa8bf2e706f`。旧null桩`6e6b9aaa…`按SHA备份；更早真库c91fc2ee原备份保留。除metasec及已授权JIT目录0700外，BASELINE七组件固定，不安装AOT。

新源码重建得到2fc993a8…，与交付SHA不同，准备阶段在覆盖/spawn前被校验拦截。保留失败准备`refined-r1`，它无child、不计正式轮次。改用共享worktree中的交付二进制，精确SHA及更新的上游断言通过，记录provenance；未将重建称为字节复现。正式轮次safe-r1…safe-r5。

每轮重新备份并清空三组profile，重新parent，app namespace内预建JIT目录UID/GID20010053、0700、非软链。真实uinput，原PID/birth约束，守护恢复不算原实例存活。原始日志/异常/失败轮完整保留。

主验收为正文可读且原实例详情RESUMED后>180s，无metasec SIGSEGV、Boolean-null NPE或main exit(1)；另测刷新、登录页、点击布局。五轮有限窗口通过也不证明无限期可靠，更不能仅凭通过断言所有功能不需Bionic。主任务完成后才跑匿名/文件JIT A/B各3轮。

测试进行中。

首轮safe-r1/25973：最后采样活101.35s、104.79s检查已死，parent killed by signal 11。无Boolean-null NPE、无main exit(1)；NewDetailActivity有ENTRY未见完成RESUMED/正文。faultlog初次及延后均未取得，SIG11归属未知，不宣称metasec已消除。JIT日志选择文件后端；首轮maps被HDC直接读取procfs截断到4011字节，先前据此推断“缺rw-s”无效（已更正）。第三轮改为板上cat到普通文件后取回，4717行含末尾stack；同inode300645具r--s/r-xs/rw-s、无rwx文件映射，实际双视图成立。

第二/三轮4522/11320亦signal11退出，最后活/检查死分别118.09/121.65s、139.13/142.69s。第三轮实际输入为同意后点未登录tab，未取得登录页；无Boolean-null NPE或main exit(1)，SIG11缺原生栈，归属未知。不能从“未见metasec栈”写成metasec崩溃0。第四轮继续。

用户新指令中止混合配置：safe-r4于uptime110953前后主动停止，user-stop.json单列，不算自然崩溃/正式通过；safe-r5未启动。r4同意前等待约265s，uinput第二条110818.36，详情RESUMED110824.240（5.88s），截图只见文章框架，正文持续空白。该时序不与前三轮同等比较。后续改到独立test/metasec-isolated-48做匿名JIT+被动记录器三轮，#50 A/B延后。
