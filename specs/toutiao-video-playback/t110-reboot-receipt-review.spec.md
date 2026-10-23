spec: task
name: "T110 software reboot first-tap evidence review"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t108-spare-board-boot-entry]
---
## 意图
独立核T108及随后T109实际重启与首点证据，区分采样时间、真正启动和上屏，减少外环串行等待。
## 已定决策
- Codex离线读取T108持久原件及T109新原件，先核旧轮boot/reboot/click/screenshots/还原回执。新轮未结束可交已核旧轮，不能把缺件当失败或杜撰新轮成功。
- 读取真实文件发现结构，按rc和stdout共同判重启、new boot、点击次数，截图实际时间相对点击命令区间，facts由record重算；首个正图仍由外环目读。只比连续两轮软件启动表现，不归因未测因素。
- 五分钟首交，不设备调用、不REA、不权限变更、不读取停止对象。输出机器可读对照和简短英文README，写明未覆盖项；工具可复用既有checks，不重写大框架。
## 边界
### 允许修改
- benchmark/2026-10-23-reboot-repeat-review/**
### 禁止
- 设备操作、运行时部署、改原件、停止对象、私有信息发布
## 验收标准
场景: 新旧轮回执完整
  审核: human
  测试: reboot_repeat_evidence_review
  假设不同boot的真实点击及截图回执已到齐
  当独立核对身份次数和时间
  那么分别输出实际结果和差异，采样上界不冒充首帧时间，保留外环视觉验收
场景: 新轮未结束或缺少原件
  审核: human
  测试: reboot_repeat_evidence_review
  假设原件缺失、窗口在运行或rc与正文不符
  当形成阶段报告
  那么只采认已核事实并标pending或unknown，不声称新轮失败或成功
## 排除范围
物理断电保证、白屏根因归因、改运行时、音频验证。
