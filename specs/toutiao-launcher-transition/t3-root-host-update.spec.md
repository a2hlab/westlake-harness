spec: task
name: "Root-only exact host HAP update and reversible acceptance"
inherits: project
depends: [t2-host-page-candidate]
satisfies: [REQ-TTVIDEO]
---
## 意图
root在5cd独占短窗将已离线验证的最小页面HAP覆盖当前同身份HAP，正常重启后一次图标自动到真实feed且不显示开发控件，完整保留已签视频候选；内环只做静态支持。
## 已定决策
- 用户本轮明确授权root设备执行，作为project“仅本地”对内环约束的显式例外；内环仍零HDC/安装/重启/推送。不新增执行器或泛化测试，复用root已离线修核window_ops.py。
- 仅5cd1e3dd00000000000000000923012c。旧HAP df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a，候选 b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0；同cert/profile/versionCode2/API20，UID20011300。只允许bm install -r -p覆盖，零卸载、零清数据，不改运行库或guardian逻辑。
- 新holder/start与fresh boot/parent/host/child/birth/WMS均由root实采；前置备份旧HAP、bm完整身份与token、数据目录元数据、当前留板六态指纹及power。原T31 origin与备份保留，不以其旧基线替代当前候选指纹。
- 安装后核UID/token/appIdentifier、目录owner/mode/label及运行时保存；正常重启后用既有已根读boot-entry/config-common/real-start-parent-bounded的fresh WID单字段派生。不得猜29或只改admission；实际派生范围和其他run字节须符合原门，超范围停止并另审。每个新boot内核physical/private对应，跨boot不要求PID或inode原值相同。
- 一次正常图标，保留早期及最终截图，确认无开发控件和真实feed；再短视频视觉检查，声音复用用户已确认，不再逐片问。等待期间空背景不当加速或feed；仅安装/READY/存活不能代图。没有新随机退出诊断或反复重启碰运气。
- 全窗最多1800秒，1200秒前完成接受判断，否则开始留600秒恢复。失败仅覆盖回精确旧HAP并正常重启，核原HAP/UID/token/数据目录、当前已签视频六态指纹及真实feed；仍host-only或缺证据则如实记录恢复未完整。恢复目标是本窗前留板候选，不是stock运行时。
- 每次安装/回退保存真实远端rc和stdout/stderr，不将host transport rc冒充设备成功；结束恢复原power10000/10000、debug原缺失状态并释放锁。未知或foreign包不卸载/不强行覆盖；保留所有失败原件。
## 边界
### 允许修改
- specs/toutiao-launcher-transition/t3-root-host-update.spec.md
- benchmark/2026-10-20-toutiao-launcher-page-t3/**
- root独占设备窗的原始操作回执与明确授权的同身份HAP覆盖。
### 禁止
- 改t1/t2冻结文件、T31来源、运行库、app数据、其他板或app；内环设备命令、推送；新执行器/新通用测试框架。
## 完成条件
场景: fresh前像与同身份覆盖
  测试: launcher_page_closure
  审核: human
  假设 t2候选签名门通过且root持新锁取得fresh身份与本窗前像
  当 bm install -r -p执行并返回显式远端rc
  那么 同cert/profile/versionCode下UID和token及目录身份保存，六态运行时内容不变，零卸载零清数据
场景: 正常重启一次图标与视频保留
  测试: launcher_page_closure
  审核: human
  假设 安装核验通过且正常重启fresh WID由既有路径准确派生
  当 一次正常图标并取得早期和最终真实图及短视频视觉证据
  那么 开发控件不再显示且最终feed真实，已签视频行为保持，声音复用用户确认，不承诺零等待或加速
场景: WID漂移与未知身份拒绝
  测试: launcher_page_negative
  审核: human
  假设 fresh WID超已验派生范围或包foreign或token目录运行时漂移
  当 root检查实际对象与原门
  那么 停止验收、不猜29、不绕门或卸载，保留原件并进入已审回退或明确范围外待审
场景: 失败覆盖旧HAP恢复
  测试: launcher_page_closure
  审核: human
  假设 安装或视觉核验失败且精确旧HAP回退件可用
  当 覆盖旧HAP并正常重启且执行原身份和指纹核验
  那么 原HAP和本窗前留板六态及目录token恢复，真实feed另核；缺feed不得宣称完整恢复
场景: 有界窗口与真实收口
  测试: launcher_page_closure
  审核: human
  假设 窗口真实start与全部原始回执可读
  当 到达1200秒判断点并最迟1800秒结束
  那么 未齐开始恢复，power和debug恢复后解锁，实际超时或恢复未完整均记录不倒签
## 排除范围
启动性能优化、跳过宿主、公共API冻结扩大、其他app、视频候选重建、逐片声音重新确认。
