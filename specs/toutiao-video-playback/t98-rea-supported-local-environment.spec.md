spec: task
name: "T98 REA supported local compiler and writable cache"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t97-runtime-clock-cli]
---
## 意图
T97D已在安装源码核明REA支持显式编译器/SDK/缓存选项。本次仅修正已授权离线分析的子进程构建环境，让编译器缓存写入内环已有可写工作区，保留沙箱及所有审批策略，不写原拒绝目录或改变权限。
## 已定决策
- Codex唯一执行者，只在其工作树benchmark/2026-10-23-rea-local-environment/.private/创建缓存/tmp/日志/snapshot。原T96/T97失败原件不覆盖，不调用被拒MCP会话查询，不接续T91。用户此前明确授权REA操作用于本移植任务；本次无新设备/网络/安装或全局配置修改。
- 子进程显式环境：REA_DARWIN_SWIFTC_PATH=/Applications/Xcode-26.4.0-Release.Candidate.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc；SDKROOT为同bundle的Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk；REA_DARWIN_MODULE_CACHE_PATH为上述自有工作目录的module-cache；TMPDIR为其中tmp。变量由T97D安装源码ProcessOwnershipObservation.js157–175及DarwinProcessRunTokenReader.js294–327确认，不修改该源码，不删除或放松ownership检查。
- 使用现有/opt/homebrew/opt/ghidra/libexec和/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home作为GHIDRA_INSTALL_DIR/JAVA_HOME。只运行一次公共REA search目标TOUCH21，目标仍是8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1的本地liboh_android_runtime.so。不得改HOME或CODEX_HOME，不切换执行者/沙箱/权限档，不sudo。
- 如新环境实际成功，后继仅从真实返回引用查询计时函数，保存Evidence、函数地址及原始构建/provider执行日志；不执行目标、不诊断内存/故障、不修改二进制。若宿主拒绝、编译或provider失败立即停止，不再改参数重试。5分钟首交；真实长任务只报句柄，不按观察超时重启。
## 边界
### 允许修改
- benchmark/2026-10-23-rea-local-environment/**
### 禁止
- 原HOME缓存目录、全局配置、权限/审批/沙箱设置、REA实现与安全检查、设备和目标二进制
## 验收标准
场景: 受支持环境下搜索成功
  审核: human
  测试: rea_local_environment_review
  假设现有编译器SDK和工作区目录满足只读及写入权限
  当用已记录环境执行一次离线目标搜索
  那么原始回执证明工具实际完成，输入目标SHA不变，后继结论只绑定实际证据
场景: 编译或权限失败
  审核: human
  测试: rea_local_environment_review
  假设新尝试返回拒绝或失败
  当采集到完整原始输出或到达首交期限
  那么停止并保留失败，不再调整入口/权限或声称搜索完成
## 排除范围
全局环境修复、用户权限修改、白屏修复部署、冷启动签认。
