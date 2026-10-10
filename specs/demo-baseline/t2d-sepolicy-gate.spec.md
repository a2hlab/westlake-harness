spec: task
name: "Offline sepolicy gate for the SELinux label recipe"
inherits: project
---

## 意图

标签配方里每一条是否正确,由板上真实策略离线证明,不靠上板试。策略只拉一次存作证据,每条配方附一条 sesearch 证明,配方或策略变动时自动重查。2026-10-10 61b 重启后连撞 EACCES(入口点类型错)与 exit 127(appspawn 域不能 map data_local_tmp),两堵墙用这份策略离线都能一次查出。

## 已定决策

- 策略证据:三板 `/sys/fs/selinux/policy` SHA 相同 `7d23015f5e494b47044f3bfba7545789c20525aecb4c3b6b743aa77e97d764f0`(OH 6.1.0.31,526 KB,policy v31),原件在 `$WORKSPACES/westlake-inputs/sepolicy/oh-6.1.0.31/policy`,仓库只记路径与 SHA,不提交二进制。
- 查询工具:OrbStack `a2hlab` 里的 setools 4.4.4(`orb -m a2hlab sesearch …`,外环已装);不在 Mac 上另装。
- 配方唯一事实源 `knowledge/gates/selinux-label-recipe.json`(cx-bms 在做);本门只读它,不写它。配方未落地前用夹具配方(今天四条已知:appspawn-x=appspawn_exec、/system/android/lib64=system_lib_file、/system/android 其余=system_file、/system/lib64/seccomp=system_file 原厂值)。
- 每条配方要证明的规则按用途选:入口点(`-s <domain> -c file -p entrypoint`)、加载(`-s <domain> -c file -p map,read,open,execute`)、路径可见(`-s <domain> -c dir -p search,getattr` 与 file getattr);域取自 cfg 的 secon 与 app 子进程域。
- 已知答案测试必须包含今天两个反例:appspawn 对 system_file 无 entrypoint、对 data_local_tmp 无 map。

## 边界

### 允许修改
- scripts/lab/sepolicy_gate.py
- scripts/lab/test_sepolicy_gate.py
- knowledge/gates/sepolicy-evidence.json
- benchmark/2026-10-10-sepolicy-gate/**
- tools/spec-checks/tests/demo_baseline.rs
- specs/demo-baseline/**

### 禁止
- 上板写操作;修改配方 JSON;提交策略二进制。

## 验收标准

场景: Every recipe entry carries a passing policy proof
  测试: demo_baseline_sepolicy_gate
  假设 The pinned policy and the recipe JSON
  当 sepolicy_gate.py runs
  那么 Each entry prints the domain the label and the matching sesearch allow rule and the gate exits zero

场景: Known wrong labels are rejected
  测试: demo_baseline_sepolicy_gate
  假设 A recipe that labels appspawn-x system_file or leaves a library data_local_tmp
  当 The gate runs
  那么 It exits nonzero naming the entry the domain and the missing permission

场景: Policy or recipe change forces a recheck
  测试: demo_baseline_sepolicy_gate
  假设 The recorded evidence was computed for an older policy SHA or recipe SHA
  当 The gate runs
  那么 It recomputes every proof and refuses to reuse the stale evidence

场景: Missing query tool fails closed
  测试: demo_baseline_sepolicy_gate
  假设 sesearch is unreachable or the policy file SHA does not match the pin
  当 The gate runs
  那么 It exits nonzero with the reason and reports no entry as proven

## 排除范围

- 生成或改写配方;改 deploy_generation.py 或开机自启脚本(另有 cx-bms 与 cc-wiki)。
