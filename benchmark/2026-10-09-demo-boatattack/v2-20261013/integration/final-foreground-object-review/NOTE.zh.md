# 最小修正：前台焦点对象是目标UID进程集，host参数仍绑定imehost

**确认补充卡的 `{current_host_pid}` 对象选错，不是当前头条feed违反原R5。** 原 `bms_batch.py:376–382` 只判断焦点PID属于传入集合；真实调用 `:767–772` 从当前ps取目标UID全部进程。当前原始ps同UID20011206集合为4583与6789，原函数本地重放：host-only=false，UID集合=true（焦点6789/WID30）。没有修改原函数或重跑设备。

原 `observations.py:132–142,199–210` 要求唯一imehost0可见（ZOrd≥0）、host实际UID/GID、PID/birth/NUL cmdline及宿主WID一致；没有“Focus必须hostPID”条件。`seal_checks.py:168–183` 保留system_params、包版本和inventory门，没有新增host独占Focus门。原f28 checker调用不变R5 comparison。

更强反证：同boot086d的 `final61b-ui-closeout/final-selfcheck954.json` 为真实live954 PASS，其已pin原WMS同样是 **imehost4583/WID33/ZOrd101可见，头条6789/WID30/ZOrd102获Focus30**。因此原954早已接受此状态，不能把补充卡新增单PID假设当既有签认门。

最小正确接法：保留原host参数读取/可见性门；用当前同boot原ps/status/BMS身份绑定的目标UID20011206进程集合传入原 `foreground(wm,pids)`，并保留root对真实feed图的判词。不要硬编码6789或把任意获焦点PID加入白名单；UID未知、焦点歧义、关系/身份异常仍按原门停。头条6789的PPID是4782，host4583的PPID是373，不要求头条直接由imehost作为Linux父进程。这里只纠正集合参数，不改expected/consumer/validator。

**WL_PARENT_ID与参数window_id仍是imehost的33，不是焦点30。** 不因头条获焦点就派生为30或改run.sh。当前followup报告run.sh SHA为d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4，与此前同boot954的动态结果一致；root仍按冻结824期望做原精确核对，再继续collector→新proof→实际最终954。历史PASS只证明此对象语义合法，不顶替新最终954。

保留原host-only false原件，并用本修正侧件说明原因；不回写旧补充卡或operations-r2冻结稿。当前图由root亲读，本审不冒称重新读图或采集。精确路径/SHA及原纯函数本地输出在同目录results.json。零HDC、零签字、未改任何运行输入。
