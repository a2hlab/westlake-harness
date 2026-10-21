spec: task
name: "G26 source build exact Genshin native compatibility route"
inherits: project
depends: [t16-runtime-loader-triage, t24-gles-window02]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
复用已有公共 native-cluster 路径，构建原神精确选择候选，移走 G24 实报的 libyuanshen __register_atfork 首个致命点。现有 d205 ABI 也覆盖主库的两个 FD 检查导入；不把静态覆盖或候选构建当游戏可用。
## 已定决策
- 依据 G16 g24-route-comparison、g24-host-build-readiness、g24-atfork-bootstrap 固定报告；当前 host 基线 2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e，ANL 基线 eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c。G24 policy 878c 是已有独立产物，本任务不重建或改变它。
- 在完整源码快照副本中，给 ANL 与 host 已有 native_cluster_path 增加精确包组件 com.miHoYo.Yuanshen，保留现有13个native及6个Flutter选择、私有根限制、caller GLOBAL拒绝、namespace身份检查。近似前后缀、大小写变化、别的app必须不新增命中。
- ANL native shared表对精确原神域额外允许 libmediandk.so，沿现有host配置机制继承，不全局增加白名单或搜索根。精确选择须覆盖实际 path/app_paths/app_permitted_paths 输入；两组件选择保持一致。不得改变其他native/Flutter shared表。
- 复用已部署私有 d205 ABI及现有host固定路径 NOW|GLOBAL发布；不改ABI实现、不添加空桩或补丁到游戏。保留 atfork不支持DSO卸载注销的已知限制。给出三处精确LIBC导入与导出的对照、所有新增open-site及namespace归属。
- 现有native路径带来libandroid/GLESv2/zlib来源变化；以实际精确provider核DT_NEEDED和符号版本，不把磁盘闭包当运行时可见性。核 libmediandk 到host-owner的路径及runtime依赖；若还需新增resident/runtime/audio发布步骤，先交证据给外环追加决策，不自行扩大补丁。
- host使用U13 baseline命令对和U12完整应用源码/头；ANL使用N3完整源码/include/map及已核工具链，不能拿N5替代eebd。仅在独立持久目录构建，不运行会改历史树的stage脚本；保留原命令语义与输入，对路径派生明确记录。
- 先核所有输入SHA及冻结检查，再实际重建两个基线并要求精确SHA相等；失败保留原argv/stdout/stderr/rc及差异，禁止悄悄换基线。每个成功候选保存真实执行日志、编译依赖、实际链接库输入、工具链SHA、完整源码、补丁和复现入口。可复用对象与缺完整源的边界如实列出，禁止称全源清洁重编。
- 5分钟首片交完整source diff、输入可用性和owner/shared准入结论；随后单一owner执行构建。缺环境输入按本地、OrbStack、hw248顺序，环境失败不算源码构建轮次，禁止重启服务或改变权限。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/native-route-candidate/**
- tools/spec-checks/tests/commercial_game_native_route_candidate.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/native-route-candidate/**
### 禁止
- 不设备、不部署、不修改APK/保护机制/历史源/冻结登记/主树，不运行或重做G14/T38被拒步骤，不push，不在其他车道源码目录构建。
## 验收标准
场景: 两入口精确选择及mediandk增量
  测试: commercial_game_native_route_candidate
  假设精确host和ANL基线完整源码已绑定
  当实际执行候选选择函数及namespace参数捕获回归
  那么仅原神新增native选择与mediandk继承，原13个native和6个Flutter及普通控制均保持原选择与共享表
场景: 错误选择和范围扩张被拒绝
  测试: commercial_game_native_route_candidate
  假设输入包含原神近似包名、错误大小写、无私有根或caller GLOBAL
  当执行实际选择和host边界函数
  那么近似目标不获得新增兼容行为，原拒绝行为不放宽，真实函数回归而非仅grep源码
场景: 两个基线与候选构建证据
  测试: commercial_game_native_route_candidate
  假设工具链和编译链接输入SHA已核
  当执行原配方的独立目录构建
  那么两个基线等2a87118e及eebd62f2，候选导出和依赖差异可解释，真实rc日志与完整来源保存在持久位置
场景: 构建失败与证据缺口不得升级为运行通过
  测试: commercial_game_native_route_candidate
  假设基线不等或provider可见性尚未实证
  当生成结果和API对照
  那么保留失败与unknown，不称已部署、游戏帧、API冻结或全部缺口修复，不自动触板
## 排除范围
游戏保护绕过、游戏资产修改、音视频新实现、头条部署、设备验收及完整游戏可玩性验收。
