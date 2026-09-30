spec: task
name: "T6 板上短窗验证新镜像"
inherits: project
depends: [t5-boot-image]
tags: [dex2oat, board, l2]
---

## 意图

在一块空闲板上叠加 T5 的 27 个文件(板上现役 libart 不动),验证 app 不再在 CheckSystemClass abort,HW、ZigZag 与至少 5 个当前已亮 app 在 t20 仍显示自身界面;结束卸载回 U2。

## 已定决策

- 叠加前先只读备份 27 个现役文件的哈希;appspawn-x 只用 begetctl stop_service/start_service 与 socket 属主修正
- abort 时当场拉回 /data/log/faultlog/temp/ 下的 cppcrash 原文再卸载

## 边界

### 允许修改
- benchmark/*-dex2oat-l2/**

### 禁止
- 不 kill -9 appspawn-x
- 窗口不超过 30 分钟;结束必须回到 U2 指纹

## 验收标准

场景: 新镜像下 app 正常启动
  测试: d6_board_accepts_image
  审核: human
  假设 一块持锁的空闲板叠加了 T5 的 27 个文件
  当 bms_batch 跑 HW、ZigZag 与 5 个 U2 已亮 app
  那么 facts.txt 无 CheckSystemClass abort,外环读图 7 个 app 在 t20 显示自身界面
  并且 结束后卸载回 U2,runtime fingerprint 为 937e2a6d0d88
