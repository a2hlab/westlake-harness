spec: task
name: "G06 exact Genshin first launch on spare 5ea"
inherits: project
depends: [t4-exact-static, t5-spare-preflight]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
用真实一次启动取代继续推测，找到原神在既有桥接运行时的实际首屏或首个阻塞点，以此确定下一轮修复。
## 已定决策
- 仅5ea34a4500000000000000001123012c。官方APK SHA256 abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc，513290344字节；不改包、不搬Boat私补、不换公共runtime，不登录或同意账号操作，不下载完整资源。
- 外环采认G04和G05后派发；先fresh读取与前像一致检查、板锁和恢复方案，沿既有board_run/BMS安装与正常launcher路径。仅为首次启动派生单包manifest、参数和有界日志采集；不得为跑通放宽既有身份/冻结/恢复门。
- 保存实际安装输出、早期child stderr和hilog、boot/PID/birth、t5/t20实际截图；有首帧继续观察至t60或出现资源/登录提示即止。记录Application到native加载的实际边界，不把缺marker、main回退名或静态未匹配JNI当根因。
- 一个设备写窗不超过1800秒，1200秒前停止新实验并恢复；失败和超时也走恢复，恢复失败保持锁并报告，不另开窗口。恢复原宿主/前台/电源，保留原runtime和用户数据；新安装包及本次生成目录的清理仅在证明为本窗新增且无消费者后执行，原始证据持久保留。
- 为后续修复复用，允许在5ea保留已核身份的本窗原神安装包和新数据目录；闭窗须停止本窗child并明确记录保留清单，不把保留安装当运行通过。不要求每轮卸载再装或删除新目录。若选择卸载，断连、空包列表及身份不明均拒绝成功；其他现有app数据不动。
- 先完成真实试验和收窗，再长报告。结果含first_fatal原行/时间/进程或UNKNOWN、首图及facts原样、所有执行argv/rc与恢复证据；脚本PASS不等于亮屏，不声称已可玩。
- CC执行设备动作，不调用REA；Codex可离线检查新计划/工具，不能同时向同板写。61b不动。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/first-launch/**
- tools/spec-checks/tests/commercial_game_first_launch.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/first-launch/**
- 5ea本窗新包及既有安装器必须的可恢复状态，须列明准确路径和前像
### 禁止
- 不改冻结实现、系统运行时、信号策略、保护机制、用户账号和已有app数据；不push，不删除旧证据，不操作61b或5cd。
## 验收标准
场景: 准入及单次启动
  测试: commercial_game_first_launch_receipt
  审核: human
  假设 G04和G05已采认且fresh身份一致与板锁有效
  当 使用精确APK完成安装并正常启动
  那么 保留实际执行回执及t5/t20截图，每个结果绑定boot和child身份，首屏只按实图判定
场景: 首个实际阻塞
  测试: commercial_game_first_launch_receipt
  审核: human
  假设 启动未达到游戏画面
  当 读取覆盖启动时段的stderr和hilog
  那么 给出最早可证失败原行及所属进程，覆盖缺失写UNKNOWN，不以静态候选替代实测
场景: 恢复并闭窗
  测试: commercial_game_first_launch_receipt
  审核: human
  假设 单次观察结束或发生失败超时
  当 执行本窗恢复和复核
  那么 记录原runtime与宿主电源恢复、实际截止时间和解锁；恢复失败保锁不冒称闭窗
## 排除范围
本卡取得真实第一轮阻塞，不承担完整资源、登录、玩法和封板；后继按实际问题继续修复。
