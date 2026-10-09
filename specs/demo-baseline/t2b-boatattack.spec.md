spec: task
name: "BoatAttack on the demo board's unified state"
inherits: project
---

## 意图

让之前在 00.Workspace(`~/orca/00.Workspace-games-ad1ab0a7`,分支 `games/boatattack-repro` 43ec24af9)点亮过的 BoatAttack(`com.Unity3d.BoatAttackDay`,APK SHA 8dc63665…)在演示板上跑起来:1920×1200 赛艇画面、同一进程、触摸有响应,并且和另外 100 多个应用用同一套统一态。

## 已定决策

- 已知事实:BoatAttack 的共享运行代(`strict-boat-assembled-20260924T074522Z-25403`)与我们的统一态在 9 个共享路径中只有 `libwestlake_bionic_pthread_bridge.so` 同 SHA;appspawn-x、adapter bridge、android runtime、nativeloader、oh-adapter-runtime.jar 都不同。两代不能同路径共存。
- 先静态:列出 BoatAttack 共享代相对我们统一态的差异里,哪些是它的必要修复(横屏父会话、真实触摸投射、Swappy、JNI attach 等,出处是该分支提交与 `src/tools/devices/boat-attack-apk-lightup.sh`),哪些与我们已有修复等价;产出逐件对照表。
- 路线顺序:① 统一态 + BoatAttack 私有三件(C7 libunity、C4 libil2cpp、signal-box,应用私有 bind,不碰共享路径);② ① 不行时按对照表把必要修复以新文件移植进统一态,不改冻结项;③ 仍不行再报告给外环,不擅自换整代。
- 每一步先在空闲板上做,通过后才叠到演示板;复用该分支的驱动脚本时只扩白名单,不改判据。

- 验收以原版 PASS 截图为对照(00.Workspace var/state/reproduce-boat-attack-apk/20260924T080718Z-quick):HUD 字号与清晰度一致(非放大拉伸)、色彩一致(非偏紫)、加速触摸后 KPH 升到两位数且 LAP/位置推进、转向触摸改变航向、1920×1200 整屏。只看尺寸和 KPH 000→001 不算通过(2026-10-10 外环签错一次)。
- 路线以原版复现为准:先在空闲板原样跑 reproduce.sh 到 PASS,再按差异表把缺的原版件补到目标板,不自行裁件。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-boatattack/**
- specs/demo-baseline/**
- tools/spec-checks/tests/demo_baseline.rs

## 验收标准

场景: Generation difference table is complete and sourced
  测试: demo_baseline_boatattack_static
  假设 Both generations are pinned by SHA
  当 The difference table is built offline
  那么 Each of the nine shared paths lists both SHAs the commit that introduced the BoatAttack side and whether our unified state has an equivalent fix

场景: BoatAttack runs on the unified state with touch
  审核: human
  测试: demo_baseline_boatattack_run
  假设 The chosen route is overlaid on a spare board running the unified state
  当 BoatAttack is launched from the desktop and touched five times
  那么 The screenshot shows the 1920x1200 racing scene the PID stays the same and the scene changes after touch

场景: Overlay that breaks other apps is rolled back
  测试: demo_baseline_boatattack_run
  假设 The BoatAttack overlay is installed
  当 Ten previously lit keys are relaunched
  那么 If any of them is no longer lit by t20 screenshot the overlay is rolled back and the failure is recorded

场景: Missing or mismatched inputs reject before any board write
  测试: demo_baseline_boatattack_static
  假设 The APK or a private candidate SHA does not match its pin
  当 The overlay step starts
  那么 It exits nonzero naming the mismatched file and no board write is logged

## 排除范围

- 修改 APK 或重签;整代换成 BoatAttack 的共享代;改另外两块实验板的统一态。
