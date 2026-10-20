spec: task
name: "Reproduce deployed bridge and build single AudioTrack getter"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t18-audiotrack-effective-size]
tags: [audio, production-build, offline, human-review]
---
## 意图
从已找到的原52对象及实际生产链接记录复现d4fa，再仅重编AudioTrack owner加入已审getter，预计移走toutiao的JNI异常墙；不把构建成功当声音或播放成功。
## 已定决策
- 原bridge基线必须重链得到精确d4fa。旧owner源必须等于原生产source pin8e922c5d。
- 先以原385参数重编未改owner并逐ELF section对照bca071e6；本机工具链仅.comment版本字符串不同可独立审查，其余section必须相同，不改写.comment伪造一致。
- 候选复用T18同一getter和单项注册，保持其余owner源码原字节，其他对象和链接依赖逐SHA复用，原序不变。
- 先frozen门，所有原始argv/stdout/stderr/rc及失败/timeout都持久保存；实际compiler、隐式lld、头文件与所有link输入都登记SHA。
- 实际产物须ABI导出/依赖比较且独立审核。构建不改变任何板；缺源闭包逐项列unknown，不升级成全源重建或实板验证。
## 边界
### 允许修改
- benchmark/2026-10-20-t18-audiotrack-production/**
- specs/toutiao-video-playback/t18b-audiotrack-production.spec.md
- tools/spec-checks/tests/toutiao_t18b_audiotrack_production.rs
### 禁止
- 不修改已交T18源码级记录、冻结源码、旧对象、设备、主树；不推送。
## 完成条件
场景: 基线与原对象核对
  测试: ttvideo_t18b_audiotrack_production
  假设 原bridge对象与工具链输入已pin
  当 复核保存的真实构建原件
  那么 基线重链为d4fa且旧owner仅允许独审.comment差异，其他section相同
场景: 候选单对象与ABI
  测试: ttvideo_t18b_audiotrack_production
  审核: human
  假设 基线已核准且getter边界测试已通过
  当 审核实际候选的source/对象/链接记录及ABI结果
  那么 仅AudioTrack对象变化而其余链接对象逐SHA相等，未出现未解释导出/依赖漂移，不声称播放完成
场景: 未完成构建不冒认
  测试: ttvideo_t18b_audiotrack_production
  假设 编译失败或timeout或原件缺失
  当 校验构建回执
  那么 原始失败输出保留且状态非通过，不产生可部署结论
## 排除范围
- 设备操作、随机退出、其他JNI API、ANW修复和实际音频验收。
