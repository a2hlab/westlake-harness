spec: task
name: "Build dedicated SurfaceView geometry candidate from exact947 source"
inherits: project
---

## 意图

读T4已有具体链路，以最小BBQ分支delta构建完整runtime候选；用实际函数离线负例和原工具冷构建闭合来源。

## 已定决策

- 记录child获取成功结果，不能只按SurfaceView字符串决定requested，fallback main保持panel。
- 不恢复全局seed，另外三几何函数与lazy实现和NOLOAD/M1owner/SQLite完全沿947。
- 复用原cold prepare/container/clang和严格link；源码独立替换recipe单一TU路径，不写兄弟工作树。

## 边界

允许修改: benchmark/2026-10-13-runtime-surfaceview-split/**、specs/runtime-surfaceview-split/**、tools/spec-checks/tests/runtime_surfaceview_split.rs、README.md、.octos/KNOWLEDGE-DIGEST.md。
禁止修改: 兄弟源码、现存运行时、已冻包、设备、私有app数据、原构建工具。

## 验收标准

场景: 专属child与main及失败fallback实际函数分流
  测试: runtime_surfaceview_split
  假设 专属child和main是不同window且child获取可成功或失败
  当 抽取候选真实BBQ函数进行host编译并执行三分支
  那么 仅成功专属child使用requested而main和失败fallback使用1200x1920
  并且 lazy与STAGE0 preserve及width0几何保持不写回

场景: 完整runtime冷构建与来源闭包
  测试: runtime_surfaceview_split
  假设 原6347输入/源archive/clang/container与严格recipe均逐SHA匹配
  当 原工具构建只替换一个候选geometry TU
  那么 原始rc0日志绑定候选ELF与全部源码recipe工具链
  并且 保留787导出和四个GLOBAL真实SQLite/CursorWindow注册器

场景: 预测保留主层反例与动态待验
  测试: runtime_surfaceview_split
  假设 Boat旧947同时更新main和child而popup有三项控件回退
  当 输出分支预测表与候选冻结回执
  那么 Boatmain变化明确待AB且不声称UI或交互PASS
