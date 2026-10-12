spec: task
name: "Exact parameter realization for seal selfcheck and spare restoration"
inherits: project
depends: [t4-stability]
---

## 意图

落实用户 2026-10-12 批准的精确参数派生，使正常窗口 ID 变化与备机实际 UID 不会被误判为代码漂移。复用现有封板、自检和 restore-v6 编译器，只为白名单参数建立可复验的派生证明，保留原封存指纹与严格拒绝行为。

## 已定决策

- 仅宿主 UID/GID、设备序列号、独立控制目录与 run.sh 的单一 WL_PARENT_ID 赋值点可派生；request.bin 只允许已证实的 312/316 小端 UID/GID 字段变化，其他字节不变。
- 每个派生文件记录原模板 SHA、生成器 SHA、来源 seal SHA、实测参数及来源、替换位置、目标完整 SHA；缺参数、未知替换位置、重复位置和其他字节变化均拒绝。
- 原 seal 和历史 provider/executor 不覆盖；新 realization 由独立离线编译器产生，经过外环复验后才启用。默认预览零设备访问；实测自检只读并使用当前 boot 和宿主身份，不能拿文件里自报窗口 ID 当独立证明。
- 复用 restore-v6 的完整 487 目标包和既有事务，保留源码/构建日志、前像、元数据、UID/boot/锁/回滚检查；不重写事务矩阵。增加显式派生入口，不把原 seal 冒充目标 seal。
- 内环仅离线编码；实际 5cd 恢复、只读现场取参、启用签字由外环执行。原 signed_by 角色约定保留；允许用户本次批准所需自检入口窄改动。

## 边界

### 允许修改
- benchmark/2026-10-12-exact-realization/**
- scripts/lab/demo_selfcheck.sh
- scripts/lab/demo_restore.sh
- tools/spec-checks/tests/exact_realization.rs

### 禁止
- 不改既有冻结 API、运行时 native/JAR、原 seal、restore-v6 冻结文件、用户数据、现有运行目录或正在执行的回归 driver。
- 不发设备、VM、远端命令，不自动同意隐私、不杀父进程、不推送。

## 验收标准

场景: 真实模板按白名单生成精确目标
  测试: exact_realization_roundtrip
  假设 已钉真实61b模板和5cd实际UID及控制目录输入
  当 离线生成并复核派生证明
  那么 每个非派生文件SHA相等且派生文件完整SHA等于可复现生成结果并保留原sealSHA和参数来源，设备调用为零

场景: 未声明字节或参数来源变化拒绝
  测试: exact_realization_reject
  假设 模板存在单字节篡改或重复窗口赋值或未知替换位置或错误sealSHA
  当 验证派生文件
  那么 非零退出并指出具体路径和原因且不输出可执行恢复授权

场景: 只读自检绑定实测宿主窗口与启动身份
  测试: exact_realization_selfcheck
  假设 同板窗口ID发生批准范围内变化且有当前boot和独立宿主窗口证据
  当 调用显式派生自检入口
  那么 精确生成文件可匹配且输出派生证明和零设备写入，过期boot或仅从run.sh反推窗口ID的输入拒绝

场景: 恢复入口保留原事务守卫
  测试: exact_realization_restore
  假设 restore-v6真实目标包和绑定原seal的派生证明
  当 预览恢复入口并测试缺签名错误serial过期boot未知前像
  那么 预览列出原seal与目标完整文件SHA且零设备调用，任一守卫错误拒绝而executor字节保持原值

## 排除范围

- 原生随机崩溃根因修复、扩充API表、重跑历史大矩阵、新增应用或Boat、内环上板及封板签字。
