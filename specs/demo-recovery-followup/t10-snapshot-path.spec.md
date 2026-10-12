spec: task
name: "Route B snapshot capture in the OH permitted directory"
inherits: project
depends: [t9-child-readiness]
---

## 意图

修复 r3 守护程序将截图写入状态目录而被 OH snapshot_display 确定拒绝的缺陷。新 boot 52533 的原始 snapshot.log 指明只能写入 /data/local/tmp；身份守卫与自动重试已经运行，采图路径不得继续阻断画面判定。

## 已定决策

- 复用本仓已验证的 snapshot_display 临时目录方法，在 /data/local/tmp 下创建本次运行独占的非符号链接目录；已有或未知目录拒绝复用并保留。
- 只有本次命令成功、输出为新生成的非空普通文件且归档读回一致时才交给原分类器；旧图、命令失败、空图、链接、复制或读回失败不能发布 READY。
- 采图失败保持 UI_UNVERIFIED 或明确 I/O 失败，不对存活子进程或父进程发信号，不清用户数据、历史 stop 或未知临时目录。
- 保留 r3 的成功零编码、2 秒期限、完整身份守卫、原重试上限与退避；在新独立目录交件并刷新受影响发布 SHA，旧冻结字节不变。

## 边界

### 允许修改
- benchmark/2026-10-12-snapshot-path/**
- tools/spec-checks/tests/recovery_snapshot_path.rs

## 验收标准

场景: 允许路径的新截图归档后使用原分类器
  测试: recovery_snapshot_path_success
  假设 截图工具只接受 /data/local/tmp 下新建的独占目录
  当 候选成功采集非空普通图片并归档读回一致
  那么 原分类器仅收到本次新图片且发布绑定逐项匹配并保留原身份和重试判据

场景: 未知目录和异常图片不能误报通过
  测试: recovery_snapshot_path_reject
  假设 目录已存在、符号链接、命令非零、缺图、空图或旧图等负例
  当 候选尝试采图
  那么 每项拒绝使用图片且无 READY、应用信号、未知文件删除或用户数据变化

场景: 归档和清理失败保留准确失败证据
  测试: recovery_snapshot_path_io
  假设 归档复制、读回或本次自有临时文件清理失败
  当 候选记录本次状态
  那么 不发布成功回执且证据指出失败步骤并保留父进程、子进程和历史 stop

## 排除范围

- 内环板访问、重启、签字、随机 SIGSEGV 修复、修改分类器阈值、放宽原封板验收或生成模拟生产锁。
