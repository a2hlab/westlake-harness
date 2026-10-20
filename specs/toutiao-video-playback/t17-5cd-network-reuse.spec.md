spec: task
name: "5cd exact R9 networking configuration reuse"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t16-5cd-load-chain-reuse]
tags: [5cd, reuse, network, human-review]
---
## 意图
T16真实头条已越过IID装载墙而反复ff_listen_connect2=-97；复用R9两行配置，预计移走的key仅toutiao。保持原T16部署门禁及回滚，后续ANW采样独立，不把加载/绑定/封面当视频完成。
## 已定决策
- 仅5cd，T16须先实际恢复；新窗fresh身份/前像/当前WID须重核，旧parent/boot字段只作历史。使用T17新admission/apply-plan/backup/stage，不借T16或61b授权。
- run仅在R8之上追加NET_TARGETS libmffmpeg.so和INHERIT已有netcompat；三个R8运行库逐字复用，不重编/不改provider、不重复REA。5cd WID29参考run为11d3d671；唯一WID数字行派生仍按T16严门。
- 实际netcompat精确f6c354d1、UID20011300、label/物理private inode齐；源/配方存在但exact producing build closure仍unknown，不冒认构建可复现。INHERIT影响共享android_app namespace，不能宣称只影响media。
- 派生精确T16 executor05099f6c，仅新命名空间和netcompat只读hash/meta/inode守卫；preview默认、outer独立签源码SHA；保留30分钟窗/10分钟回滚预留、CAS、三备份先齐、foreign拒绝、no-parent仅物理恢复、freshboot后运行态与真实feed验收。
- 必须实际读新child两项GOT：media getaddrinfo/freeaddrinfo均到exact f6目标；使用已有PT_LOAD/对象SHA/dev:inode/前后maps方法，旧61b reader不可原样执行。误配/无法读取则unknown并恢复，不用映射存在替代winner。
- 网络错误及桥接进展由实际短日志判定；R9历史256条镜像耗尽后不能宣称无新错误。ANW/音频/动态两周期播放继续保持独立human门。
## 边界
### 允许修改
- benchmark/2026-10-20-t17-network-reuse/**
- specs/toutiao-video-playback/t17-5cd-network-reuse.spec.md
- tools/spec-checks/tests/toutiao_t17_network_reuse.rs
### 禁止
- 不改T16/已签源码/61b/provider二进制，当前作者不设备执行、不推送。
## 完成条件
场景: 精确两行和既有运行件
  测试: ttvideo_t17_network_reuse
  假设 R9原template与T16实际5cd模板及三个固定库
  当 离线派生与检查
  那么 只有两行路由差异，库字节无变化，preview零设备命令且CAS负面检查仍过
场景: 实际网络绑定与进展
  测试: ttvideo_t17_network_reuse
  审核: human
  假设 已独立准入且新child正常视频动作
  当 同身份同映射对象读取两GOT并取实际短日志
  那么 两项均匹配才声明绑定，后续首错误按原件记，不能宣称动态有声播放
场景: 原5cd恢复
  测试: ttvideo_t17_network_reuse
  审核: human
  假设 失败或进入回滚预留时段
  当 按本窗apply-plan恢复并freshboot
  那么 518+26同scope快照及原参数/power/兼容库缺席与实际图标feed核实，物理恢复不能直接判运行态恢复
## 排除范围
- 重新构建netcompat、修随机崩溃、新ANW实现、自动视频封板。
