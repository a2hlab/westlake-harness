spec: task
name: "G18 build minimal GLES library visibility candidate"
inherits: project
depends: [t16-runtime-loader-triage]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
用已验证U13源码和配方构建最小公共loader修复候选，使原神已实报失败的libGLESv2.so依赖可见，不重写图形栈或改游戏。
## 已定决策
- 基线为实际部署libnativeloader SHA b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7，源是benchmark/2026-10-02-u13-single-native/sources/candidate/policy的10件及policy-build-receipt.json。该源shared_sonames已7项，system_libraries也7项；不能用bms当前6项头作基线。
- 在独立副本中只给shared_sonames JSON和对应头增加libGLESv2.so；保留原7项顺序、所有system_libraries、media_jni RTLD_NOLOAD、namespace隔离和原全部行为。预计移走key=genshin的libyuanshen依赖GLES名称不可见首阻断；不承诺后续JNI/图形已成功。
- __errno早期错误已被捕获继续，当前未证致退因果，暂不纳入补丁。原神直接GL导入0；不替换GLES占位件、不复制BoatAttack私有补丁、不增加全局宽泛搜索或任意库白名单。
- 复用U13实际policy编译链接命令和输入，将输出与源映射到本任务持久目录；先核工具链、依赖和旧日志SHA。不要执行会改历史树的旧stage()/build主入口。baseline重建必须等b8be；candidate保留实际stdout+stderr/argv/rc、对象和输入SHA，工具链和配方入库，二进制留持久位置。
- 运行原policy及native loader有意义回归，另证明旧7项原样保留、新增仅1项、错误/重复项仍拒绝；以实际候选ELF解析核shared8、导出/NEEDED与基线兼容，不以字符串命中替代配置消费。缺构建输入按local→OrbStack→hw248找，不改变源版本掩盖缺项。
- 5分钟首片交source diff/输入可用性；随后实际构建。外环尚需核child加载对象和最小部署窗口，候选不自动上板。所有有效脚本持久保存，不只放tmp。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/gles-loader-candidate/**
- tools/spec-checks/tests/commercial_game_gles_loader_candidate.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/gles-loader-candidate/**
### 禁止
- 不设备、不改原APK/游戏保护/运行时现部署/冻结登记/历史源、不运行或重做G14/T38被拒步骤、不push、不在共享源码树构建。
## 验收标准
场景: 最小policy增量
  测试: commercial_game_gles_loader_candidate
  假设精确U13源与实际基线相符
  当生成候选并运行policy回归
  那么原shared7及system7行为完整保留，仅增加GLES名称且重复或非法项仍拒绝
场景: 原始构建证据
  测试: commercial_game_gles_loader_candidate
  假设原编译器链接器与依赖可核
  当重建基线和候选
  那么基线等b8be，候选ELF实际shared8且导出/NEEDED兼容，原始执行日志与输入SHA持久化
场景: 缺证与部署隔离
  测试: commercial_game_gles_loader_candidate
  假设构建失败或实际child映射仍缺
  当汇报交件
  那么保留失败日志及缺项，禁止声明已部署或原神亮屏，不自动上板
## 排除范围
头条部署、errno修复、GLES全栈改写、游戏资源下载和可玩验收。
