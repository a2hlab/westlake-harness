# V2 演示操作页（候选草稿，128待审，未签认）

本页描述本轮已真实完成的有限动作，不把本页当部署授权、最终演示应用清单或封板签字。普通应用集合待本轮61b完整128逐项图审后填入新签认文件的 `demo_set`；旧112、V1 Plan2或5ea回归数不挪用。当前已确认画面与动作可作候选演示；最终集合由outer据真实结果确定，失败项skip。本页不覆盖V1手册。

证据的便携路径与完整SHA在 `evidence-bindings.json`，下文方括号是其中 `references` 的键；已知限制全文在 `known-limits.json`。本轮实际板为61b，候选boot086db6c7，Boat UID20011207；这些是历史证据参数，不是下次启动的固定参数。

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

## 最终采集前由root确认前台

等待本轮128完全结束后，先按原补充卡 `[foreground_supplement]` 独立只读核当前imehost的Focus/PID/WMS；旧1053不是当前前台证明。必要时用原BMS桌面图标入口与capture恢复，root读真实截图；不自动同意隐私。随后先核run.sh实际完整SHA等于冻结824预期，才进入collector与最终自检链。来源/WID变化沿补充卡停止或以独立真实参数派生新审定输入，不能改expected、旧pin或跳门。具体顺序见本包 `FINALIZE.zh.md`，补充卡精确路径/SHA见证据表。此操作不与运行中的128并发。

## 一键只读自检（最终动态字段填齐后）

由root选用新最终seal对应的原realization，不用旧V1 proof或此前candidate954顶替。设置 `WORKSPACES` 为工作区父目录，`FINAL_PROOF`、`ACTUAL_BOOT`、`HDC` 与新输出路径来自最终签认；命令不执行恢复/安装。

```sh
MAIN="$WORKSPACES/westlake-harness"
bash "$MAIN/scripts/lab/demo_selfcheck.sh" \
  --realization "$FINAL_PROOF/realization.json" \
  --serial 61b0657200000000000000000324012c \
  --boot-id "$ACTUAL_BOOT" --hdc "$HDC" --out "$NEW_SELFCHECK_JSON"
```

原wrapper显式路由到binary-safe R5 collector。不能传 `--observed` 后称实时自检；新boot/WID变化须按原独立host/WMS参数证据精确派生，不能从run.sh倒读猜WID。自检FAIL则停止本次演示并交outer处理，不能跳SHA门。[selfcheck_wrapper, binary_selfcheck, realization]
