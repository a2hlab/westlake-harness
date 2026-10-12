# registry shard 覆盖说明(2026-10-12, oc-t4, 初审修正版)

## 行集(22 行)

- **REG-001..008 = 冻结 8 条逐项成行**(FZ-001..FZ-008):成员精确到符号/文件;`frozen_ids` 关联;验证一律 **reported**(历史签认,本轮不重看图);validation.result 保留登记原文(不再截断);source_location 完整引用登记 source_record;route_generation 按登记写具体代际(FZ-001 b5a67c62 / FZ-002 U13 / FZ-004 J1-final→J3 jar 链 / FZ-006 J7·J7b·U6 / FZ-005 master art-r155)。
- **修正(外环初审)**:FZ 行 oh_tested 全部改 **unknown**(冻结登记≠本轮部署,板级 OH 小版本未逐板核验,只在 verified_apps.board 有 61b/5cd/5ea 字样);deployment_status 全部 **historical**(当前部署需 image-provenance/runtime 指纹另证,不泛套 current_evidence)。
- **REG-101..114 = 横切能力 14 行**(修正 REG-108/110 members 与 evidence 补齐):
  - ART 工具链 ×4(101/102/103/104)、SELinux ×2(105/106)、冷启动 ×2(107/108)、BoatAttack(109)、NDK(110 partial)、治理 ×4(111-114)。
- **支撑知识标注(修正 5)**:REG-105..109 与 REG-111..114 共 9 行是**门禁/部署/治理工具与知识**,不是 Android API 本身——保留它们是为 API 行提供可追溯的运行环境与验证基建语境,按外环指示在 notes 显式标注;主表汇总时可归入"supporting-knowledge"分组,不与 API 能力行混计。

## 证据规则

- 15+2 来源:master 相对路径 + SHA256(经主树 atlas.py validate_rows 亲验 = `{"rows": 22, "hashed_files": 16}` 全过,零报错);跨树引用 $WORKSPACES/<tree>(t4/wiki/00.Workspace,resolve 走 WORKSPACES 根)。
- unknown 保留:android_tested 全 unknown;android_source 仅 r1/r16 有据处;apk_target_sdk 不外推。
- static/unit/reported 分级:符号导出=static;门禁/构建=unit;历史板测=reported。

## 版本变更发现

8 条冻结全部 version=1、history=0——tiered-freeze(3af0b90b)建立后无条目走过 defect/platform/extension 换版;art-r155 配方侧 seccomp-stock 删除(4d97756aff,内容哈希 0ad4af23→78357079)未触发冻结升版。

## 缺口(gaps 汇总,8 条)

1. 18 件 art/oat 未逐字节复现(checksum+53KB,d600 构建侧差异;树源未取得)——REG-102
2. 板上 libart 精确源 commit 未知(d600)——REG-101
3. c-route asm 产物未持久到 master(hw248)——REG-103
4. app-private(/data/app)SELinux 域未证(范围外 skip)——REG-105
5. NDK 16 缺失符号中 ASensor×11/AConfiguration×5 无实现——REG-110
6. barrier 修复版 driver 未在真实封存跑过——REG-108
7. BoatAttack 可玩判据(1920×1200/HUD/KPH)待上板;49B CLASSNAME_FIX 移植决策未落——REG-109
8. FZ 行 APK 级验证全为历史 reported;OH 实测小版本未逐板核(oh_tested=unknown)——REG-001..008

## unclassified(3)

- knowledge/gates/native-predeploy-exceptions.json(4MB 逐符号例外,未逐条成行;建议 native shard 或后续轮)
- knowledge/gates/spec-check-exceptions.json(测试基建例外,非 API 面)
- knowledge/toolchains/PORTING-DEX2OAT-NEXT.md(后续计划非现状)
