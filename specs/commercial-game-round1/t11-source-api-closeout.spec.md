spec: task
name: "G11 source build and API evidence crosswalk"
inherits: project
depends: [t8-apk-extractor]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
在原神和头条修复并行时，提前核对源码、构建配方、证据与API全表的对应关系，交可合入的增量草稿和确定缺项，避免修复完成后再串行补档。不重复G04整包扫描或已有11行Boat音频复用表。
## 已定决策
- OC仅离线资料交叉核对，不改实现、不设备、不REA、不构建。实际主线在相邻westlake-harness，当前worktree旧时直接只读主线目标文件，不reset自己的旧工作。
- 从主线README及最近API交付入口定位权威表和生成器，记录精确源SHA；不随便选历史views。重点映射JAVA-042的G08 ZIP注释修复与G09构建配方、T35白屏证据与T36待完成修复；原表和生成器只读，独立目录写草稿与校验器。
- 每行含功能/API边界、实现路径与blob或SHA、原来源/补丁、工具链/构建入口、原始日志引用、Android/OH版本证据、验证app/设备/范围、当前部署及未验证项。应用专用守护和公共桥接API分类分开，不把宿主脚本包装成安卓API。
- 当前G08仅host Open成功，原神板上安装失败且未启动；G09未有真实编译前保持NOT_BUILT，T35不是修复通过，T36保持候选状态。未有新ACK不提升状态，不冻结单app候选。更新写expected_input_sha供外环合入前重核。
- 15分钟首片先给确定缺项，随后完整可读表+JSON+链接/SHA校验回执；输出不含凭据个人路径或大产物。知识源保存在仓库，私有日志用持久别名。
## 边界
### 允许修改
- benchmark/2026-10-21-dual-track-source-api/**
- tools/spec-checks/tests/dual_track_source_api.rs
### 禁止
- 不改权威API表、生成器、源实现、旧证据、冻结项、他人文件或主树，不push，不全盘扫描，不调用设备和REA。
## 验收标准
场景: 权威表和源码构建链对应
  测试: dual_track_source_api_receipt
  假设主线有G08及现有API全表
  当建立增量草稿并核引用
  那么每项关联到实际主线文件和SHA或明确缺项，权威表来源和预期输入SHA可重核
场景: 验证范围不得升级
  测试: dual_track_source_api_receipt
  假设只有host解析通过或白屏现场记录
  当输出验证app与部署状态
  那么原神游戏保持未启动、头条白屏修复保持待验，不以历史Boat或声音证据替代当前结果
场景: 缺失源码或日志
  测试: dual_track_source_api_receipt
  假设引用不存在或哈希不符或只有归档旧产物
  当校验交付闭包
  那么列具体缺项并拒绝标为可复现，不伪造本次构建日志
## 排除范围
正式API表修改、原神启动与头条修复上板，交外环审查后按实际证据更新。
