spec: project
name: "Deployment SELinux label recipe"
---

## 意图

将 PR03 与 cc-wiki v2 的已证标签配方变成只读审计与默认启用的启动前拒绝门。

## 约束

- 本次只在本机使用夹具，不连接板、VM、SSH，不改安全策略或执行 setenforce。
- 审计器只读；打标只能由已有部署器的受锁与 boot 守卫保护的 shell 执行。
- 标签门不证明 app 点亮，不替代字节、native 票据、截图和 seccomp 门。

## 边界

### 允许修改
- scripts/lab/selinux_label_audit.py
- scripts/lab/selinux_label_recipe.sh
- scripts/lab/test_selinux_label_audit.py
- scripts/lab/deploy_generation.py
- knowledge/gates/selinux-label-recipe.json
- specs/selinux-label-recipe/**
- tools/spec-checks/tests/selinux_label_recipe.rs
- benchmark/2026-10-10-selinux-label-recipe/**

## 排除范围

- 实际部署、标签修改、重启、board 锁、自动恢复、seccomp 配置与点亮签认。
