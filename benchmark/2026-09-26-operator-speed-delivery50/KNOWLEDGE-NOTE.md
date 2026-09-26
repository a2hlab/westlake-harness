## #50 现场提速与恢复计时边界（codex-2，2026-09-27）

- 当前clamp boot的BCP checksum已变成`i;9/2ab43e21`，旧AOT包不能仅凭oat247硬套。冻结现场39文件、用同源host只重编app AOT后，真实child加载app image/odex；JIT目录在parent挂载命名空间预建20010053:20010053:0700，日志和同inode RW/RX deleted-file maps才是命中证据。两次同文NewDetail0.840/0.830s、正文2.44–5.25s；基线三次14.259–24.616s，不能以这些成功样本掩盖speed-r3 SkiaCanvas析构SIG11与r6旧mallocngSIG11。
- 守护`recovery_s`若每次失败都重置，只量到最后一次启动；人工SIGSEGV到READY实际84.94s，而最后日志写49s，必须从原始触发uptime算完整中断。SIGKILL另次22.44s恢复，不能把它推广为每次30s内。RESUMED与正文可见仍分开取证；guardian-on恢复功能样本不混入guardian-off A/B统计。
