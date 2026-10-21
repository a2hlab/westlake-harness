spec: task
name: "G30 reuse locale ABI for observed Genshin ctype failure"
inherits: project
depends: [t16-runtime-loader-triage, t26-native-route-candidate, t28-native-route-window]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
移走G28原神主库实际首终止点_ctype_@LIBC，复用已有公共兼容源码与已选择的native路径，按相关ABI簇交付可复现候选。不得把磁盘导出、早采maps或编译通过当实际namespace解析和游戏成功。
## 已定决策
- 输入固定G28 child14857/parent12781/birth1768375日志：L3259主库_ctype_缺失，后续Unity加载失败与JNI未绑定、exit1；MHY的__assert2是继续执行后的背景错误，不能改写为本轮主库首终止。
- 先交5分钟source/owner首片：从真实G26 host/ANL选择到native ABI加载、namespace继承、库搜索顺序和精确ELF导出，给逐open-site归属。G28 maps早于失败，不据此选实际赢家。预计移走首致命点的key仅genshin。
- 优先复用本地bionic_locale_compat.c的_ctype_指针与257字节表、strtoll_l和strtoull_l，并核已有db31/b8a与d205精确来源。先本地，再OrbStack，再hw248补来源；历史注释不等于对应AOSP字节验证。不给单符号新leaf，不引入新的namespace owner或全局搜索根。
- 原实现已存在而不可见时，交精确接线方案；若需要向已选native ABI合入该现有模块，以独立源副本和最小补丁实现，并保持原导出、构造、atfork/FD/__sF行为。先完成source/owner首片由外环采认具体接线，再构建，不擅自扩展host/ANL/runtime/audio发布。
- 同簇评审_ctype_@LIBC的OBJECT类型和8字节指针、EOF加256字节分类表，以及strtoll_l/strtoull_l的版本、errno/endptr和既有locale语义。__assert2只列独立次级缺口；若拟加入，必须先提供AOSP对应源码与保持报告后终止的语义证据，不使用返回成功或吞错误的桩。__sF和__ctype_get_mb_cur_max已有实现，不重复。
- 候选前核冻结和完整输入，实际重建所改组件的精确基线；d205若无可复现配方，保留缺口并先补齐，不替换成不明基线。构建在独立持久目录，保存实际argv/stdout/stderr/rc、源/补丁/依赖/工具链SHA与ELF。环境失败不计源码轮次，不重启服务或改权限。
- 实际函数回归覆盖EOF、ASCII、0x80至0xff分类、整数正负/边界/溢出/无转换/endptr及受支持locale行为；比较完整导出和DT_NEEDED，新增版本只含已批准簇。不能仅grep源码。首片只读分析不需运行时构建，后续单一owner构建；缺输入或语义偏差如实失败。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/locale-abi-candidate/**
- tools/spec-checks/tests/commercial_game_locale_abi_candidate.rs
- 私有持久locale-abi-candidate构建和证据目录
### 禁止
- 不设备、不部署、不改原游戏/保护/资产/已冻结实现/历史源码/门禁，不修改主树，不触G14/T38，不push，不与其他车道共用构建输出。
## 验收标准
场景: 来源和所有者精确闭合
  测试: commercial_game_locale_abi_candidate
  假设G28实际首终止和候选组件SHA已绑定
  当核现有locale源码及host和ANL加载路径并交source/owner首片
  那么每个拟改符号有类型版本与出处，接线和原有行为范围明确，早maps不升级为失败时赢家
场景: 复用实现的实际函数与构建回归
  测试: commercial_game_locale_abi_candidate
  假设外环已采认精确接线且原基线可重建
  当实际构建基线与候选并运行生产函数测试
  那么基线SHA精确相同，EOF及256字节分类和整数边界正确，原导出和依赖行为保留，完整原始日志可查
场景: 错误ABI与缺证据拒绝
  测试: commercial_game_locale_abi_candidate
  假设把_ctype_误作函数或数组、表长错误、版本漂移或缺源日志
  当验收候选
  那么逐项拒绝，不以测试替身代替生产函数，不静默换基线或扩大符号范围
场景: 离线候选不升级为运行成功
  测试: commercial_game_locale_abi_candidate
  假设实际namespace解析和游戏页面尚未复验
  当输出结果及源码构建对照
  那么保持未部署和游戏未成功，不登记公共API冻结，不宣称所有缺口已解决
## 排除范围
游戏修改或保护绕过、新命名空间机制、全量设备验收、头条部署、游戏资源下载及登录。
