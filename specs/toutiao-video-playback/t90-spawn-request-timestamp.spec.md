spec: task
name: "T90 minimal ordinary spawn request timestamp candidate"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t89-host-lifecycle-latency]
---
## 意图
T89宿主前台事务已完成但新spawn晚约26秒。制作最小的请求发出时间标记候选，后续能区分调用客户端前等待与客户端响应等待；不改超时，不改启动授权，不宣称它已修复白屏。
## 已定决策
- cx-env实现，cx-reentry-peer独立复核。仅以已入库benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root/payload/real-spawn.sh这个独立启动客户端入口为参考（固定三个argv），不读watchdog/reentry脚本或进行退出/内存归属分析。
- 候选在原host_spawn命令之前仅用shell内建读取/proc/uptime，向stderr写一个可辨识的单调时间标记。不得记录请求内容/凭据；读取/记录失败不得阻止原命令执行或改变其返回码。原命令路径、socket和request参数逐字保留，stdin/stdout保持；不加后台进程、重试或sleep，不改客户端30秒上限或其他检查。不任意改exec/进程层次语义。
- 候选仅放benchmark目录，不覆盖原文件、不部署。保留原文件SHA、候选SHA和精确diff。动态离线测试通过隔离临时fixture把原绝对命令映射到fake命令，验证argv/stdin/stdout/退出码保持，以及uptime文件缺失时仍执行；不把fixture替换用于设备，不启动真实socket客户端。
- 测试至少覆盖原命令成功、非零退出、时间源缺失、时间标记与stdout分离。以真实shell运行并保留rc，不编造PASS。若无法保持语义就交reject，不扩大设计。6分钟首交，至多一页说明；没有部署验收不叫已修复。
- 外环另审部署对象/启动副本与成员清单，在验证过的部署方案形成前本卡不写设备。保持61b当前可操作现场，不因候选就重启或关闭头条。
## 边界
### 允许修改
- benchmark/2026-10-23-spawn-request-timestamp/**
### 禁止
- 设备调用或部署、修改既有源码/冻结件/运行时、读取此前拒绝脚本、改权限/检查/超时/请求数据、信号或内存分析、其他应用任务
## 验收标准
场景: 时间标记不改变正常启动语义
  审核: human
  测试: spawn_timestamp_candidate_review
  假设绑定原入口SHA且fake命令可记录argv及stdin
  当真实shell执行成功与非零退出用例
  那么argv和stdin/stdout/退出码与原入口一致，仅stderr多一个时间标记，无部署
场景: 时间源或记录失败仍保留原行为
  审核: human
  测试: spawn_timestamp_candidate_review
  假设uptime不可读或标记不可写
  当真实shell执行候选
  那么原命令仍执行且返回其状态，记录失败不改检查/请求/超时，不宣称白屏修复
## 排除范围
运行时部署、启动延迟修复、进程退出原因、冷启动封板与原神。
