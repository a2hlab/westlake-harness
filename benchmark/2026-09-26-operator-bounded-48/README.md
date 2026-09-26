# #48 无守护、限时三轮隔离

按外环最新指令重跑。之前带守护数据不并入本组三轮：外环清掉7个头条进程、停止守护、终止挂起的isolated48驱动；资源污染使原组不能作为干净对照。

仅61b06572。test/metasec-bounded-48，基于a1197ba；BASELINE+1021a058桩+78e34445被动记录器，runffb324e4（unset JIT_FILE_CACHE_DIR）。无AOT，无自动重启，无新重编。

每轮前要求pidof头条和appspawn-x均为空，MemAvailable>1GiB，记录free -m和全部7组件SHA。归档三组profile并新启动parent/child。spawn后核记录器目录fd。只启动一个child，不更新/启动operator守护，stop标记全程保留。

按最新“测≤180s”指令，每轮正常观测约173s，随后先kill -9实例、parent和同板残留头条/appspawn，再确认两类PID均空、MemAvailable>1GiB，最后取证。另有只终止、绝不重启的单次板上178s期限计时器，按PID/birth匹配，防VM驱动失联；它不是自动重启守护。此组**不声称详情RESUMED后又存活180s**，避免把最新限时口径混成旧验收。

Mac真实HDC使用独立进程组，最长55s后SIGKILL；VM代理最长59s后SIGKILL进程组。操作超时记该轮失败，finally先清理，再最多各15-20s下载原始日志/快照。不让下载延长活实例窗口。不回收服务端共享HDC，不碰其他板。

第一次single-r1在Mac代理参数映射处exec format error、未接触板/未spawn，保留为夹具准备失败。改为mac bash传递Python源码和base64参数，正式bounded-r1..3。

## 人工点击时序准备轮与自动正式轮

bounded-r1..3均按173s清场，无守护、无超时，但人工读图/发指令使条目点击发生在启动后116.18/103.70/139.74s，短窗不足，不将它们当作正文性能或3轮正式验收。原始失败/截图全部保留。

正式auto-r1..3由驱动每10s检查真实截图中的固定同意框（1200×1920、红按钮/白面板/蓝盾多点交集），匹配后才执行已授权的真实uinput同意和条目点击。判据在3张已人工确认同意框及5张宿主/信息流负例上通过；它仅适配当前固定板UI，不是通用识别器。每次匹配截图与点击uptime留档，最终正文仍由人工读截图。使用独立VM venv-bounded48，Pillow12.3.0，不改其他环境。仍无守护、173s窗口、178s一次性清理兜底、先清场后下载。
