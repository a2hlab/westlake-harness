spec: task
name: "T43 observe the owned host through its supported desktop icon"
inherits: project
depends: [t41-host-observer-package]
satisfies: [REQ-TTVIDEO]
---
## 意图
通过已验证的普通桌面图标入口观察自有宿主的真实生命周期。T42 的 AA 调用被系统拒绝，未到回调阶段；本卡使用应用面向用户公开的正常入口，不调整调用者权限或应用权限。
## 已定决策
- 历史依据为 T32/T33 的 AppIconCommonView_org.westlake.imehost.EntryAbility 实际点击及采认回执；b189 的 module 声明 exported=true、visible=true、home skill。历史成功不替代本次实际画面/回调，不使用 aa start、不修改 exported 或任何权限。
- 唯一板为 5cd1e3dd00000000000000000923012c；T42已于12:24:57恢复b189并释锁。每轮仍须重新只读核boot、HAP b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0、bundle身份、filesDir与锁；持锁后再次复核，不能继承旧context或holder。
- 候选只用已采认 T41 release-02，SHA02f56d181fa883f96505e196570eab6ea75911fa2f1e5edab15f5180c9f19485，59008B；恢复包必须b189。使用正规同签名 bm install -r，不卸载、不清数据，不重启。
- 写前/恢复后分别保存同一清单的native runtime与boot-image逐件SHA（bms_batch.FINGERPRINT_PATHS及BOOT_IMAGE_PATHS，只读取，先展开并固定实际路径集合，逐项保留rc/stderr及完整SHA，缺必需项或读失败拒绝，不能直接采信旧helper过滤后的摘要）；保存宿主数据目录stat的设备号/inode/模式/UID/GID和power-shell当前实际超时前像。任何必要前像缺失即不开写窗，不能把证书fingerprint或UID当完整运行时/目录身份。
- 最多两次标准桌面图标点击：正常Home到桌面，从当前layout选精确图标ID及bounds并保存选择证据后点击，采一次观察记录/宿主PID与birth/截图；可再次Home后点击同一图标。标记automated_desktop_click，不冒称人工触屏，不强求onNewWant。不能用旧坐标或把其他app当目标。
- 只使用现成普通UI操作及layout采集/select_icon纯解析接口（layout是设备操作，保存回执并计入电源副作用）；不得调用包含无关弹窗处理、批量滑屏、冷停的整体runner。必要时正常唤醒屏幕；若遇密码/PIN/权限对话框或任一步操作被拒，立即停止，不绕过。uitest会改变屏幕超时，结束必须按实际前像恢复并核对，不写固定猜测值。
- launch-observation与window-state逐次留存，判别未启动、观察文件写失败、有效回调、旧记录未更新；manual_origin仍unverified、eligible_for_reentry仍false。截图接收前后SHA相同并目读；截图或layout含私人信息时只提交SHA/私有路径和不含隐私的分类。
- 现有桥接环境可能自行响应宿主窗口，原样观察；不修改、启动、停止或编排guardian、第三方进程或运行时。不是T38编排重试，不使用REA或调试器。遇工具/安全拒绝停止，不换工具或模型重试该操作。
- 最多20分钟实验，另留10分钟恢复；结束先恢复b189、核候选宿主实例已退出、身份/完整前后清单/目录元数据/电源前像，再释放锁，然后写报告。安装超时或结果未知先只读核实际状态，不盲重装。原始argv、时间、stdout/stderr、远端rc持久保存，正文失败即停止，shell rc0不能单独放行。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-host-launcher-observation/**
- tools/spec-checks/tests/toutiao_host_launcher_observation.rs
### 禁止
- 不修改冻结项、既有源/回执、权限、guardian、第三方app、运行时或其他板。不新增设备编排器，不commit、不push；内环执行普通操作并交路径/SHA，外环复验合入。
## 验收标准
场景: 桌面入口回调与恢复
  审核: human
  测试: toutiao_host_launcher_observation
  假设真实身份与全部前像符合固定输入且本轮持有5cd独占锁
  当同签名更新后最多两次精确图标点击并逐次采证再恢复
  那么保存当前layout与选择/点击回执、实际回调或明确缺失分类、截图SHA与目读结论；恢复HAP和候选实例退出、身份/完整指纹清单/目录元数据/电源均逐项核对后释锁，不宣称白屏修复或人工触屏验收
场景: 前置条件缺失或操作被拒
  测试: toutiao_host_launcher_observation
  假设前像不完整、图标无法精确识别或任一调用正文失败
  当执行准入或普通操作
  那么立即停止后续请求、保留原始失败与真实返回码，不猜坐标不修改权限；未更新时不写板，更新后按本轮已核依据恢复，结果未知先只读查明
场景: 证据或恢复不完整
  测试: toutiao_host_launcher_observation
  假设回调未到达、原始记录缺失或恢复任一项未知
  当汇总结果
  那么记录unknown/not reached与task_pass=false，证据完整检查成功不能替代设备任务通过，不将证书指纹或目录UID替代要求的前后清单
## 排除范围
白屏策略修复、自动拉起、视频声音复验、第三方崩溃诊断、原神、其他板部署与封板。
