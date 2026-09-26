# #48 无守护、限时三轮隔离

按外环最新指令重跑。之前带守护数据不并入本组三轮：外环清掉7个头条进程、停止守护、终止挂起的isolated48驱动；资源污染使原组不能作为干净对照。

仅61b06572。test/metasec-bounded-48，基于a1197ba；BASELINE+1021a058桩+78e34445被动记录器，runffb324e4（unset JIT_FILE_CACHE_DIR）。无AOT，无自动重启，无新重编。

每轮前要求pidof头条和appspawn-x均为空，MemAvailable>1GiB，记录free -m和全部7组件SHA。归档三组profile并新启动parent/child。spawn后核记录器目录fd。只启动一个child，不更新/启动operator守护，stop标记全程保留。

按最新“测≤180s”指令，每轮正常观测约173s，随后先kill -9实例、parent和同板残留头条/appspawn，再确认两类PID均空、MemAvailable>1GiB，最后取证。另有只终止、绝不重启的单次板上178s期限计时器，按PID/birth匹配，防VM驱动失联；它不是自动重启守护。此组**不声称详情RESUMED后又存活180s**，避免把最新限时口径混成旧验收。

Mac真实HDC使用独立进程组，最长55s后SIGKILL；VM代理最长59s后SIGKILL进程组。操作超时记该轮失败，finally先清理，再最多各15-20s下载原始日志/快照。不让下载延长活实例窗口。不回收服务端共享HDC，不碰其他板。

第一次single-r1在Mac代理参数映射处exec format error、未接触板/未spawn，保留为夹具准备失败。改为mac bash传递Python源码和base64参数，正式bounded-r1..3。
