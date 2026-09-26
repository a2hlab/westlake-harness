# #48 R1GUARD48 + R5NEUTER48 合并 warm 板测

Board `61b0657200000000000000000324012c`，独立分支 `test/merged-stability-48`。禁守护、保留同意、每轮单实例；本次未清数据、未加速度 AOT/JIT。结果以末尾统计及 `evidence/verdict.json` 为准。

## 配方与部署

在 hollow+clamp+引擎基线上只换两库，部署前逐件备份并拉回核 SHA：

| 文件 | 本轮 SHA256 |
|---|---|
| libmonitorcollector-lib.so | `8c97ef7cd666517e92c0a79a9471518afff0133a891f775d5291a557cdbacf31` |
| libsscronet.so | `5ba487778a6a3be4a633b7ba5e90e0ff4e1bb6693d28c970f0e8025eb88fdb79` |

实际 app runtime：`/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`，app 命名空间内为 `/data/local/tmp/asx`。替换其 `lib/arm64-v8a/` 下文件。原件备份 `/data/local/tmp/operator45-crashes/merged48-original/`；原 monitorcollector f3918bdc，原 sscronet 38f0dd42，完整 SHA 在 deployment 证据。

保留 shim85c789f4、npth9966e296、memsponge2f066332、sysoptc92d0ea5、metasec1021a058、bytehookfbb761a0、shadowhook34378f5c、clamp adapter ea5d8b27+匹配 oat247 boot、bridge d4fae8e5、TT targets/LD_PRELOAD、map_count1048576。run.sh ffb324e4，文件 JIT 缓存未启用。

R1 patch 是三条虚调用指令**无条件 NOP**，并非条件判空分支；R5 是两处可达 sigaction 调用假返回成功。源脚本/解释见同仓相邻 operator-r1guard-48、operator-r5neuter-48。不把静态断言当运行成功。

## 方法

- 每轮 `warm48.py merged-rN confirm-warm`；每轮前后确认头条/appspawn PID 空与可用内存>1GiB，原 PID/birth 终态核验，计划360s结束；无自动重启/替补轮。
- HDC host hard deadline <=55s；收集前先清实例，单次异常不会无限等。板上368s单次兜底只杀该PID/birth，不重启。
- 真实触摸为 `uinput -T -d x y -u x y`；滑动为 `uinput -T -m ...`。`inputs.jsonl` 保存 uptime。只对截图中可见文章作文章点击判定；空白区域点击不能冒充读文章。
- 周期截图与 maps20/60/190/330；活体 `/proc/pid/root/...` 核8库SHA及inode，对照maps。无ULE仅代表本轮未见加载错误，不代表全部native逐一调用。
- 判崩同时读 child.stderr、parent退出、CRASH42记录器，分类 musl mallocng、sscronet0x28a21c、musl sigaction 区域和其他SIG11；不只数旧偏移子串。
- 正文需人工视图审阅 + 行首 B47-SLA ENTRY / ABILITY38-RESUMED 生命周期；服务端JSON不算。未到文章时，存活观察不覆盖文章压力路径。

## 可重放证据

VM 原证据 `~/a2hlab/board/61b0657200000000000000000324012c/merged48`；共享压缩归档在 `evidence/`，manifest同时记录原始及归档SHA。`python3 verify.py` 核两层哈希；提交后加 `--git` 核HEAD对象。`out/` 为本轮确切候选二进制。

R1首次静态检查ELF项FAIL、三NOP及epilogue项PASS；直接readelf确认AArch64、同SHA重跑全部PASS。初次失败输出保留，不给未证实根因。R5静态全PASS。

## 最终结果：ACK(blocked)，R2=partially

按外环新派 sscronet 原库对照，带守卫第5轮未开始即取消。已完成4轮全部保留，不凑5/5。

| 轮次 | child PID | 原PID终检存活(s) | SIG11 / exit1 / ULE | 真feed / 正文 |
|---|---:|---:|---|---|
| merged-r1 | 12807 | 360.174 | 0 / 0 / 0 | 未见 / 0 |
| merged-r2 | 20441 | 360.126 | 0 / 0 / 0 | 未见 / 0 |
| merged-r3 | 27987 | 360.131 | 0 / 0 / 0 | 未见 / 0 |
| merged-r4 | 4146 | 360.121 | 0 / 0 / 0 | 未见 / 0 |
| r5 | — | 未运行 | 不计 | 按改派转对照 |

四轮均未见 mallocng / sscronet0x28a21c / sigaction SIG11，也没有其他SIG11，但**没有到文章路径，不能宣称文章压力下三类崩溃根治**。四轮都有work_thread SIGABRT横幅，之后原进程继续到360s；不报告所有信号0。Layout -79/exit1/ULE均0，clamp guard共24次。八库实际maps+命名空间SHA+inode证据齐；静态native覆盖不等于所有native动态调用。

推荐页空白，r1/r3深圳分类明确网络异常；r2热榜空白，r4“我的”进登录页、关闭回空白首页。没有NewDetail/ArticleInflow行首生命周期，没有文章截图。截图：[r1网络异常](evidence/merged-r1/tab-probe.jpeg)、[r2推荐空白](evidence/merged-r2/refresh-probe.jpeg)、[r3重试仍失败](evidence/merged-r3/retry-result.jpeg)、[r4登录关闭后](evidence/merged-r4/mine-dismissed.jpeg)。

板IP/域名ping通、app UID有已建立443连接，系统epoch与host一致；不能据此证明feed API正常，更不能直接归因守卫。按外环指令单变量恢复38f0dd42后转相邻 `operator-r1control48` 对照；合并阶段final-check记录是在恢复前获取，不代表对照结束后的板态。
