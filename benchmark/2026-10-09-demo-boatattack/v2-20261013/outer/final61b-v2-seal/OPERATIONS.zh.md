# V2 演示操作页

实际封板状态与精确证据以同目录 final-signoff.json 为准。本轮61b已完成128项首屏比较、Boat方向/加速/复位/LAP0→1及头条feed/文章/返回/画面刷新；普通应用115项仅首屏展示、13项排除，详见[实际演示清单](../../../../2026-10-14-final61b-full128-outer/demo-list.json)。不代表完整功能、整圈比赛或长期稳定。

原证据键对应原[证据索引](../../integration/final-v2-operations-draft-r2/evidence-bindings.json)；本文补充[前台对象纠正](../../integration/final-foreground-object-review/NOTE.zh.md)：Focus属于同目标UID的头条子进程合法，宿主WID保持33；不能把焦点WID30写入run.sh。

## 开场与普通应用

1. 正常开机，等待原U13启动完成；本轮receipt为READY56、Boat BOUND7。它们只证明底座/挂载准备，不证明应用上屏。不要为演示重新安装、清数据或手工bind。
2. 普通app从桌面真实图标启动；systemdaemon按需激活，刚开机尚无parent不是需要人工修复的错误。不要手工启动或杀system父进程。
3. 看真实截图/屏幕，等本应用界面稳定。首屏、菜单、空态、引导页按最终128审定说明展示，不宣称全部功能可用。HW/ZZ本轮控制截图已审，但不替代128结果。[primary_stage_completion, primary_controls_review, prior_runbook]
4. 黑屏、无响应、异常裁切或崩溃：记录当前画面和应用名，回桌面，跳下一项；不现场改运行时、重装或修墙。不要把alive/READY打印当画面PASS。

## BoatAttack：已验证的有限操作

从桌面进入Boat，确认场景正常、圆形HUD、1920×1200实际游戏画面。顶部状态栏遮挡部分HUD仍是限制。方向和LAP应由图像确认，不能用船自然漂移替代转向证据。[boat_review, root_scoped_ui]

| 操作 | 已批准的源码派生参考命中（1920×1200） | 演示判断 |
|---|---|---|
| 左转 | 左摇杆中心154,1046拖至49,1046 | 比较操作前后船头方向；不把自然移动当响应 |
| 右转 | 同中心拖至259,1046 | 比较操作前后方向；水中静止也可转向，搁浅可能不响应 |
| 加速 | 右侧圆控1794,1074 | 短按后看实际位移；本轮加速驶上岸，不能承诺连续驾驶稳定 |
| 复位 | 圆控1584,1074 | 本轮同child回到水中；旧1440,1100在命中框外，不沿用 |

这些是布局实参参考，不是跨尺寸盲点坐标。画面尺寸或控件位置不符则skip，不猜新坐标。本轮原组已见LAP0/3→1/3；等待整理证据超过240秒后原组超时，原件保留。独立续接在同child17734/birth46774下完成 `right→right→left→accelerate→reset`。不能把两组拼成“原序列一次全PASS”，也不宣称完成整圈、比赛、帧率或长稳。[boat_partial, boat_resume, boat_review, control_layout, control_engine, control_boat]

演示按实时画面短步操作；方向不对先看图，搁浅可用真实复位控件，失败即skip。复位是已有补充证据，不新增成原t2b的硬门。不要求重新跑历史cadence来重验已经审定的动作。

## 今日头条：按图判READY，尊重隐私等待

1. 从桌面普通图标进入，等待现有自动恢复；默认最多3个child attempt，不是固定秒数或成功承诺。保留原parent，不人工补runtime。历史随机SIG11未证明修复。[prior_runbook]
2. 出现登录推广可由操作者按可见关闭控件退出；本轮未填手机号、未登录、未勾同意。出现隐私协议则交用户自行选择，不自动同意、不借关闭推广冒称已同意隐私。5cd目前隐私等待事实仍保留。[root_scoped_ui, spare_completion]
3. 实际信息流可见后，点一条真实文章，查看正文，返回原信息流，再下拉刷新。本轮已见内容变化；只证明画面改变，不证明网络实时性。[toutiao_review]
4. 文章灰色插图占位与右侧文字裁切仍在；出现这些情况如实说明。无feed、反复异常或自动恢复停止则skip；不要登录、clear数据、杀parent或手动启动来伪装自恢复。

## 一键只读自检

本轮新seal对应的原realization已经完成实时954项PASS。再次只读检查时设置 `WORKSPACES` 为工作区父目录，`FINAL_PROOF`、`ACTUAL_BOOT`、`HDC` 与新输出路径来自最终签认；命令不执行恢复/安装。

```sh
MAIN="$WORKSPACES/westlake-harness"
FINAL_PROOF="$MAIN/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final61b-v2-realization/proof"
# ACTUAL_BOOT 取当前设备真实boot；NEW_SELFCHECK_JSON为新输出路径。
bash "$MAIN/scripts/lab/demo_selfcheck.sh" \
  --realization "$FINAL_PROOF/realization.json" \
  --serial 61b0657200000000000000000324012c \
  --boot-id "$ACTUAL_BOOT" --hdc "$HDC" --out "$NEW_SELFCHECK_JSON"
```

原wrapper显式路由到binary-safe R5 collector。不能传 `--observed` 后称实时自检；新boot/WID变化须按原独立host/WMS参数证据精确派生，不能从run.sh倒读猜WID。自检FAIL则停止本次演示并交outer处理，不能跳SHA门。[selfcheck_wrapper, binary_selfcheck, realization]
