spec: task
name: "G27 prepare exact native-route transaction inputs"
inherits: project
depends: [t26-native-route-candidate, t20-gles-transaction-package, t24-gles-window02]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
在G26编译与回归进行时复用G20/G24已有组装器准备下一轮原神输入，避免候选完成后再找基线。只交离线可核的包及恢复绑定，实际设备窗口另行验收。
## 已定决策
- 基线是G24已实际恢复的319目标，host2a871、ANLeebd双别名、policy b8be双别名，以及单列Boat3指纹。复用G24窗口原bundle及原U7事务工具，不新写部署或首启编排，不假造旧owned state。
- 候选沿已验G24 policy878c保持其GLES共享名增量，再叠G26新host与ANL，方便和实报atfork结果对照。相对板上恢复基线逻辑变化恰5目标：host1、ANL2、policy2；同库双别名必须同SHA。实际U7写入成员按真实manifest逐项列，不称仅5次写操作。
- G26目前ANL候选640b3c87e2f0f86d31b7defbd8b892515636afa61dcbbab5030d422ec1fb7d86已实际编译；host候选仅在G26原始rc0及独立复验固定后消费，不从半写文件或预估哈希取值。先准备恢复包和组装入口，缺候选时输出pending，不伪造产物。
- 公共源码、构建原件、工具链和原始日志引用G26固定包及G18，不另编译。先核现有组装器的哈希消费者、host启动检查和全部别名，若有硬编码旧host阻断，报告原代码位置与最小缺口，不在此卡改工具。
- 复用原完整离线preflight/native/frozen/namespace检查；Linux执行通道若内环超时，保留终态并交精确argv，外环核后单一执行，不重复构建或重启服务。输出实际argv/rc/stdout/stderr，不把工具没运行称PASS。
- 不复用G24撤销的窗口例外或旧签字。默认rollout_ready=false，列明待外环精确审签和fresh只读基线绑定；本卡不得修改全局exceptions、签字或设备。缺签名导致门禁拒绝如实保留，候选离线齐套不等于deployable或游戏成功。
- 5分钟首片交实际包位置、5目标表和待补字段；随后消费G26固定结果完成机器可读包、英文README及path-only清单。公开不放大二进制与stderr；原始执行日志和产物保存在持久目录。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/native-route-package/**
- tools/spec-checks/tests/commercial_game_native_route_package.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/native-route-package/**
### 禁止
- 不设备、不修改G26源/产物、历史包、共享主树、冻结登记、例外表或部署器；不重试G14/T38被拒步骤，不push。
## 验收标准
场景: 五目标与完整恢复清单
  测试: commercial_game_native_route_package
  假设G24真实恢复证据和G26固定构建可核
  当调用原组装方法生成独立包
  那么相对319基线只有host1及ANL2和policy2发生逻辑变化，双别名同SHA，Boat3不变，真实写入清单和原恢复包SHA完整
场景: 缺候选或别名漂移拒绝
  测试: commercial_game_native_route_package
  假设G26某产物未固定或同库别名SHA不一致
  当检查候选输入
  那么拒绝齐套结论并列具体缺项，不能用旧host或半写文件代替
场景: 原门禁与待签认分开
  测试: commercial_game_native_route_package
  假设包齐套但尚无本窗外环签认或fresh板状态
  当执行可运行的原离线检查
  那么保存真实输出与rc并保持rollout_ready=false，不修改门禁或例外表，不把离线检查称设备成功
## 排除范围
设备部署、图标自动首启、游戏修改、保护绕过、额外ABI实现、永久保留候选。
