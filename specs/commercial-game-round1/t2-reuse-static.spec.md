spec: task
name: "G02 qualify reusable runtime mechanisms and exact-input scan entry"
inherits: project
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
并行复核BoatAttack已验证公共机制与现有静态扫描入口，形成后继拿到精确商业游戏输入即可执行的最小检查卡。不凭引擎同名预填兼容结论。
## 已定决策
- 从旧boatattack-comparison及其实际源/构建/运行记录出发，每项列出source/output SHA、已验范围、不可移植的app私有补丁、原神待证条件。
- 用户追加：纳入此前音频经验，区分AudioTrack有效ring容量getter、后端namespace归属、OpenSLES ABI宽度与PLAY回调支持；头条已验音频不作为原神通过证据，优先复用原始REA结论而非重复逆向。
- 列现有manifest/ELF/JNI/open-site扫描器的实际CLI、输入要求和输出；至少一个可用入口以现存小真实APK离线执行并保留回执。该APK结果只是工具冒烟，不能称原神扫描完成。
- 未取得t1精确输入时不猜原神引擎版本、ABI、Vulkan/GLES要求、缺口数或首致命点。无需REA就不用；存在精确二进制问题时给对象SHA/地址/问题另派，不以摘要充工具原件。
- 本切片15分钟内交README.md、results.json、reuse-matrix.json、scan-entry.json、source-index.json，补最小Rust commercial_game_reuse_receipt校验；目前该选择器不存在不得报通过。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/reuse/**
- tools/spec-checks/tests/commercial_game_reuse.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/reuse/**
### 禁止
- 不改旧工具、运行时、冻结项、其他车道、主树；不联网下载、不操作设备、不产生原神运行通过声明。
## 验收标准
场景: 可复用能力有精确来源
  测试: commercial_game_reuse_receipt
  审核: human
  假设 BoatAttack的源码构建运行证据存在
  当 核验引用并建立矩阵
  那么 每行区分公共机制与app私有补丁，声明复用条件和未证项而非原神PASS
场景: 工具入口缺失或真实消费失败
  测试: commercial_game_reuse_receipt
  审核: human
  假设 记录的CLI不可用或工具拒绝实际输入
  当 离线执行最小实际消费
  那么 保留argv/rc原件并记缺口，不把帮助页或手写命令称已验证入口
场景: 原神输入缺失
  测试: commercial_game_reuse_receipt
  审核: human
  假设 t1尚未交精确包
  当 输出检查卡
  那么 原神特有字段均为UNKNOWN，真实APK工具冒烟独立标注，后继依赖指向t1结果
## 排除范围
游戏代码修复、资源下载、上板实验、同app跨板冻结公共API。
