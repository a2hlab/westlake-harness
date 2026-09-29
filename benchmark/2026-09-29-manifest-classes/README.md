# #69: fd-binaryeye spawn-stage first cause + 20-app manifest classification

## ① fd-binaryeye 卡在 spawn 阶段的首因(61b,探针 T1520)

现象(pid 29875,t+15/t+30 双存活):
- `cmdline` = `/system/bin/appspawn-x`(进程从未 re-exec 换名;`comm` = `de.markusfisch.` 截断名)
- 主线程 `MQ_nativePollOnce`(Java looper 空转),内核栈 `do_epoll_wait` — **不是死锁/自旋**

首因链(hilog 原文,`be-hilog.txt`):
1. `[ROUTE-A] stock stage31 complete; entering Android child` — 子进程正常进入 Android 运行时
2. `[B43-BIND] ensureBindApplication start bundle=de.markusfisch.android.binaryeye`
3. **`[B43-BIND] nativeParseManifestJson failed: java.lang.UnsatisfiedLinkError: No implementation found for java.lang.String adapter.activity.AppSchedulerBridge.nativeParseManifestJson(...)`** — 桥接库 84695d62 缺 manifest 解析 JNI(与 B8 结论一致)
4. `[B43-BIND] providers populated: 0` → androidx.startup 不跑、自定义 Application 类名不被应用(裸 Application)
5. 同因副作用:`[WL-THEME-SYNC] sync parse failed: UnsatisfiedLinkError`(同一 JNI);`[COROUTINE-FIX] primeCoroutineStart FAILED (non-fatal): ClassNotFoundException: kotlinx.coroutines.CoroutineStart`
6. **本代 ScheduleLaunchAbility 已到达**(`[BRIDGED] ScheduleLaunchAbility -> scheduleTransaction(LaunchActivityItem)`、`[B47-SLA]`)——与 #63 r5 的 13 app"拿到前台后 0.7s 退出"不同:binaryeye 过了 SLA、进了 looper,但因为 manifest 解析失败,bind 阶段的 Application/providers/theme 全部缺失,app 停在空转白窗,AbilityStage 回应依旧不发生。

结论:**binaryeye 的首因 = 桥接库缺 `nativeParseManifestJson` JNI(B8 INVENTORY 第 1-3 项的运行时证据)**,不是 spawn/ART/VSync 问题。

## ② 20 个 app 的 manifest 静态分类

来源:#63 白窗 13 ∪ #65 B8r7b 14,去重 = 20(`keys-27.json`)。工具:aapt2 badging+xmltree + zip 目录(Flutter)+ dex 字节(appcompat/material)。

| key | application name | Flutter | providers | targetSdk |
|---|---|---|---|---|
| burgerking | com.emn8.mobilem8.nativeapp.bk.MainApplication | ✗ | 8 | 36 |
| fd-android | net.thunderbird.android.ThunderbirdApp | ✗ | 9 | 36 |
| fd-binaryeye | …app.BinaryEyeApp(自定义) | ✗ | 2 | 37 |
| fd-catima | protect.card_locker.LoyaltyCardLockerApplication | ✗ | 4 | 36 |
| fd-etar | com.android.calendar.CalendarApplication | ✗ | 3 | 37 |
| fd-fennec_fdroid | org.mozilla.fenix.FenixApplication | ✗ | 9 | 37 |
| fd-fluffychat | chat.fluffy.fluffychat.MainActivity | ✓ | 3 | 36 |
| fd-immich | app.alextran.immich.ImmichApp | ✓ | 4 | 36 |
| fd-k9 | app.k9mail.K9App | ✗ | 9 | 36 |
| fd-kitchenowl | android.app.Application(默认) | ✓ | 3 | 36 |
| fd-libre | deckers.thibault.aves.MainActivity | ✓ | 4 | 36 |
| fd-minetest | *(见注) | ✗ | 3 | 35 |
| fd-mobile | org.jellyfin.mobile.JellyfinApplication | ✗ | 2 | 36 |
| fd-saber | android.app.Application(默认) | ✓ | 6 | 36 |
| fd-stk | org.supertuxkart.stk.SuperTuxKartActivity | ✗ | 0 | 30 |
| localsend | android.app.Application(默认) | ✓ | 3 | 37 |
| mindustry | *(见注) | ✗ | 0 | 36 |
| noice | …noice.NoiceApplication | ✗ | 1 | 33 |
| ooniprobe | org.ooni.probe.AndroidApplication | ✗ | 4 | 37 |
| opencamera | …opencamera.OpenCameraApplication | ✗ | 1 | 36 |

完整字段(含 theme ref、minSdk、launch activity、appcompat/material dex 命中)在 `results.json`。

### 预测(#68/r8b manifest 投影落地后)

- **只差 manifest 解析**(自定义 Application + providers 即可过 bind,无其它已知墙):fd-binaryeye、fd-catima、noice、fd-mobile、ooniprobe、fd-k9(条件:Koin 由自定义 App 启动)、fd-android(同前,ThunderbirdApp)、opencamera
- **manifest 之外还有墙**:
  - Flutter 域外路径(flutter .so outside app domain):fd-fluffychat、fd-immich、fd-kitchenowl、fd-libre、fd-saber、localsend
  - Theme.AppCompat(inflate 崩):burgerking、fd-minetest、opencamera(可能既有 manifest 又有主题)
  - armeabi namespace(Etar/BK 类):fd-etar、burgerking
  - fd-stk/mindustry:providers=0、Application=Activity 类名(异常 manifest,可能已过 bind 但无 UI;stk 在 #60 已证 looper 空转)
- 优先验证顺序建议:先 fd-binaryeye/custom Application 类(JNI 修复的直接受益者),再 Flutter 组(需要另一项修复)
