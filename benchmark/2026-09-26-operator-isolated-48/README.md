# #48 细化空壳隔离测试

用户要求撤掉#50文件JIT，仅稳定基线+细化桩1021a058，并以crash42被动记录器取得SIG11原生现场。独立test/metasec-isolated-48；仅61b06572；只commit不push。

run.sh去掉FILE_CACHE_DIR并显式unset，保留原ANON_FALLBACK=1及JIT_BASELINE；新增WESTLAKE_CRASH42_DIR。守护禁用JIT目录准备钩子，不重启测试期间存活的原实例。目录0700这一权限本身不触发文件后端，实际后端仍须日志/maps验证。记录器目录独立private-tmp/crash42，UID20010053、0700、appdat。

当前A1 ART ae2cb182先逐字节重链复现，核454对象；复用out-crash42/recorder已有sigchain.o及crash_snapshot.o，只重链出cdd3e268，不全链编译，不撤A1。保留core libandroid c9969638、shim85c789f4、mc46、npth8b8d559c、四tt targets及LD_PRELOAD、map_count1048576。新run ffb324e4。原ART和run均按完整SHA备份到operator45-crashes/isolated48-original。

记录器仅在ART special callback全部拒绝后保存siginfo/ucontext/maps/SP栈/有界FP链，继续原OH链，不改signal handler语义。数据是原始快照/FP链，不自动等同完整DWARF栈；若self/mem被拒或信号未经过该链，须如实记录。记录器开销不用于性能结论。

每轮新三组profile、新parent、原PID/birth生存监测；真实uinput同意及点文章，要求详情RESUMED+正文截图且存活>180s。原实例退出即失败，守护替代不续时。完成三轮或失败有原生证据后落ACK，#50 A/B延期。

首准备iso-r1在spawn前被旧缓存的expected SHA拒绝（实际是正确新ART/run）；未运行应用、不计轮次。清掉本分支Python字节码缓存并用-B重跑，正式命名diag-r1..3；保留原失败证据。
