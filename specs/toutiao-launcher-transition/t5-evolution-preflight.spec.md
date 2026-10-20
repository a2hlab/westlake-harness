spec: task
name: "Evidence-led campaign retrospective and offline host preflight"
inherits: project
depends: [t4-demo61b-host-update]
satisfies: [REQ-TTVIDEO]
---
## 意图
按用户要求在演示机更新结束后复盘进化环，将复发问题、工具准备、公共API冻结缺口和已验证操作方法关联到真实证据，并补一个无设备副作用的宿主部署离线预检工具。
## 已定决策
- 所有工作只读设备已有证据，不调用HDC/REA或远程服务，不重开板窗、不推送；复用已有工具优先，不编写新的部署执行器。
- 复盘最多处理3类复发问题，每类列证据、已有规则/工具、剩余缺口、可执行改进。区分流程已落地与仅提案，不把记录了知识等同门禁生效。
- 公共API严格沿AGENTS的2个不同app条件；同app不同板不算2app。冻结矩阵写源码/产物/实测/缺口，未达条件不新增frozen.json。方法配方的复用记录与公共API冻结分开。
- 新工具仅从本地T33原始intake与候选HAP提取宿主包差异、bundle UID/token、power两字段、runtime/guardian哈希与compat缺失断言，输出机器可读清单和输入SHA。只接受精确T32已验证baseline及只改Index.abc的候选，拒绝未知包/缺项/路径错误，不生成fresh授权或留板结论。
- 用本轮真实T33输入做一次正例，再用副本中的缺字段、错误baseline、额外HAP成员变化作负例；保留argv/stdout/stderr/rc，避免仅用模仿实现的合成正例。
- 本任务显式扩展project本地允许路径到下列工具和复盘目录。外环负责采认主树及精炼DIGEST/RUNBOOK，内环仅隔离树交付。
## 边界
### 允许修改
- specs/toutiao-launcher-transition/t5-evolution-preflight.spec.md
- scripts/lab/host_hap_preflight.py
- tools/spec-checks/tests/host_hap_preflight.rs
- benchmark/2026-10-20-evolution-closeout/**
- knowledge/context/evolution/FLAW-011.md
- knowledge/context/evolution/FLAW-012.md
- knowledge/context/evolution/FLAW-013.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md
- README.md
### 禁止
- 设备命令、修改运行时或旧签认、放宽冻结门、未验证API冻结、修改工具权限、远端推送。
## 完成条件
场景: 真实离线输入和清单输出
  测试: host_hap_preflight_positive
  审核: human
  假设 T33实际intake及T32已验候选可读取且输入SHA已钉
  当 离线工具核完整包成员和bundle power runtime controls
  那么 输出JSON带来源SHA和61b实际UID及30000/86400000，只称offline预检不称部署或fresh授权
场景: 错误或缺失输入拒绝
  测试: host_hap_preflight_negative
  审核: human
  假设 输入副本缺字段或原包不符或候选额外成员变化
  当 同一CLI运行真实负例
  那么 返回非零和明确错误，不能输出通过状态，不覆盖原证据
场景: 复盘和冻结边界有据可查
  测试: launcher_page_closure
  审核: human
  假设 进化卡及实际源码构建部署验收记录可读取
  当 对最多3类复发问题和新增API方法分级
  那么 每项有证据和缺口，2板同app不当2app，未达冻结门只列待补，已实施与计划明确分开
场景: 原件缺失和未知不升级
  测试: launcher_page_negative
  审核: human
  假设 引用未找到或只有summary或仅单app经过候选
  当 汇总工具和冻结完成程度
  那么 标unknown或pending并保留限制，不称原始回执完整或公共API已冻结
## 排除范围
新API修复、跨app上板实验、自动签认、自动生命周期晋升、重写历史记录、基础工具重构。
