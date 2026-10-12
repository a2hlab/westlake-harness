# API version bindings — frozen 8 entries vs locally stored run evidence

Offline pass (2026-10-12, oc-t4): for every `knowledge/frozen/frozen.json` entry,
locate the local run directory, platform identity and artifact hashes, and grade
how directly the platform version binds to the registered APK evidence.

Binding strength rules (per t3-version-bindings.spec.md):

- **direct** — the same run that produced the registered verification carries an
  explicit platform-version string (e.g. the run's `contract.txt` pinning
  "系统保持 OpenHarmony 6.1.0.31,不刷机").
- **context_only** — the platform version appears only in a *different* run's
  identity record (`platform-context.json`, 5cd U13 2026-10-10). Background, not
  a same-run binding.
- **unknown** — no local version evidence at all (do not infer from AOSP tags or
  APK targetSdk).

## Results

| FZ | binding_strength | 系统版本 | 依据 |
|---|---|---|---|
| FZ-001 | context_only | planned=OH 6.1.0.31;实跑 unknown | contract.txt 是**运行前计划口径**;同 run 实跑件(results.json device 块 status=unverified、evidence record)无版本串 → 降级,记 planned_version |
| FZ-002 | context_only | planned=OH 6.1.0.31;实跑 unknown | 同 FZ-001:contract 为计划口径;evidence record 有 serial/boot_id 无版本串 → 降级 |
| FZ-003 | context_only | (背景) OH 6.1.0.31 | 运行目录 `2026-09-30-asset-fd-runtime` 在位,设备件仅 compileSdkType=OpenHarmony;版本只来自不同 run 的 platform-context |
| FZ-004 | context_only | (背景) OH 6.1.0.31 | j3-u3-sweep 目录 grep 版本串空;仅 platform-context 背景 |
| FZ-005 | unknown | — | art-r155 BUILD.md 无平台版本串;host 工具链与本板验证非同 run 证据链 |
| FZ-006 | context_only | (背景) OH 6.1.0.31 | u6-sweep 目录 grep 空;仅 platform-context 背景 |
| FZ-007 | context_only | (背景) OH 6.1.0.31 | t7d-stub-spec 无版本串;仅 platform-context 背景 |
| FZ-008 | context_only | (背景) OH 6.1.0.31 | t7d-stub-spec 无版本串;仅 platform-context 背景 |

APK/产物/来源 SHA per row live in `version-bindings.json` (verified_apps from
frozen.json are `reported`; artifacts carry their registered SHA). Files:

- `version-bindings.json` — the machine table (8 rows, schema `api-version-bindings/v1`)
- `results.json` — checker + negative-run outputs (five mutations nonzero, original untouched; incl. planned-as-direct and crossrun-as-direct scope cases)
- `check_version_bindings.py` — validator + `--negative` mode
- `landing-paths.txt`

No atlas shard or frozen.json entry was modified; no board/VM/remote access.
