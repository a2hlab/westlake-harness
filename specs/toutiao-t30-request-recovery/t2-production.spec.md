spec: task
name: "T30 two-unit production preparation"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-recovery]
---
## 意图
在t1候选冻结和离线复核后，以T29实际生产输入重编window_module.c与provider_adapter.c并链接T30 shim。当前任务只准备可复跑入口和精确清单，首个Request失败根因及运行时切换结果仍UNKNOWN。
## 已定决策
- 默认只输出JSON预览且不启动编译器、不建立产物目录；--execute必须同时提供外环冻结manifest、R14与R15两个源码的各自实际SHA及review原件SHA。
- 编译argv沿T29实际r14和T28实际r15命令，仅替换source/output/dependency输出路径，R15增加MD/MF依赖原件；链接沿T29实际shim命令，仅替换r14.o、r15.o和输出路径，其余对象、脚本、sysroot库及工具均钉SHA。
- 先对原对象重链接复现9f3cecde，再编译两个TU；bridge b0e5602a只逐字复制。成功候选必须保留78个非空动态定义及NEEDED、无TEXTREL，三versioned入口唯一；新offset从实际候选提取。
- 每个执行命令原始argv/stdout/stderr/rc写到新的持久目录；编译依赖闭包不得引入未冻结头；失败保留INCOMPLETE且不自动重试、不部署。
## 边界
### 允许修改
- benchmark/2026-10-20-t30-request-recovery/production/**
- specs/toutiao-t30-request-recovery/t2-production.spec.md
- tools/spec-checks/tests/toutiao_t30_production.rs
### 禁止
- benchmark/2026-10-20-t29-window-observation/**
- benchmark/2026-10-20-t30-request-recovery/pinned-src/**
- knowledge/frozen/**
## 完成条件
场景: 默认预览没有执行副作用
  测试: ttvideo_t30_production_prepare
  假设 候选源码尚未冻结
  当 无execute调用入口
  那么 stdout输出PREVIEW_ONLY及双TU计划，不调用编译链接工具也不创建候选输出目录
场景: 未冻结与内容漂移拒绝执行
  测试: ttvideo_t30_production_prepare
  假设 缺少冻结manifest或source/review/任一基线输入SHA不符
  当 请求execute或验证冻结输入
  那么 非零退出并明确拒绝原因，编译器调用数为0，不产生可部署候选
场景: 双TU与原对象闭包明确
  测试: ttvideo_t30_production_prepare
  假设 读取已验证T29实际compile/link命令与精确输入清单
  当 检查production recipe
  那么 编译目标为window_module.c和provider_adapter.c，链接仅r14.o与r15.o可替换，bridge与其他对象保持各自原SHA，工具和隐式libc/libdl输入均非空且有真实hash
场景: 执行原件与新产物需外环审核
  测试: ttvideo_t30_production_prepare
  审核: human
  假设 外环冻结t1候选并另外组织真实构建
  当 执行两个TU编译链接且成功退出
  那么 原始命令回执及输入输出SHA可审阅，ABI78和NEEDED与基线一致且三槽偏移取自新ELF；预览和离线fixture不算真实构建成功或上板授权
## 排除范围
当前不执行真实生产编译、不操作设备、不修改CC候选实现、不调查首Q错误、不更新API冻结或宣称运行时恢复。
