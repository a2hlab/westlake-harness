spec: task
name: "T91 read-only timestamp candidate deployment preflight"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t89-host-lifecycle-latency]
---
## 意图
与T90候选开发并行准备一份可复核的单变量验证/回滚方案，优先空闲5cd，不打断61b现有演示。只做元数据和已有部署机制核验，不部署或试启动。
## 已定决策
- CC唯一设备读取者，仅白名单61b0657200000000000000000324012c和5cd1e3dd00000000000000000923012c。先holder/boot；有他人holder停止该板。读设备当前init配置的启动root以及已知root/当前boot的real-spawn.sh stat/SHA，不读取watchdog/reentry内容。原207字节入口SHA46337ba8前缀；新对象不符就报告差异，不套用61b路径。
- 只读独立real-spawn.sh、members.tsv或同等部署清单、当前init配置以及已入库部署/回滚工具的接口。不得执行包中命令、创建文件、改trace/电源/设置，或读取故障转储/内存。不能证明部署程序怎样更新清单则写缺口，不绕清单检查。
- 离线给具体部署对象、原SHA/权限/owner/SELinux、启动副本是否每次执行、部署验证入口、回滚入口；从已有已验证部署机制复用，不手写未知生产写命令。5cd具备相同入口且空闲才列为首选候选板，61b保持现场。
- 最多4分钟首交，至多一页+results.json。记录完整只读命令argv/时段/rc/stdout/stderr到持久目录，检查正文错误；任何权限拒绝不换入口重试。
## 边界
### 允许修改
- benchmark/2026-10-23-spawn-request-timestamp/preflight/**
- 私有 $HOME/.local/share/westlake/spawn-request-timestamp-preflight-20261023/**
### 禁止
- 任何设备写入/部署/启动/重启、读取此前拒绝脚本、配置/数据修改、进程/网络操作、其他板
## 验收标准
场景: 入口与既有部署机制可核
  审核: human
  测试: timestamp_deployment_preflight_review
  假设无他人holder且入口元数据可读
  当只读核对root/boot副本与已验证部署工具
  那么列具体对象和保留检查的部署/回滚入口及SHA，方案可复核但没有执行
场景: 对象不符或机制不明
  审核: human
  测试: timestamp_deployment_preflight_review
  假设对象不存在、来源不同或清单更新机制未证
  当读取失败或4分钟截止
  那么报告缺口不猜路径、不执行写入，保留61b演示
## 排除范围
部署、设备复现、修改监督器、故障归属与封板签认。
