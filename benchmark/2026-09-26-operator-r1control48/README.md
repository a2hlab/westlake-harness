# #48 原始 sscronet 单变量 warm 对照

目的：判断带 R1GUARD48 的合并配方为何feed空白。带守卫4轮各360s但0feed/正文，完整结果在相邻 [merged48](../2026-09-26-operator-merged48/README.md)，commit90f860f。

本对照仅恢复 `libsscronet.so` 到原始 SHA256 `38f0dd424fabd2b92a08e0a6eb372bc464dd424b370aba23c88e39ba6374866f`；保留 monitorcollector R5NEUTER48 `8c97ef7cd666517e92c0a79a9471518afff0133a891f775d5291a557cdbacf31`，其余 hollow引擎、npth、clamp jar/boot、memsponge/sysopt、metasec、shim与合并配方全同。恢复前备份守卫版到 `/data/local/tmp/operator45-crashes/r1control48-original/libsscronet.R1GUARD48.so`。板上原库取自已核SHA的 merged48-original；部署前后全组件比较仅sscronet不同。

Board `61b0657200000000000000000324012c`，同一独立worktree/分支。保留同意、禁守护，每轮单一原进程，360s有界观察；退出或到时清理child和appspawn后检查空PID与内存。真实uinput，不i/c注入、不清数据、不加速度层。各轮maps+进程命名空间SHA/inode；parent/child/recorder合并判断崩溃。VM根 `~/a2hlab/board/61b0657200000000000000000324012c/r1control48`。

本轮承重是实际feed标题与NewDetail/ArticleInflow正文；进程存活单独列。原sscronet的已知偶发空虚表崩溃风险未解决。恢复正文也不自动等于可靠交付。

所有证据在 `evidence/`；`verify.py` 核原始+归档SHA，`--git`核HEAD对象。`scripts/deploy_control.py` 为一次性部署记录；勿对运行实例重跑。

## 最终：ACK(blocked)，R2=partially

| 对照轮次 | child PID | 观察存活(s) | 真feed | NewDetail正文 | ArticleInflow | 退出/崩溃 |
|---|---:|---:|---|---|---|---|
| control-r1 | 13082 | 360.112 | 有标题及真实封面 | 标题+段落+配图 | 未验证 | 原PID终检存活，按计划结束 |
| control-r2 | 21009 | 17.419 | 未到达 | 无 | 未到达 | platform-io-thr SIG11，musl ELF0xd6e20 |
| control-r3 | 22516 | 17.476 | 未到达 | 无 | 未到达 | ChromiumNet0 SIG11，musl ELF0xd6e20 |

带守卫4轮0/4真feed；只回原sscronet后首轮feed和NewDetail正文恢复，证明其他补丁组合仍存在可读路径，并为R1GUARD破坏feed提供单变量动态证据。尚未定位被省略调用的具体网络职责，不能从一轮恢复排除全部时间/服务端因素，更不宣称原库稳定。后两轮早崩，不能归为“feed空白”。原sscronet0x28a21c本次未复发，但mallocng有两次明确反例；r5 sigaction本次0。

截图：[无遮挡真feed](evidence/control-r1/feed-gate.jpeg)、[NewDetail正文](evidence/control-r1/article1-body.jpeg)、[返回feed并滚动](evidence/control-r1/feed-scroll.jpeg)。真实uinput(380,380)点击；NewDetail ENTRY recordId2 + RESUMED uptime147223693，点击uptime147208220，差15.473s。正文截图晚于RESUMED，不能将该差值写成正文出现的精确延迟。没有ArticleInflow截图，未满足3篇文章指标。

两次故障PC均musl ELF0xd6e20、LR0xd6a18、fault=0；r2 event-5211-52bf-1（进程birth后16.752s），r3 event-57f4-58c2-1（16.951s）。寄存器/maps齐，mem_open EACCES无完整回溯，不能据线程名定唯一破坏源。各库身份核验详见verdict：首轮有活体命名空间SHA，两早崩轮使用preflight SHA+完整故障maps inode+结束源SHA/inode复核。r1/r2八库映射，r3的sysopt尚未映射，其余七库可见，所以三轮“全部映射”总断言为false，不能用ULE=0替代尚未到达的加载成功。

ULE/exit1/Layout -79均0；r1有work_thread SIGABRT横幅后继续存活，不说全信号0。结束时app/appspawn PID均空，守护两stop且无lock，map_count1048576，同意数据保留。现场最终保留原sscronet38f0dd42+r5neuter8c97ef7c及其余hollow/clamp/引擎配置，未擅自切回守卫版。

交claude-3重审R1被无条件NOP的网络调用，做保留正常路径的修复；同时判读两次mallocng故障。现有证据不能认“堆崩永久闭合”。
