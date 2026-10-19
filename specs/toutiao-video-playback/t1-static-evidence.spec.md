spec: task
name: "Toutiao video current-route static evidence"
inherits: project
satisfies: [REQ-TTVIDEO]
tags: [media, static, ready]
---
## 意图
将历史冻结封面记录与当前APK/运行时分开，输出下载、解码、视频Surface、音频、生命周期五段调用链和首致命点预测。为最小修复提供可定位的API与源码对象；暂不上板。
## 已定决策
- baseline来自外环只读采集的serial/boot_id/APK SHA/runtime逐件SHA，缺失时static-only，不编造当前部署。
- 复用scripts/lab/open_site_scan.py、deployed_class_diff.py、deployed_strings_diff.py；查宿主/child namespace、最后JNI注册方、dlopen实际消费者与Surface对象，而非只按符号存在判断。
- 查本地Westlake/00.Workspace/real-work/vm-copies，再a2hlab再hw248；每处记录命中或不可访问，并保留source commit/blob与配方路径。
- 以首致命点排序；网络/服务拒绝为external，缺证为unknown。ReliableSurface是HWUI包装，必须证明具体视频producer消费它才可升格根因。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/static/**
- specs/toutiao-video-playback/t1-static-evidence.spec.md
### 禁止
- 不调用设备写命令、不抢61b锁、不改native/JAR/API表或既有观测记录。
## 完成条件

### Rule: evidence-before-verdict — 先绑定证据再判断
场景: 五段媒体路径与首个失败证据
  测试: ttvideo_static_receipt
  审核: human
  假设 外环提供baseline的serial/boot_id/APK SHA/runtime逐件SHA与已有源文件
  当 按本地Westlake/00.Workspace/real-work/vm-copies、a2hlab、hw248顺序查源并写入prediction.json文件及关联证据哈希
  那么 五段路径逐项记录consumer/provider/namespace/API与source路径，确认或未知分开
  并且 修复清单只包含有证据预计移走首个致命点的key与精确文件
场景: 历史日志或网络失败不误判桥接
  测试: ttvideo_static_receipt
  审核: human
  假设 只有9月28日stub日志或当前视频请求被服务拒绝
  当 归因与预测
  那么 status为needs_observation或external_blocked且ReliableSurface/HWUI因果为unknown，不宣称当前Surface或codec根因
场景: 缺输入与多份provider拒绝
  测试: ttvideo_static_receipt
  审核: human
  假设 缺部署SHA或同名库在多个namespace有不同提供方
  当 生成派单
  那么 标明unknown和最小观测方案且不进入t2修复
## 排除范围
- 随机崩溃根因、安全机制改造、用户数据清理和自动远程推送。
