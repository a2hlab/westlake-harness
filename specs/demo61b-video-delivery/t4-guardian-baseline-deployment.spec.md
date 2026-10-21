spec: task
name: "Deploy and verify the r3 guardian as an independent 61b baseline"
inherits: project
depends: [t3-confirmed-child-retirement]
satisfies: [REQ-TTVIDEO]
---
## 意图
复用原icon-r2独立控制目录与cfg事务，先验证并留板r3 guardian新基线，再重新采fresh控制SHA准备视频迁移；本窗绝不同时更换视频六件。
## 已定决策
- 复用benchmark/2026-10-19-toutiao-icon-deploy/prepare.py与deploy.py事务及test_deploy.py真实shell测试；新目录机械派生当前before cfg入口与CC精确holder/start绑定。原OLD_ROOT固定sealed r1且只查outer首token不适用，不原样执行、不放宽成任意cfg/holder；没有新通用executor。
- t3独立peer通过、r3完整生成器SHA级联与精确文件清单冻结后才能填写准入；当前候选SHA/新root/boot/holder/approved_by均null。entry引用watchdog/helper、members逐项SHA/mode、startup.env引用members、startup.expected引用startup.env、cfg引用boot-entry逐级实际验证；所有新增依赖入包，不手改哈希使门通过。
- CC唯一设备执行，外环只审核。新独占窗口≤1800秒，1000秒停止新增实验，1100秒准备恢复，1200秒前明确签留或开始实际回滚，余600秒完成恢复与解锁；本次完整holder/start固定，每次设备命令校验，命令超时及远端唯一rc标记保留，未知写不自动重试。
- 写前只读备份本次实际cfg原字节/metadata、当前root成员及entry/members/startup/expected完整链、HAP、当前runtime六态、run、power/debug和身份；沿现有只读配方，不再全扫518。新root必须不存在且非symlink，先全部传输SHA/mode/owner/label核对，最后仅cfg服务入口原子CAS切换；原目录/旧锁/stop/events不删不改。
- 旧guardian已退出和旧lockowner stale的处置仅正常reboot进入新boot，不手清锁、不kill、不启动第二guardian。启动顺序复用原boot-entry服务与普通图标；新boot核新guardian PID/birth/实际控制root及members、新parent/host/WID，runtime六态保持原基线（run仅既有单WL_PARENT_ID数值派生有证据时单列），不能把cfg放置成功当已生效。
- 一次正常图标须有实际child PID/birth/parent/UID/exe与spawn回执和真实feed图。若窗口内自然child退出，再一次普通Home→图标，核strict退役事件与新child身份及feed；不人为制造崩溃/发信号、不等待自然退出拖过截止。未自然退出记该动态分支NOT_OBSERVED，不能伪报已验；外环可基于明确离线退役测试和本次fresh启动/feed作限域guardian留板，不等于视频封板。
- 候选失败/无签留则原plan+真实apply transaction恢复本次before.cfg，正常reboot重新核原控制链、runtime六态、原power/debug/只读root挂载及UI事实后解锁；foreign cfg拒绝自动覆盖并立刻交外环，不删除新root证据。cfg恢复只是物理恢复，不能代替新boot运行态核验。
- 留板须外环approved_by=outer(codex)真实签认；签后保存新guardian完整控制SHA基线，再为T34视频executor单独fresh-bind，不复用旧18SHA的恢复卡。声音沿已有用户确认不重复问，不增加新的61b人工听验声明。
- 输出机械delta、原始测试、unsigned准入、执行/回退卡、完整source pins及本次device receipts。新增demo61b_guardian_deployment为待实现Rust薄入口，调用复用的实际shell事务测试；尚未实现/执行不得报通过。
## 边界
### 允许修改
- benchmark/2026-10-21-t34-demo61b-video/guardian-deployment-01/**
- tools/spec-checks/tests/demo61b_guardian_deployment.rs
- 独立持久证据$HOME/.local/share/westlake/t34-guardian-deployment-20261021/**。
- 外环实际签认后，CC独占61b新icon-manual-*控制目录、唯一头条init cfg、正常reboot/UI/临时power及精确失败恢复。
### 禁止
- 不改r2原件、T31候选runtime、视频六件、HAP、共享runtime、用户数据或权限，不写5cd/5ea，不手清旧锁/stop、不signal进程、不假报新音频或视频通过、不推送。
## 完成条件
场景: 源链与本次前像完整才生成可执行卡
  测试: demo61b_guardian_deployment
  审核: human
  假设 t3审过且本板完整cfg控制链和r3精确输入已核
  当 派生原prepare和deploy的最小数据及holder变更
  那么 完整级联及新root边界均验证，未填SHA或未签准入只可preview且无设备调用
场景: 部分传输与错误身份不切换cfg
  测试: demo61b_guardian_deployment
  假设 传输失败或SHA身份holder/start不符或root已存在
  当 实际生成事务在本机故障夹具执行
  那么 cfg仍原值或按精确本次plan恢复，所有未知和原始rc保留且不自动重试写
场景: cfg事务失败仍回封并恢复精确原入口
  测试: demo61b_guardian_deployment
  假设 cfg CAS或remount失败或跨boot需要回退
  当 沿本次apply transaction执行恢复
  那么 仅接受before或after字节并保持metadata，恢复实际before入口而非旧sealed或inert入口，root恢复只读且新root不删
场景: 新guardian生效与退出分支如实分级
  测试: demo61b_guardian_deployment
  审核: human
  假设 正常reboot后新guardian身份和控制链均实核
  当 普通图标产生child及feed且如有自然退出则手动再次进入
  那么 startup与重开各按实际identity和图像判定，未自然退出分支NOT_OBSERVED，未改视频runtime且不声称视频封板
场景: 独立基线留板或原样恢复后解锁
  测试: demo61b_guardian_deployment
  审核: human
  假设 1200秒前达到决策节点
  当 外环签限定guardian留板或CC执行本窗精确回退
  那么 1800秒内完成原power/debug恢复与解锁，留板生成新控制SHA基线而失败恢复原链，新视频窗口不复用旧18SHA准入
## 排除范围
- 视频六件迁移、新runtime修复、SIG11根因、人为制造退出、重复听验、新通用执行器、原神任务。
