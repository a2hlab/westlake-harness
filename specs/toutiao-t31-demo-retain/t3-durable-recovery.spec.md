spec: task
name: "T31 exact six-state durable recovery successor"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-offline-preparation]
---
## 意图
实现仅5cd当前T30六态的独立rollback入口。本次T31真实apply-plan和备份来源不变，不接受已回滚T30 plan冒充当前候选，新恢复窗拥有独立真实holder/start与1800秒预算；解决原同窗执行器过期后无法使用的生命周期缺口，不更改业务候选或已冻结执行器。
## 已定决策
- recovery.py从executor693448逐字派生，只接受rollback，默认preview不接设备；execute需显式origin-data、原apply-plan及原apply-admission。origin数据逐SHA锁定，原admission哈希等于plan字段；原holder/start/executor与原admission一致，新holder/start独立且不能等于旧holder。新窗口start晚于旧窗口，1800秒内；不修改原plan任何字段。
- 新admission由本地recovery_admission.py消费当前held与boot/parent/host/WMS/metadata前后原始读数生成；原exe/UID/namespace/来源门不变。八个静态来源pin中只替recovery executor SHA，原admission另存SHA；未给有效origin或fresh身份在Board初始化前拒绝。
- 只支持本次T31实际apply的origin WID29及恢复fresh WID29；raw run/WMS/parent环境须同时29，owner已20011300。WID漂移或dead parent拒绝，超范围恢复UNKNOWN需另审，不承诺无条件救援；任何其他run字节变化、foreign media/player/bridge/shim/compat均拒绝。原五文件备份必须全部存在且逐SHA/metadata验证；ABSENT marker沿原门核存在及精确SHA，不新增未采metadata准入，不新建备份、不截断映射inode。
- 原backup路径仍用origin boot8，不用当前boot替换。原顺序、同目录temp校验→紧邻SHA/metadata CAS→rename、compat精确删除及freshboot要求保持。源门绑定继任来源文件与旧原件；没有恢复成功回执不能宣称恢复。
- 离线从真实继任代码执行已知pre/post状态矩阵、六个实际写入cutpoint、foreign/missing-backup/backup漂移/live身份拒绝及生成脚本CAS检查；只替传输为fake，允许本地bash验证真实guard；不执行设备shell或HDC。原始命令stdout/stderr/rc持久保存，交第二peer复核前不得开设备窗。
## 边界
### 允许修改
- specs/toutiao-t31-demo-retain/**
- benchmark/2026-10-20-t31-demo-retain/**
- tools/spec-checks/tests/toutiao_t31_preview.rs
### 禁止
- benchmark/2026-10-20-t30-request-recovery/**
- knowledge/frozen/**
- 禁止设备调用、修改MAIN及原备份、编译运行时、伪造旧start、推送。
## 完成条件
场景: 新恢复窗与原apply来源分离
  测试: ttvideo_t31_recovery
  假设 原apply已过期且新held及fresh读数属于另一个窗口
  当 生成新恢复admission并预演真实继任rollback分支
  那么 当前预算取新start，旧holder/start/boot和plan字节不变，备份只取原boot来源
场景: 过期假身份与来源漂移拒绝
  测试: ttvideo_t31_recovery
  假设 重用旧holder或新窗已1800秒或原plan/admission/hash/source不符
  当 请求恢复准入
  那么 非零拒绝且不建立Board或调用设备
场景: 已知混合状态逐项恢复且拒foreign
  测试: ttvideo_t31_recovery
  假设 五文件各为精确before或after且compat为absent或精确after
  当 运行继任真实校验与脚本生成分支
  那么 known组合保持逐件CAS且先核全部备份，任意foreign或缺一备份或ABSENT marker均拒绝，不输出可用成功回执
场景: 默认预览及未授权操作拒绝
  测试: ttvideo_t31_recovery
  假设 无execute或请求apply或缺fresh准入
  当 运行继任CLI
  那么 preview只输出JSON与device_calls0，apply或缺参非零拒绝，不修改文件或调用设备
