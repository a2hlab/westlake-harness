spec: project
name: "Toutiao ordinary host window recovery"
satisfies: [REQ-TTHOST]
---
## 意图
恢复演示机正常桌面打开和最近任务关闭后重开的头条信息流，保留已验证的输入、绘制和视频行为。诊断、源码绑定和离线测试通过均不是封板完成。
## 约束
- 以实际截图与正常触控验证；主机新建、子进程存活、窗口dump或脚本PASS不能替代可操作的信息流。
- 修改前核现役产物、源码/工具链和构建配方；不将候选Java快照替代更晚的现役DEX。
- 同一host前后台不重建producer；host更换后的session恢复必须覆盖身份、窗口关联、surface与输入一致性。
- 单板单写者，先只读检查、持锁、备回滚；运行时构建保留原stdout/stderr/rc及SHA，冻结项按既有规则处理。
- 拒绝判断必须绑定具体请求与实际证据：历史CC的reasoning_extraction标签不证明设备命令本身被拒，不把支持工单回复设为所有后续开发或验证的统一前置。正常独立任务按实际条件推进；不索取模型内部推理，不为绕过明确拒绝而换模型/入口重试同一请求，不读取停止的控制器/执行器/配置，不修改安全约束。
- 源码、构建配方、API记录与实测证据进入实际主干master；软件重启和物理断电证据分别标注。
## 问题
- 原RSSurfaceNode/producer是否能通过正常SSM新子会话复用，或必须协调Java与EGL重建？待当前双车道源核结论。
- host窗口实例记录的child侧读取资格尚需实际执行证明；root通过/proc/PID/root看到同一inode不是child读取成功。
