spec: task
name: "Propagate accepted host page to the 61b demo device"
inherits: project
depends: [t3-root-host-update]
satisfies: [REQ-TTVIDEO]
---
## 意图
将5cd已接受的无开发控件宿主页同步到用户指定的61b演示机，正常图标自动打开真实头条信息流；以61b自己的当前态为保存和回退依据。
## 已定决策
- 本任务显式扩展project的5cd范围，仅root可操作61b0657200000000000000000324012c；内环继续零设备调用。5cd和5ea不动。
- 候选沿用T32 b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0。先核61b真实HAP、cert/profile、全部成员和启动链；不因同名包就安装。原件不等价时先做差异审查，不照搬5cd身份参数。
- 当前61b的UID/token、数据目录、运行库、guardian、图标与其他演示app保持本窗前态；不宣称同步视频修复。只允许同签bm install -r -p覆盖，不卸载不清数据。旧HAP及原始操作回执保存到持久目录。
- 复用T32的最小执行路径，按61b实读参数核对，不重建运行时、不修改guardian。重启仅正常重启；如原启动链按WID派生run.sh，允许该原有字段派生，其余字节保持并记录。
- root取得新板锁和fresh状态后开窗，1200秒前决定retain或回退，最迟1800秒恢复电源/debug原态、解锁。失败覆盖回本窗原HAP，核身份/运行时与真实feed；缺图则明确恢复未完整。
- 图标验收以实际早期及最终截图判定：无开发标题和输入框，自动进入真实feed。不以READY或存活替代截图，不承诺秒开，不诊断头条随机崩溃，不再次询问声音。
- 交件补API观察记录、源码/配方/实际设备关联；不改315历史语义，不推送远端Git。
## 边界
### 允许修改
- specs/toutiao-launcher-transition/t4-demo61b-host-update.spec.md
- benchmark/2026-10-20-t33-demo61b-host/**
- benchmark/2026-10-19-api-progress-update/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md
- root独占61b同签宿主HAP安装、正常启动验证、恢复及原始持久证据。
### 禁止
- 5cd/5ea设备操作、卸载/清数据、运行库或guardian源码更改、修改历史签认、推送。
## 完成条件
场景: 精确61b原包匹配与身份保存
  测试: launcher_page_closure
  审核: human
  假设 61b只读原包和T32签名成员对账一致且旧包持久备份
  当 root持锁进行同签覆盖并读取实际bundle及目录状态
  那么 UID及token和目录身份保存，运行库指纹等于61b本窗前态，其他app不变
场景: 一次图标进入真实信息流
  测试: launcher_page_closure
  审核: human
  假设 正常重启且fresh宿主与parent身份和WID链相符
  当 root一次点击真实桌面头条图标并采早期和最终图
  那么 开发控件消失且最终为真实feed，等待时长如实报告
场景: 不匹配或视觉失败回退
  测试: launcher_page_negative
  审核: human
  假设 原包签名不匹配或覆盖后身份漂移或1200秒内视觉未过
  当 root停止实验并执行本窗原包回退
  那么 未安装则保持原态，已安装则恢复精确原HAP并核原身份和运行时，缺feed不宣称恢复完整
场景: 真实有界收窗与可追溯交件
  测试: launcher_page_closure
  审核: human
  假设 原始命令回执与窗口起点存在
  当 root作出retain或回退决定后恢复电源并解锁
  那么 记录实际时长及判词并关联API表，超时如实保留，原始证据持久保存
## 排除范围
视频候选跨板迁移、所有app复验、启动性能优化、随机崩溃修复、重新构建HAP、重新冻结公共API。
