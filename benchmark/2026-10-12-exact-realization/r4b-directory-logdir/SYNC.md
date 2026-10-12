# R4b ACK

原r4纯只读首probe因未建transport目录失败；仅加logs.mkdir(parents=True,exist_ok=False)，其余executor字节相等。真实CLI+原Transport+本地假HDC验证raw落盘，预设remote42导致rc1，无intent/目标写入/重启。原16矩阵和487不重跑。新manifest/executor/auth pins，wrapper显式recipe路由转r4b；原r4其余文件不改。请outer用fresh output+新独立授权执行单目录，旧失败证据保留。结果不代表自恢复或封板通过。

Land测试入口修订：无参使用TemporaryDirectory/fresh子目录，实际无参运行rc0；显式out原行为不变。65d3 executor、839f manifest、原CLI proof未改。旧freeze记录保存在freeze.before-noarg-fix.json。
