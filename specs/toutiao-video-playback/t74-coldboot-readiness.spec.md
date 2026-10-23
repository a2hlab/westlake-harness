spec: task
name: "T74 cold-power demo readiness and launch delay audit"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
用户明确要求61b真实断电开机后，首次普通桌面头条点击进入真实信息流，不能以同boot重开或reboot替代。先用已部署的自有开机/启动脚本和现成普通事件定位首次启动依赖以及T72约31秒点击到spawn等待，给出最小可执行候选和物理断电验收准备。
## 已定决策
- 先核T70的10件源码映射，再读已存在T68/T72的普通boot/guardian事件；禁止打开T71 faultlog或进行其已停止的内存破坏/第三方安全归因。只研究自有shell控制流、poll周期、前台判断与启动依赖。
- 限时8分钟首交机器可读分段时间线、来源file:line及确定/未知结论。不将约31秒相关性直接称为sleep根因，不重启或修改板子。源码检查用本地已验实现优先。
- 若发现自有启动脚本可确定的等待或开机依赖缺口，候选写独立目录并保留原件，给出离线针对性检查/部署回退入口；不改冻结文件，不未经复核部署。无法定位则交一个最小运行观察方案，不循环静态猜测。
- 最终冷启动标准为实际断供后开机，不依赖Mac手动bootstrap/重新部署，网络自动接上后普通图标首点显示信息流。点击到feed希望5至10秒，当前是优化目标而非已承诺能力。保留首次失败，禁止靠多次重试掩盖；断供证据不能用HDC断连替代。
- 只commit不push；本卡交分析和候选，不签冷启动通过。截图审核human；没有自动测试实现时不得声称lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-coldboot-demo-readiness/inner/**
- benchmark/2026-10-23-coldboot-demo-readiness/candidate/**
- 私有$HOME/.local/share/westlake/coldboot-demo-readiness-20261023/**
### 禁止
- 修改已部署运行时、任一板写操作、第三方崩溃与反虚拟化分析、已有原始记录覆盖、其他agent文件
## 验收标准
场景: 现有脚本能解释等待或开机依赖
  审核: human
  测试: coldboot_readiness_evidence_review
  假设已有T70源码映射和T72普通事件
  当按真实调用顺序检查开机恢复与点击等待
  那么分段时间线每个结论均有原件或源码行引用，候选另存并给离线检查与回退路径，未上板不标通过
场景: 证据不足或出现权限失败
  审核: human
  测试: coldboot_readiness_evidence_review
  假设现有文件不足以解释延迟或工具拒绝
  当到达8分钟边界或权限拒绝
  那么保留unknown和原始失败，交最小后续观察方案，不换上下文绕过拒绝，不重复猜因
## 排除范围
随机崩溃归因和修复、原神、全量APK、自动切断未确认的供电设备、本卡部署或冷启动签认。
