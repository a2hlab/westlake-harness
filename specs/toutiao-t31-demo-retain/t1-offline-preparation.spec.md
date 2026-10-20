spec: task
name: "T31 bounded offline preparation"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
给出可审的最小复用计划、现有提交和真实缺口。机器预演只校验固定候选、WID分支与计划结构，不产生fresh admission、不执行远程命令、不签认留候选。
## 已定决策
- preview.py默认只向stdout输出PREVIEW_ONLY、device_calls0、fresh字段null；--repo可指定MAIN，--wid仅作为离线分支输入，不证明现场值。未知参数和漂移以stderr及非零rc拒绝，不创建输出目录。
- fresh WID29且前像逐字等于5a3a参考时复用原executor/fill与两run模板。owner已20011300，不再执行20011206替换。其他WID返回WID_DERIVATION_REQUIRED，不自动生成执行件；未来只能另目录派生executor normalize/apply/template/rollback、fill及两模板并重钉自pins，不能仅改admission。
- 参数与源码取已落MAIN的T30 final-01/helpers；核本轮使用文件SHA，不运行旧候选测试。T31使用新输出根，不调用硬钉t30-5cd-window-01的acquire/launch助手。
- 原rollback有同holder/start和1800秒门，仅能原窗恢复。留候选前必须另审recovery-only继任入口：不可变origin apply-plan/backup哈希，与新鲜恢复窗口holder/start/boot/父身份分开绑定；保留原六态CAS/foreign拒绝/backup校验/跨boot精确run/WID集合、freshboot和518+26恢复，不伪造旧start或重写原plan。
## 边界
### 允许修改
- specs/toutiao-t31-demo-retain/**
- benchmark/2026-10-20-t31-demo-retain/**
- tools/spec-checks/tests/toutiao_t31_preview.rs
### 禁止
- benchmark/2026-10-20-t30-request-recovery/**
- knowledge/frozen/**
- 禁止设备调用、生产构建、共享主表改动及自动签字。
## 完成条件
场景: 默认预演无设备和输出目录副作用
  测试: ttvideo_t31_preview
  假设 T30精确来源存在
  当 以MAIN和未知fresh WID运行preview
  那么 输出PREVIEW_ONLY和null身份，device_calls为0且没有写输出目录
场景: 29与漂移WID不同处理
  测试: ttvideo_t31_preview
  假设 两模板owner已为20011300且参考WID29
  当 分别预演29与41及非法WID
  那么 29可列原样复用，41仅列需派生，非法值非零拒绝且不生成admission
场景: 源漂移和未知执行参数拒绝
  测试: ttvideo_t31_preview
  假设 executor或模板SHA漂移或传入execute参数
  当 运行preview
  那么 stderr列拒绝且非零退出，不调用执行器或设备
场景: 过期恢复与永久签认不能冒充已就绪
  测试: ttvideo_t31_preview
  假设 当前只有T30原rollback实现
  当 读取预演的recovery和retain状态
  那么 原窗恢复可复用而跨窗恢复继任待交，永久留候选为NOT_AUTHORIZED且两段音频与签字均pending；跨窗恢复只在独立t3完成后标OFFLINE_REVIEW_REQUIRED
