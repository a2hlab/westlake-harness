spec: task
name: "T107 current 61b ordinary desktop entry"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t106-cross-board-startup-inputs]
---
## 意图
确认61b当前现存头条实例的普通桌面入口是否可供演示，保留现有可用进程，不将本次暖返回当作修复或断电保证。
## 已定决策
- CC唯一61b执行者。fresh held/boot/power/ps，现有child身份与前序T106绑定；进程不存在、holder冲突、读取失败停止，不启动替代实例或换板。
- 独占锁下正常唤醒并解无凭据锁屏；先截图当前画面。能显示已有头条界面才Home→按当前完整布局定位头条图标→一次普通点击；采5/20/30秒图和进程身份。初始白屏则停止点击，不丢失初始现象。
- 三分钟停止观察，五分钟恢复原power参数并释锁。保持信息流画面，不点新闻/视频，不杀进程/重启/部署/改网络。record/facts取实际，原件持久保存。
## 边界
### 允许修改
- benchmark/2026-10-23-current-demo-entry/**
- 私有 $HOME/.local/share/westlake/current-demo-entry-20261023/**
### 禁止
- 5cd/5ea操作、进程终止、部署、网络改变、停止对象、应用数据
## 验收标准
场景: 当前实例普通桌面返回
  审核: human
  测试: current_demo_entry_review
  假设fresh读检确认现有目标child且唤醒显示头条
  当普通Home和一次新布局图标点击
  那么报告实际截图和是否同child回到信息流，恢复power释锁，不签冷断电
场景: 初态异常或身份缺失
  审核: human
  测试: current_demo_entry_review
  假设初态白屏、凭据锁屏、holder冲突或child缺失
  当达到停止条件
  那么保留真实现象并停止后续点击，完成必要恢复而不制造成功
## 排除范围
随机崩溃预防、白屏修复、冷启动封板、新闻与视频交互。
