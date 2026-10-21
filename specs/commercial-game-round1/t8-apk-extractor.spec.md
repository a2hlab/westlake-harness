spec: task
name: "G08 reproduce exact Genshin APK native extractor rejection offline"
inherits: project
depends: [t6-first-launch]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
G06第二窗真实安装停在APK_NATIVE_SO提取器初始化，尚未启动原神。沿精确APK及实际错误查源码和ZIP结构，给出可复演的首个拒绝条件及最小修复，不用重复上板猜测。
## 已定决策
- 输入为官方APK SHA256 abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc、513290344字节及first-launch/window-outer-02实际install-hilog：15:59:05.058 installd PID13171，base_extractor.cpp Init43 open zip file failed errno22，ExtractApkNativeFiles3212，APK_NATIVE_SO ec8519936；manifest和资源HAP先成功。errno22不是已证具体根因。
- 先本地已收JAVA-042-installer/FZ-001源与已验证实现，再本地其他树/vm-copies，再OrbStack，再hw248；有界找bundle_extractor/base_extractor/zip_file调用链及对应版本。来源路径/commit/blob和部署对应程度分开记录，不把源码存在等同板上同源。
- Codex车道只做离线分析，可用REA检查精确现成安装器制品来绑定拒绝路径；不调用设备、不修改APK、不做签名/授权绕过、不改变保护行为。完整APK/提取大文件/反编译原文放持久私有目录。
- 读精确ZIP的EOCD/CD/local-header/entry flags/method/offset/size/签名块布局，沿原解析器条件复演；正常小APK作对照。优先复用原源码最小host harness，不重写一个宽松解析器来宣称修好。不靠单一errno或猜测ZIP64定根因。
- 20分钟交首片；若不能复演，明确阻断的源码/部署件或具体未证条件，给下一项最小取证。若找到根因，可在新目录写最小源码补丁及配方/测试，不改现有冻结源、不构建上板产物。本卡预计移走首个致命点的key仅genshin。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/apk-extractor/**
- tools/spec-checks/tests/commercial_game_apk_extractor.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/**
### 禁止
- 不修改主树、APK、现有冻结实现、运行时或设备；不push，不覆盖失败回执，不安装/启动/登录，不下载完整资源，不递归扫整盘。
## 验收标准
场景: 精确输入与失败边界
  测试: commercial_game_apk_extractor_receipt
  假设G06实际安装输出与官方APK存在
  当校验SHA和逐条安装日志
  那么结果记录APK身份、成功的manifest/HAP阶段和首次native提取失败原行，运行状态为NOT_STARTED
场景: 原解析器拒绝条件复演
  测试: commercial_game_apk_extractor_receipt
  假设已定位版本明确的原提取器源码
  当对精确APK及正常小APK运行同一离线入口
  那么记录实际argv/rc、首个拒绝分支及ZIP字段偏移；若源码或部署对应不足则结论UNKNOWN并列精确缺项
场景: 最小修复与失败保留
  测试: commercial_game_apk_extractor_receipt
  假设已证拒绝条件且存在可行兼容修复
  当在新目录应用补丁并复跑原输入、正常对照和截断坏包
  那么原输入过该拒绝点、对照保持、坏包仍拒；无法完成则状态未验证，原APK哈希不变且不声称板上安装成功
## 排除范围
设备部署、完整游戏启动、资源下载、玩法验收和封板；本卡产出推动后继真实安装验证，不代替其结果。
