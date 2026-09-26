
## D补：#48 hollow引擎的动态边界（codex-2）

- `test/hollow-engines-warm-48`：仅将bytehook/shadowhook换成fbb761a0/34378f5c，hollow+clamp其余基线不变，禁守护warm五轮。3轮完成360s观察并真实uinput打开ArticleInflow与NewDetail（正文/图）；另两轮约17.91s/17.54s发生SIG11：r1 ChromiumNet0在sscronet ELF0x28a21c读空虚表+0x28；r5 platform-handle在musl **sigaction+0x184/ELF0x111954**向输出对象+96写入时ACCERR。未观察到mallocng故障不等于5/5或永久堆安全；旧0x111974未命中也**不能宣称sigaction类全清**。两次完整maps+寄存器有、栈EACCES，不能据故障点直接认定承重钩/唯一非钩写源。r3短讯正文可读但评论网络异常，需单列功能限制。
- 实际加载身份应连接“每轮源文件SHA→maps inode/路径→进程/proc/pid/root命名空间SHA→结束复核”。本轮r2/r3/r4完整活体链、早崩r1/r5源SHA+故障maps+结束SHA均确认patched引擎。静态入口patch和加载成功仍不等于所有运行路径已安全；失败轮保留、不删掉重凑5/5。
