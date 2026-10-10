# 演示手册终稿（离线文字版；封存启用仍待验收）

## Evidence first / 状态与来源

- 签认表机械汇总:内容档 `86/94` 为严格 lit（含 lit_splash 为87/94）；空态档 `26/32` 为 lit；游戏 `10/12` 为 lit。
- 本手册仅列 `112` 个精确 `lit` key；游戏是其中子集，不加总第二次。半亮、不亮、启动页见附录。
- 61b 演示板：`61b0657200000000000000000324012c`。此稿没有操作板、VM/SSH、安装、改运行时或签封存。
- 最终 `seal.json`、t4 两轮稳定性、封存恢复 provider、空闲板真实恢复演练尚未形成；不能凭文字终稿把它们判成 PASS。
- oc-t4 草稿中的游戏12全亮、任意FAB/固定坐标、联网空态当成功均不沿用；每个演示 key 有明确跳过兜底。

- manifest: `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-09-demo-baseline/demo-manifest.json`, SHA256 `7a2627326cb536bc8b0ee35587827999f448f827a91e22bdc663809767d82933`。
- oc-t4-draft: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-09-demo-baseline/t5/demo-runbook.md`, SHA256 `3acff381f58f41211d8f3eb11ab768c590798e5904191ceaa54506cc0d8de97c`。
- outer-signoff: `$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/t3-outer-signoff.json`, SHA256 `0e9b825a0ccbfcbe6af0bc1ccd7f93d55d323e1869b8ecdc957a7591048aa387`。

## 0. 开机就绪

等待已验收的自启恢复完成、桌面就绪；先跑只读自检：

```sh
bash scripts/lab/demo_selfcheck.sh --seal benchmark/2026-10-09-demo-baseline/t5/seal.json \
  --serial 61b0657200000000000000000324012c --out /tmp/demo-selfcheck-fresh.json
```

每次使用新的输出文件名。只有 live-readonly PASS 才说明封存身份匹配；OFFLINE_MATCH 不等于板上通过。
自检非零立即停演示、保存路径/期望/实际差异，交外环审；不得在封存板自行 restore、重启、重装或修运行时。
显示黑/白/报错不据活进程报亮。展示操作只用前台桌面与实际控件，不写死未核坐标。

## 1. 演示顺序（内容档优先，10个lit游戏在内容档最前）

每项前台点击真实桌面图标；等待自身界面。空态档的历史32个不混入首屏内容数字，虽本轮签lit仍按现场画面决定是否跳过。
游戏可在真实按钮上手动进入并演示一次触摸；本轮截图签认不证明玩法交互通过。

| 顺序 | key / 包名 | 显示名 | 分档 | 失败时跳过兜底 |
|---:|---|---|---|---|
| 1 | `cv2-com-kaajjo-libresudoku` / `com.kaajjo.libresudoku` | LibreSudoku | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-io-github-jdanders-dropcount;不重试、不现场修、不猜点击坐标 |
| 2 | `cv2-io-github-jdanders-dropcount` / `io.github.jdanders.dropcount` | DropCount | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendly2048;不重试、不现场修、不猜点击坐标 |
| 3 | `cv2-org-secuso-privacyfriendly2048` / `org.secuso.privacyfriendly2048` | 2048 （隐私友好） | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlybattleship;不重试、不现场修、不猜点击坐标 |
| 4 | `cv2-org-secuso-privacyfriendlybattleship` / `org.secuso.privacyfriendlybattleship` | Battleships | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlydame;不重试、不现场修、不猜点击坐标 |
| 5 | `cv2-org-secuso-privacyfriendlydame` / `org.secuso.privacyfriendlydame` | Checkers | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlyludo;不重试、不现场修、不猜点击坐标 |
| 6 | `cv2-org-secuso-privacyfriendlyludo` / `org.secuso.privacyfriendlyludo` | Ludo | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlymemory;不重试、不现场修、不猜点击坐标 |
| 7 | `cv2-org-secuso-privacyfriendlymemory` / `org.secuso.privacyfriendlymemory` | Memo Game | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlyminesweeper;不重试、不现场修、不猜点击坐标 |
| 8 | `cv2-org-secuso-privacyfriendlyminesweeper` / `org.secuso.privacyfriendlyminesweeper` | Minesweeper | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlysudoku;不重试、不现场修、不猜点击坐标 |
| 9 | `cv2-org-secuso-privacyfriendlysudoku` / `org.secuso.privacyfriendlysudoku` | Sudoku | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlyyahtzeedicer;不重试、不现场修、不猜点击坐标 |
| 10 | `cv2-org-secuso-privacyfriendlyyahtzeedicer` / `org.secuso.privacyfriendlyyahtzeedicer` | Dice Game | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-atr-hiit;不重试、不现场修、不猜点击坐标 |
| 11 | `cv2-com-atr-hiit` / `com.atr.hiit` | HIIT | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-ei-bmicalc;不重试、不现场修、不猜点击坐标 |
| 12 | `cv2-com-ei-bmicalc` / `com.ei.bmicalc` | BmiCalc | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-lcdcode-moodcairns;不重试、不现场修、不猜点击坐标 |
| 13 | `cv2-com-lcdcode-moodcairns` / `com.lcdcode.moodcairns` | Mood Cairns | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-zola-bmi;不重试、不现场修、不猜点击坐标 |
| 14 | `cv2-com-zola-bmi` / `com.zola.bmi` | BMI Calculator | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlycircuittraining;不重试、不现场修、不猜点击坐标 |
| 15 | `cv2-org-secuso-privacyfriendlycircuittraining` / `org.secuso.privacyfriendlycircuittraining` | Circuit Trainer | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlyintervaltimer;不重试、不现场修、不猜点击坐标 |
| 16 | `cv2-org-secuso-privacyfriendlyintervaltimer` / `org.secuso.privacyfriendlyintervaltimer` | Interval Timer | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlypaindiary;不重试、不现场修、不猜点击坐标 |
| 17 | `cv2-org-secuso-privacyfriendlypaindiary` / `org.secuso.privacyfriendlypaindiary` | Pain Diary | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlypausinghealthily;不重试、不现场修、不猜点击坐标 |
| 18 | `cv2-org-secuso-privacyfriendlypausinghealthily` / `org.secuso.privacyfriendlypausinghealthily` | Pausing Healthily | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-fitness;不重试、不现场修、不猜点击坐标 |
| 19 | `fd-fitness` / `de.tadris.fitness` | FitoTrack | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-uhabits;不重试、不现场修、不猜点击坐标 |
| 20 | `fd-uhabits` / `org.isoron.uhabits` | 习惯 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-anupam-acrylic;不重试、不现场修、不猜点击坐标 |
| 21 | `cv2-anupam-acrylic` / `anupam.acrylic` | Acrylic Paint | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-benny-pxerstudio;不重试、不现场修、不猜点击坐标 |
| 22 | `cv2-com-benny-pxerstudio` / `com.benny.pxerstudio` | PxerStudio | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-ruesga-android-wallpapers-photophase;不重试、不现场修、不猜点击坐标 |
| 23 | `cv2-com-ruesga-android-wallpapers-photophase` / `com.ruesga.android.wallpapers.photophase` | PhotoPhase | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-biz-binarysolutions-vatcalculator;不重试、不现场修、不猜点击坐标 |
| 24 | `cv2-biz-binarysolutions-vatcalculator` / `biz.binarysolutions.vatcalculator` | VAT Calculator | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-ath0-rpn;不重试、不现场修、不猜点击坐标 |
| 25 | `cv2-com-ath0-rpn` / `com.ath0.rpn` | RPN | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-better-alarm;不重试、不现场修、不猜点击坐标 |
| 26 | `cv2-com-better-alarm` / `com.better.alarm` | 简单闹钟 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-caniwebview-android;不重试、不现场修、不猜点击坐标 |
| 27 | `cv2-com-caniwebview-android` / `com.caniwebview.android` | CanIWebView | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-chancehorizon-just24hoursplus;不重试、不现场修、不猜点击坐标 |
| 28 | `cv2-com-chancehorizon-just24hoursplus` / `com.chancehorizon.just24hoursplus` | Just 24 Hours | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-chess-clock;不重试、不现场修、不猜点击坐标 |
| 29 | `cv2-com-chess-clock` / `com.chess.clock` | Chess Clock | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-codedead-deadhash;不重试、不现场修、不猜点击坐标 |
| 30 | `cv2-com-codedead-deadhash` / `com.codedead.deadhash` | DeadHash | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-darkempire78-opencalculator;不重试、不现场修、不猜点击坐标 |
| 31 | `cv2-com-darkempire78-opencalculator` / `com.darkempire78.opencalculator` | 计算器 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-example-dozencalc;不重试、不现场修、不猜点击坐标 |
| 32 | `cv2-com-example-dozencalc` / `com.example.dozencalc` | DozenCalc | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-example-ttime;不重试、不现场修、不猜点击坐标 |
| 33 | `cv2-com-example-ttime` / `com.example.TTime` | TTime | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-goofwear-file85toolkit;不重试、不现场修、不猜点击坐标 |
| 34 | `cv2-com-goofwear-file85toolkit` / `com.goofwear.file85toolkit` | File85Toolkit | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-knirirr-beecount;不重试、不现场修、不猜点击坐标 |
| 35 | `cv2-com-knirirr-beecount` / `com.knirirr.beecount` | BeeCount | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-mzhang-cleantimer;不重试、不现场修、不猜点击坐标 |
| 36 | `cv2-com-mzhang-cleantimer` / `com.mzhang.cleantimer` | Clean Timer | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-nicue-onetwo;不重试、不现场修、不猜点击坐标 |
| 37 | `cv2-com-nicue-onetwo` / `com.nicue.onetwo` | OneTwo | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-paperknifeplus-app;不重试、不现场修、不猜点击坐标 |
| 38 | `cv2-com-paperknifeplus-app` / `com.paperknifeplus.app` | PaperKnife+ | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-pvcodes-debtcalc;不重试、不现场修、不猜点击坐标 |
| 39 | `cv2-com-pvcodes-debtcalc` / `com.pvcodes.debtcalc` | DebtCalc | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-simonimal-minimalcurconv;不重试、不现场修、不猜点击坐标 |
| 40 | `cv2-com-simonimal-minimalcurconv` / `com.simonimal.minimalcurconv` | Minimal Currency Converter | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-tomatodev-timerdroid;不重试、不现场修、不猜点击坐标 |
| 41 | `cv2-com-tomatodev-timerdroid` / `com.tomatodev.timerdroid` | TimerDroid | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-vonglasow-michael-voltagedrop;不重试、不现场修、不猜点击坐标 |
| 42 | `cv2-com-vonglasow-michael-voltagedrop` / `com.vonglasow.michael.voltagedrop` | Voltage Drop Calculator | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-de-markusfisch-android-shadereditor;不重试、不现场修、不猜点击坐标 |
| 43 | `cv2-de-markusfisch-android-shadereditor` / `de.markusfisch.android.shadereditor` | 着色器编辑器 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlydicer;不重试、不现场修、不猜点击坐标 |
| 44 | `cv2-org-secuso-privacyfriendlydicer` / `org.secuso.privacyfriendlydicer` | Dicer | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlypin;不重试、不现场修、不猜点击坐标 |
| 45 | `cv2-org-secuso-privacyfriendlypin` / `org.secuso.privacyfriendlypin` | PIN Mnemonic | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlyruler;不重试、不现场修、不猜点击坐标 |
| 46 | `cv2-org-secuso-privacyfriendlyruler` / `org.secuso.privacyfriendlyruler` | Ruler | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlytapemeasure;不重试、不现场修、不猜点击坐标 |
| 47 | `cv2-org-secuso-privacyfriendlytapemeasure` / `org.secuso.privacyfriendlytapemeasure` | Tape Measure | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-catima;不重试、不现场修、不猜点击坐标 |
| 48 | `fd-catima` / `me.hackerchick.catima` | Catima | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 ooniprobe;不重试、不现场修、不猜点击坐标 |
| 49 | `ooniprobe` / `org.openobservatory.ooniprobe` | OONI Probe | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-mpv;不重试、不现场修、不猜点击坐标 |
| 50 | `fd-mpv` / `is.xyz.mpv` | mpv | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-noice;不重试、不现场修、不猜点击坐标 |
| 51 | `fd-noice` / `com.github.ashutoshgngwr.noice` | Noice：自然平静的噪音 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-seal;不重试、不现场修、不猜点击坐标 |
| 52 | `fd-seal` / `com.junkfood.seal` | Seal | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-groce-app;不重试、不现场修、不猜点击坐标 |
| 53 | `cv2-com-groce-app` / `com.groce.app` | Groce | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-harr1424-listmaker;不重试、不现场修、不猜点击坐标 |
| 54 | `cv2-com-harr1424-listmaker` / `com.harr1424.listmaker` | List Maker | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-lolo-io-onelist;不重试、不现场修、不猜点击坐标 |
| 55 | `cv2-com-lolo-io-onelist` / `com.lolo.io.onelist` | 1List | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-maltaisn-notes-sync;不重试、不现场修、不猜点击坐标 |
| 56 | `cv2-com-maltaisn-notes-sync` / `com.maltaisn.notes.sync` | Another Notes | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-pocket-plan-j7-003;不重试、不现场修、不猜点击坐标 |
| 57 | `cv2-com-pocket-plan-j7-003` / `com.pocket_plan.j7_003` | PocketPlan | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-rootminusone8004-bazarnote;不重试、不现场修、不猜点击坐标 |
| 58 | `cv2-com-rootminusone8004-bazarnote` / `com.rootminusone8004.bazarnote` | Bazarnote | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-sunilpaulmathew-snotz;不重试、不现场修、不猜点击坐标 |
| 59 | `cv2-com-sunilpaulmathew-snotz` / `com.sunilpaulmathew.snotz` | sNotz | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-wattwurm-toodoo;不重试、不现场修、不猜点击坐标 |
| 60 | `cv2-com-wattwurm-toodoo` / `com.wattwurm.toodoo` | toodoo | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-de-koelle-christian-trickytripper;不重试、不现场修、不猜点击坐标 |
| 61 | `cv2-de-koelle-christian-trickytripper` / `de.koelle.christian.trickytripper` | Tricky Tripper | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlynotes;不重试、不现场修、不猜点击坐标 |
| 62 | `cv2-org-secuso-privacyfriendlynotes` / `org.secuso.privacyfriendlynotes` | Notes | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlytodolist;不重试、不现场修、不猜点击坐标 |
| 63 | `cv2-org-secuso-privacyfriendlytodolist` / `org.secuso.privacyfriendlytodolist` | To-Do List | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-calendar;不重试、不现场修、不猜点击坐标 |
| 64 | `fd-calendar` / `org.fossify.calendar` | 日历 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-client;不重试、不现场修、不猜点击坐标 |
| 65 | `fd-client` / `com.nextcloud.client` | Nextcloud | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-etar;不重试、不现场修、不猜点击坐标 |
| 66 | `fd-etar` / `ws.xsoh.etar` | Etar - 开源日历 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-tasks;不重试、不现场修、不猜点击坐标 |
| 67 | `fd-tasks` / `org.tasks` | Tasks | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 markor;不重试、不现场修、不猜点击坐标 |
| 68 | `markor` / `net.gsantner.markor` | Markor | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 anki;不重试、不现场修、不猜点击坐标 |
| 69 | `anki` / `com.ichi2.anki` | AnkiDroid | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-asdoi-timetable;不重试、不现场修、不猜点击坐标 |
| 70 | `cv2-com-asdoi-timetable` / `com.asdoi.timetable` | TimeTable | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-edward-studytracker;不重试、不现场修、不猜点击坐标 |
| 71 | `cv2-com-edward-studytracker` / `com.edward.studytracker` | study tracker | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlyrecknoningskills;不重试、不现场修、不猜点击坐标 |
| 72 | `cv2-org-secuso-privacyfriendlyrecknoningskills` / `org.secuso.privacyfriendlyrecknoningskills` | Reckoning Skills | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 aegis;不重试、不现场修、不猜点击坐标 |
| 73 | `aegis` / `com.beemdevelopment.aegis` | Aegis | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-aptasystems-dicewarepasswordgenerator;不重试、不现场修、不猜点击坐标 |
| 74 | `cv2-com-aptasystems-dicewarepasswordgenerator` / `com.aptasystems.dicewarepasswordgenerator` | Diceware Password Generator | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-codedead-advancedpassgen;不重试、不现场修、不猜点击坐标 |
| 75 | `cv2-com-codedead-advancedpassgen` / `com.codedead.advancedpassgen` | Advanced PassGen | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-trianguloy-clipboardeditor;不重试、不现场修、不猜点击坐标 |
| 76 | `cv2-com-trianguloy-clipboardeditor` / `com.trianguloy.clipboardeditor` | Simple Clipboard Editor | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-secuso-privacyfriendlypasswordgenerator;不重试、不现场修、不猜点击坐标 |
| 77 | `cv2-org-secuso-privacyfriendlypasswordgenerator` / `org.secuso.privacyfriendlypasswordgenerator` | Password Generator | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-com-amaze-filemanager;不重试、不现场修、不猜点击坐标 |
| 78 | `fd-com-amaze-filemanager` / `com.amaze.filemanager` | Amaze 文件管理器 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-com-kunzisoft-keepass-libre;不重试、不现场修、不猜点击坐标 |
| 79 | `fd-com-kunzisoft-keepass-libre` / `com.kunzisoft.keepass.libre` | KeePassDX 密码库 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-filemanager;不重试、不现场修、不猜点击坐标 |
| 80 | `fd-filemanager` / `org.fossify.filemanager` | 文件管理器 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-netguard;不重试、不现场修、不猜点击坐标 |
| 81 | `fd-netguard` / `eu.faircode.netguard` | NetGuard | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-github-dfa-diaspora-android;不重试、不现场修、不猜点击坐标 |
| 82 | `cv2-com-github-dfa-diaspora-android` / `com.github.dfa.diaspora_android` | dandelion* | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-tusky;不重试、不现场修、不猜点击坐标 |
| 83 | `fd-tusky` / `com.keylesspalace.tusky` | Tusky | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-feeder;不重试、不现场修、不猜点击坐标 |
| 84 | `fd-feeder` / `com.nononsenseapps.feeder` | Feeder | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-reader;不重试、不现场修、不猜点击坐标 |
| 85 | `fd-reader` / `me.ash.reader` | Read You | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 wikipedia;不重试、不现场修、不猜点击坐标 |
| 86 | `wikipedia` / `org.wikipedia` | 维基百科 | shown | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-willbsp-habits;不重试、不现场修、不猜点击坐标 |
| 87 | `cv2-com-willbsp-habits` / `com.willbsp.habits` | Habits | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-gallery;不重试、不现场修、不猜点击坐标 |
| 88 | `fd-gallery` / `org.fossify.gallery` | 图库 | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-angrydoughnuts-android-alarmclock;不重试、不现场修、不猜点击坐标 |
| 89 | `cv2-com-angrydoughnuts-android-alarmclock` / `com.angrydoughnuts.android.alarmclock` | 闹钟 | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-emmanuelmess-itsdicey;不重试、不现场修、不猜点击坐标 |
| 90 | `cv2-com-emmanuelmess-itsdicey` / `com.emmanuelmess.itsdicey` | Its Dicey! | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-nathaniel-motus-umlclasseditor;不重试、不现场修、不猜点击坐标 |
| 91 | `cv2-com-nathaniel-motus-umlclasseditor` / `com.nathaniel.motus.umlclasseditor` | UML Class Editor | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-pep1lo-bakerspercentagecalculator;不重试、不现场修、不猜点击坐标 |
| 92 | `cv2-com-pep1lo-bakerspercentagecalculator` / `com.pep1lo.bakerspercentagecalculator` | 烘焙百分比计算器 | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-de-markusfisch-android-libra;不重试、不现场修、不猜点击坐标 |
| 93 | `cv2-de-markusfisch-android-libra` / `de.markusfisch.android.libra` | Decisions | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-org-quicksc0p3r-simplecounter;不重试、不现场修、不猜点击坐标 |
| 94 | `cv2-org-quicksc0p3r-simplecounter` / `org.quicksc0p3r.simplecounter` | Simple Counter | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-binaryeye;不重试、不现场修、不猜点击坐标 |
| 95 | `fd-binaryeye` / `de.markusfisch.android.binaryeye` | Binary Eye | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-cg-lrceditor;不重试、不现场修、不猜点击坐标 |
| 96 | `cv2-com-cg-lrceditor` / `com.cg.lrceditor` | LRC Editor | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-app-varlorg-unote;不重试、不现场修、不猜点击坐标 |
| 97 | `cv2-app-varlorg-unote` / `app.varlorg.unote` | uNote | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-ca-ramzan-delist;不重试、不现场修、不猜点击坐标 |
| 98 | `cv2-ca-ramzan-delist` / `ca.ramzan.delist` | Delist | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-alxgnon-postwriter;不重试、不现场修、不猜点击坐标 |
| 99 | `cv2-com-alxgnon-postwriter` / `com.alxgnon.postwriter` | Post Writer | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-deva-knot;不重试、不现场修、不猜点击坐标 |
| 100 | `cv2-com-deva-knot` / `com.deva.knot` | Knot | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-git-itdolan31-crystalpad;不重试、不现场修、不猜点击坐标 |
| 101 | `cv2-com-git-itdolan31-crystalpad` / `com.git.itdolan31.crystalpad` | Crystalpad | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-maxistar-textpad;不重试、不现场修、不猜点击坐标 |
| 102 | `cv2-com-maxistar-textpad` / `com.maxistar.textpad` | 简单文本编辑器 | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-nbossard-packlist;不重试、不现场修、不猜点击坐标 |
| 103 | `cv2-com-nbossard-packlist` / `com.nbossard.packlist` | packlist | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-nima-taskmanager;不重试、不现场修、不猜点击坐标 |
| 104 | `cv2-com-nima-taskmanager` / `com.nima.taskmanager` | Task Manager | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-nononsenseapps-notepad;不重试、不现场修、不猜点击坐标 |
| 105 | `cv2-com-nononsenseapps-notepad` / `com.nononsenseapps.notepad` | NoNonsense Notes | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-notecryptpro;不重试、不现场修、不猜点击坐标 |
| 106 | `cv2-com-notecryptpro` / `com.notecryptpro` | Note Crypt Pro | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-omgodse-notally;不重试、不现场修、不猜点击坐标 |
| 107 | `cv2-com-omgodse-notally` / `com.omgodse.notally` | Notally | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-page-bizzle;不重试、不现场修、不猜点击坐标 |
| 108 | `cv2-com-page-bizzle` / `com.page.bizzle` | Page | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-rafapps-simplenotes;不重试、不现场修、不猜点击坐标 |
| 109 | `cv2-com-rafapps-simplenotes` / `com.rafapps.simplenotes` | Simple Material Notes | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-wbpxre150-shoppinglist;不重试、不现场修、不猜点击坐标 |
| 110 | `cv2-com-wbpxre150-shoppinglist` / `com.wbpxre150.shoppinglist` | Shopping List | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 cv2-com-woefe-shoppinglist;不重试、不现场修、不猜点击坐标 |
| 111 | `cv2-com-woefe-shoppinglist` / `com.woefe.shoppinglist` | Shopping List | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 fd-notes;不重试、不现场修、不猜点击坐标 |
| 112 | `fd-notes` / `org.fossify.notes` | 笔记 | minimal | 打不开/闪退/黑白屏/空态/加载或网络依赖:返回桌面直接跳至 头条(仅经独立验收后) / 收尾;不重试、不现场修、不猜点击坐标 |

## 2. 今日头条：前台桌面点击，不用后台 aa start

仅在 Route B 与最终封存叠加件独立验收后纳入。前台桌面找到「今日头条」图标点击；
不要用 `aa start` 当演示入口：现场后台启动会被拒 `10107101`。图标坐标必须取当前界面，不照抄草稿固定坐标。
首页出现自身内容后，按真实控件刷新/下拉一次，滚动信息流，点一篇文章确认正文，再返回首页；无网/不刷新/正文打不开就记现象并跳过。
看门狗只按已验收 Route B 配方管理隔离的 `asx-spawner` 与子进程，绝不按名字清理 U13 `appspawn-x`。
宿主被杀后不能依赖被拒的后台启动自愈：前台再点桌面图标；一次仍无内容则直接收尾，不现场改权限/preauth或运行时。
观察到进程抖动不等于界面稳定；最终演示要求刷新与点文章的实际画面证据。

## 3. BoatAttack

**待 PR03 渲染移植验收后补。**
不把偏紫/低分辨率、旧候选五绑定或尚未验收的私有件当封存配置；本稿不列部署/点击坐标。
待验收后补真实前台入口、分辨率/色彩/操控判据及经签部署/回滚层。未就绪时跳过BoatAttack，直接收尾。

## 4. 恢复入口与禁止现场修复

恢复默认 dry-run；封存后任何写操作仅用户能解封授权。先在外环指定空闲板演练，不修改原 seal 的 serial：

```sh
bash scripts/lab/demo_restore.sh --dry-run --rehearsal \
  --seal benchmark/2026-10-09-demo-baseline/t5/seal.json \
  --deployment benchmark/2026-10-09-demo-baseline/t5/restore-deployment.json \
  --serial <外环指定空闲板完整serial> --out <新的持久日志目录>
```

正式封存 provider 尚无。底座候选二选一待外环定：① cx-t0 fresh native票据回放（master `5a172dd057`,
`benchmark/2026-10-09-demo-baseline/t3/restore5cd-u13-ticket/`），319 diff{}→父子视图/单ART→HW/ZZ t20；
② cc-wiki `benchmark/2026-10-10-u13-autostart/payload/scripts/install-westlake-u13-autostart.sh`（5cd真实reboot只证明机制，未落master）。
自启就绪/文件相同不能代替foundation实际加载宿主库和截图验收；5cd/5ea宿主库mount与61b物理文件的差异不能外推。
选定适配器后，顺序为 U13 → 已封存头条 Route B → 已封存BoatAttack，三层provider/rollback都逐SHA绑定；不拿候选源码当已签恢复配方。
恢复前只读校验源SHA、系统版本/安装器等不可替换前提；缺读回/未知漂移拒绝，保留外部锁；不得重用旧native票据绕过门。
真实空闲板演练及最终封存/AGENTS演示板登记由外环另行安排，此离线包不执行。

## 5. 收尾

返回桌面，保存演示日志（每项 key/画面/skip 原因）；再跑新的只读 selfcheck。
若有漂移停止并交外环；不现场改 settings、安装、文件、权限或重启。封存板只读巡检，解封只有用户能批。

## 附录：不进入演示序列

| key | 显示名 | 签认 | 原因 |
|---|---|---|---|
| `antennapod` | AntennaPod | not_lit | 半亮/不亮/未签,不进入演示序列 |
| `cv2-com-armanmaurya-archiv` | Archiv | half_empty | 半亮/不亮/未签,不进入演示序列 |
| `cv2-eu-dfdx-jslab` | JSlab | half_empty | 半亮/不亮/未签,不进入演示序列 |
| `cv2-org-andresoviedo-dddmodel2` | 3D Model Viewer | not_lit | 半亮/不亮/未签,不进入演示序列 |
| `fd-android` | Thunderbird：解放收件箱 | half_loading | 半亮/不亮/未签,不进入演示序列 |
| `fd-auxio` | Auxio | half_empty | 半亮/不亮/未签,不进入演示序列 |
| `fd-droidify` | Droid-ify | half_empty | 半亮/不亮/未签,不进入演示序列 |
| `fd-k9` | K-9 Mail | half_loading | 半亮/不亮/未签,不进入演示序列 |
| `fd-libretube` | LibreTube | half_empty | 半亮/不亮/未签,不进入演示序列 |
| `fd-minetest` | Luanti | half_loading | 半亮/不亮/未签,不进入演示序列 |
| `fd-organicmaps` | Organic Maps・离线地图与导航 & GPS | lit_splash | 启动页,不进入演示序列 |
| `fd-stk` | SuperTuxKart | lit_splash | 启动页,不进入演示序列 |
| `newpipe` | NewPipe | not_lit | 半亮/不亮/未签,不进入演示序列 |
| `opencamera` | Open Camera | not_lit | 半亮/不亮/未签,不进入演示序列 |
| `termux` | Termux | not_lit | 半亮/不亮/未签,不进入演示序列 |
| `vlc` | VLC | not_lit | 半亮/不亮/未签,不进入演示序列 |
