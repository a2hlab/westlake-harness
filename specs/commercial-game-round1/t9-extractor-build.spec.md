spec: task
name: "G09 narrow reproducible installer build for ZIP comments"
inherits: project
depends: [t8-apk-extractor]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
把已通过原源码host复演的ZIP注释修复构建为可审查的libinstalls候选，推进原神真实安装。只重编实际消费的zip_file.o并重链接，保留源码、补丁、工具链与真实执行日志，避免改源码却链接旧对象。
## 已定决策
- 开始候选构建前核G08最终源码SHA4068fdbae99b602062311b1f477b14b8702b07814bba44d09ffdbfa792c601c1和对应patch；peer已独立验证原神Open1567项、8边界及坏包拒绝。仅host通过，不宣称安装通过。
- 复用G08-BUILD-PREFLIGHT(0906511581)的真实检查及JAVA042归档61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6，478511698B。使用现成OrbStack a2hlab Linux x86_64、Python3.12、原编译器SHA b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913和原246参数zip_file.cmd；新独立目录，不覆盖旧kit。
- installs.ninja没有zip_file.o编译边；先用verified-seed原source及原命令显式编译zip_file.o，再ninja仅链接libinstalls.z.so。CCACHE_DISABLE=1；确认对象进入实际rsp/链接输入。不要运行仅touch另外两文件的旧build.py并宣称ZIP修复生效。
- 先无补丁基线编译/链接，期望对象2e2a6247前缀与产物51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5；不一致则保留差异并定位构建/源码输入，不能强行标等价或继续部署。随后在隔离副本应用单补丁，编译/链接新候选，核函数/符号/NEEDED及APK未改变。
- 每步实际运行时捕获argv、stdout、stderr、rc、开始结束时间到持久私有build-runs；公开小回执使用别名与SHA，不提交大产物/个人路径。构建前check_frozen；源码/补丁/可执行构建配方及结果进入本卡路径供外环合主线。源/链接失败如实报告，环境失败修好可重跑，不替换失败原件。
- 本卡不设备、不重启、不安装、不部署、不REA、不修改既有冻结源，不构建libbms或整代runtime。首片20分钟，只有缺确切工具链/源码闭包才报精确缺项，不能拿归档旧产物当本次成功。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/apk-extractor/native-build/**
- tools/spec-checks/tests/commercial_game_extractor_build.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/build-runs/**
- a2hlab下本卡新建的独立构建目录
### 禁止
- 不改原kit、主树、APK、冻结文件、设备或其他agent文件；不push，不用缓存或归档产物冒充实际编译成功，不丢原始日志。
## 验收标准
场景: 无补丁基线真实重编
  测试: commercial_game_extractor_build_receipt
  假设输入归档工具链及源pin匹配
  当显式编译原zip_file.o并重链接libinstalls
  那么实际日志rc为0且输出匹配原SHA，或如实记录不等价及具体差异并拒绝候选准入
场景: 单补丁候选与复现配方
  测试: commercial_game_extractor_build_receipt
  假设无补丁基线已等价且G08候选SHA已采认
  当应用精确patch并执行同编译链接命令
  那么新对象和产物SHA与真实rc0日志绑定，配方可从归档及仓库patch重放，唯一修改源为zip_file.cpp且APK原SHA不变
场景: 缺输入及失败不得升级
  测试: commercial_game_extractor_build_receipt
  假设归档源工具链pin不匹配或编译链接返回非零
  当整理本轮结果
  那么保留失败argv和双流日志、结果为失败或UNKNOWN，不以旧产物存在判通过，不执行任何设备动作
## 排除范围
设备实验、原神安装和游戏可玩验收，候选完成后另派单文件短窗验证及恢复。
