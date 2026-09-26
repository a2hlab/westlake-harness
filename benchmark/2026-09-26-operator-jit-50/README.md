# #50 JIT 私有文件缓存启用

独立分支`fix/jit-file-cache-50`；仅61b06572，无重编/系统分区修改。现场core ART仍为A1 `ae2cb182…`。来源westlake `docs/parity/OH-ANDROID-PARITY-2026-09-05.md` 和ART `jit_memory_region.cc:126`：打开绝对路径、O_NOFOLLOW，UID需等于app，mode不能给group/other任何权限；之后仍需通过O_TMPFILE与RX映射探测，失败继续匿名fallback。

**已确认**：现场art-volatile原先已存在、UID/GID20010053，但mode0755。不是“从未创建”，而是前置权限检查不满足。启动脚本原本就设了文件缓存目录及匿名fallback。

`prepare_jit50.sh`在父进程app挂载命名空间内mkdir、chown、chmod0700，拒绝软链并读回确认。守护在max_map_count恢复、父进程ready后、spawn前调用，失败不spawn。原operator配方的守护安装、warm/morning启动也接入同一钩子；后续新runner应在父进程ready后调用它。仅给当前文件补权限不会改变已经建立的匿名JIT映射，因此需要新child。

现场hook及守护已安装，独立父进程执行钩子通过：20010053:20010053:700、nonsymlink；SELinux标签保持appdat。第一次独立stat命令缺nsenter的`--`分隔符被工具拒绝，原始失败保留，修正后通过。测试父进程停止，头条/守护保持停用，未启动已叫停的旧null空壳。

## A/B 接续（尚未执行）

细化metasec空壳尚未交付；用户已禁止继续旧null版。当前“目录/钩子部署verified”，实际JIT后端选择和提速unverified，不引用历史p90 -61.6%作为本次结果。

同一细化空壳、同一native/ART/framework、同一profile起点，按匿名/文件交错各3轮。两臂目录均由钩子保持0700；仅匿名臂将run.sh中的WESTLAKE_OH_JIT_FILE_CACHE_DIR设为空，文件臂恢复原值；每轮重启父进程，核对子进程环境和实际maps。不要用改变JIT阈值或关闭JIT代替匿名对照。试验后恢复原run.sh文件缓存值并核SHA。

逐轮记录原PID/birth、真实uinput前/proc uptime、详情Activity完整ENTRY和匹配RESUMED、正文截图、异常/退出；不以settings JSON子串计数、不以守护替代PID续时。每臂3个有效点击的同时保留失败/删失轮。首跑同意后主线程空闲再点击同一文章，避免把SDK首跑差异混入JIT效果。报告各样本及中位数；n=3不作稳定p90推断。#48可靠性仍需独立判断正文>180s及副作用。

文件臂必须有实际后端日志、无anonymous cache with RWX、同一deleted inode的共享RW/RX映射且无RWX文件页，实际JIT编译成功；身份/能力另列。仅chmod或环境变量不能算生效。现有上游verify_jit_file_cache.py会因任意Fatal signal横幅而拒绝，已知work_thread横幅应原样保留并分列，不篡改日志使断言通过。
