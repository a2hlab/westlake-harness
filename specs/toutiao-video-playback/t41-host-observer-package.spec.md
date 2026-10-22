spec: task
name: "T41 package the passive host observation application"
inherits: project
depends: [t40-host-observer-compile]
satisfies: [REQ-TTVIDEO]
---
## 意图
把 T40 真实编译的被动宿主观察候选装入独立、可验签的应用包，保持历史已验证宿主的其余行为。此卡只完成离线应用打包，不执行设备部署或重入恢复。
## 已定决策
- 输入基座为 T32/T33 历史候选 HAP b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0，不能退回早期 df385 原包。从持久 T32 原始回执定位，不全盘搜索。
- 唯一内容变化为 ets/entryability/EntryAbility.abc 从 bb1eccd3338dde573393b24d81e26e67450d5461ba51f73e578d9e42a78cbde9 到 T40 db7814368150e9a90b39c77fb5762802ce033b1bccb43a53e719720516b59bdd；其余程序/资源成员逐字保留，包括现有 Index.abc、模块、图标与资源；唯一派生签名元数据例外按本目录 t41-metadata-exception.json 严格核验，不能泛化为任意 .pages.info 变化。签名容器变动另列。
- 复用 T32 package_sign.py 已验证的官方签名/验签方法、现有公共开发证书与profile，不更换身份、申请新权限或新增凭据。工具SHA按 T32 production-01.json 验证，签名前后确认身份与profile一致。不公开密钥或含凭据的命令参数；未脱敏原始日志留持久私有目录，公开索引按SHA关联。
- 先确认原包验签、输入ABC及源码来源、精确工具SHA；异常立即停止。新输出目录禁止复用；运行时落原始 argv/stdout/stderr/rc/时间。成功需真实签名/验签rc0和ZIP逐成员对照；模拟测试不能代替真实构建。
- 这不是 T38 运行时编排或已拒步骤的重试。不使用设备、REA、调试器、guardian、运行时部署器或权限变更；现有通道拒绝时停止该操作、不换入口。
- 2026-10-22 外环证据修订：首次真实签名因 .pages.info 变化被原判据拒绝，保留该失败；PageInfoGenerator 源码与签后ZIP页布局独立计算均证明该字段随ABC可执行页增加派生更新。规则由精确例外表限定，不删除代码签名、不放宽其他成员，也不追认首次运行通过。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-host-observer-package/**
- tools/spec-checks/tests/toutiao_host_observer_package.rs
### 禁止
- 不修改 T32/T39/T40 原件、sources、冻结项、其他车道文件、设备状态、权限配置、Git共享引用；不commit、不push。只交路径清单与SHA，由外环合入。
## 验收标准
场景: 真实单成员打包与验签
  测试: toutiao_host_observer_package
  假设原包、ABC、工具和身份符合固定输入
  当复用原签名方法构建新包并真实验签
  那么原包与新包验签均rc0，程序/资源仅EntryAbility变化、其余7程序/资源成员不变；另一个.pages.info只允许例外表中的精确前后SHA并与实际ABC页布局独立推导吻合，profile及证书身份一致，原始日志可核SHA
场景: 输入或内容漂移
  测试: toutiao_host_observer_package
  假设基座或ABC的SHA错误，或额外ZIP成员改变（包括.pages.info偏离例外表或布局推导）
  当调用实际生产检查器
  那么非零退出且不得标记包已通过，生产反例测试不只测试断言助手
场景: 构建失败或证据不完整
  测试: toutiao_host_observer_package
  假设工具不可用、签名验签失败、原始日志缺失或输出目录已存在
  当运行构建或验证
  那么停止并保留明确失败与原始日志，不覆盖原件，不声明部署或设备验收
## 排除范围
安装、重启、设备点击、重入协议、白屏修复验收、原神调试。
