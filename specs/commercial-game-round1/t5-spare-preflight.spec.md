spec: task
name: "G05 spare D600 fresh state and minimal Genshin launch preparation"
inherits: project
depends: [t3-official-input]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
在外环复验G04同时，用只读实际状态把下一次原神最小启动准备到可执行，避免静态交件后空等。
## 已定决策
- 首选5ea34a4500000000000000001123012c；只读核连接、boot、锁所有者、系统、内存/磁盘、当前宿主/parent/child身份、部署runtime和已有安装入口。无权限或断连记录真实错误，不改连接配置。
- 首片10分钟。读现有board_run/BMS安装器、Boat验证入口，给最小实验的具体argv、已有脚本来源和需派生参数；不重建整代、不搬Boat私有补丁。APK固定abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc。
- 计划包含启动前像/恢复动作、板锁、首屏截图与实际child日志采集；只观察首次启动，不登录、不取完整资源。单次设备写窗上限30分钟，1200秒前停止新实验并开始恢复。
- 原始命令及stdout/stderr/rc写持久私有目录；公开报告含哈希/别名，不含网络标识或凭据。当前卡不持锁、不安装、不点击、不重启、不改设备文件，不用REA。61b零动作。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/spare-preflight/**
- tools/spec-checks/tests/commercial_game_spare_preflight.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/spare-preflight/**
### 禁止
- 不修改主树、既有运行时、APK、账号数据或设备，不push，不解除其他任务板锁。
## 验收标准
场景: fresh板状态
  测试: commercial_game_spare_preflight_receipt
  审核: human
  假设 5ea当前通过USB连接
  当 执行有界只读采样
  那么 保留前后boot和所有命令原件，身份及资源按实际输出记录，不能用旧基线替代fresh状态
场景: 可执行下一步
  测试: commercial_game_spare_preflight_receipt
  审核: human
  假设 精确原神输入已验签
  当 核对现有安装和启动入口
  那么 交包含具体argv、参数来源、恢复与窗口截止的最小计划，未验证参数标unknown，不虚构准入或执行成功
场景: 设备不可用
  测试: commercial_game_spare_preflight_receipt
  假设 目标连接失败或已有有效锁
  当 预检发现不可用
  那么 保留错误及所有者信息并报告不可用，不接管锁、不重启设备、不改用61b
## 排除范围
本卡不执行设备写入，原神可运行性由后续实际窗口判定。
