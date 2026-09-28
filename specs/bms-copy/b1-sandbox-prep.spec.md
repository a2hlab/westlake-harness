spec: task
name: "B1 批量安装补上沙箱准备"
inherits: project
tags: [bms, sandbox, cx-t0]
---

## 意图

条目 24 的同板 A/B 证实:批量安装后 app 拉不起,是因为缺了 restore 在 `bm install` 之后做的沙箱准备——AppSpawnX child 强制 bind mount `el1/100/database/<pkg>` 时 ENOENT,22 ms 后退出。本任务把 HelloWorld restore 与 ZigZag `prepare_sandbox` 的沙箱准备原样抄成按包名参数化的函数,接进批量脚本。

## 已定决策

- 函数照搬来源写明文件与行号:`bms/.agents/skills/reproduce-helloworld/scripts/reproduce.sh` 与 ZigZag `prepare_sandbox`;只改包名与 uid 参数
- 准备内容:10 个沙箱根目录、owner uid/gid、mode、SELinux label,以及逐项 chcon
- 执行时机:`bm install` 成功之后、桌面点击之前

## 边界

### 允许修改
- benchmark/2026-09-28-bms-route-deploy/**
- tools/spec-checks/**

### 禁止
- 不修改 APK
- 不改动 BMS 补丁库与共享运行代

## 验收标准

场景: Wikipedia 补上沙箱准备后进程存活并上屏
  测试: b1_wikipedia_lit_after_sandbox_prep
  审核: human
  假设 Wikipedia 已 `bm install` 且执行了沙箱准备函数
  当 从桌面点击它的图标并等待 15 s
  那么 该 app 的 BMS uid 下有进程持续存活
  并且 外环读图签认截图是 Wikipedia 自身界面

场景: 10 个沙箱根目录属性与 HelloWorld 一致
  测试: b1_sandbox_roots_match_helloworld
  假设 同一块板上 HelloWorld 与 Wikipedia 都做过准备
  当 比对两者 10 个沙箱根目录
  那么 每个目录都存在,owner 为各自 uid,mode 与 SELinux label 与 HelloWorld 同类目录一致

场景: 沙箱准备失败时不点击
  测试: b1_prep_failure_skips_launch
  假设 某个沙箱根目录创建或 chcon 失败
  当 批量脚本处理该 app
  那么 该 app 记 `sandbox_prep_failed` 并附失败命令与返回值
  并且 不对它执行桌面点击

场景: 准备函数可重复执行
  测试: b1_prep_is_idempotent
  假设 某 app 的沙箱已准备过一次
  当 再次执行准备函数
  那么 返回成功且目录属性不变

## 排除范围

- 名字与图标(见 B2、B3)
- 对 app 私有 native 库的补丁
