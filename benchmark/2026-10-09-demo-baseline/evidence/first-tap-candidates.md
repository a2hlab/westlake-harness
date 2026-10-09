# 附表 A 的 32 个 B-tier key:首屏为什么空 + 一次点击能否出内容(2026-10-09 oc-t4)

数据源(只读离线):10-08 画册 `benchmark/2026-10-08-lit-apps-gallery/curation.json`(tier=B 32 key,每条 `shot` 指回 u14-window2 运行目录)+ 对应运行目录的 `record.json / processes-t20.txt / windows-t20.txt / hilog.txt / faults-after.txt`(全部亲读,零上板)。

## 总判(先给结论)

**32/32 全部是「进程活着 + 全屏窗口在 + 无崩溃」的静默空首屏**——不是死 app,是一次点击大概率能出内容的候选:

- 32/32 t20 时进程存活(ps 亲验),31/32 有自身全屏窗口(`pkg/activity` 形态,rect 0,0,1200,1920;唯一例外 fd-minetest 有窗但 rect 是全屏、内容为游戏首帧加载,见单条)
- 32/32 hilog 无 SIGSEGV/SIGABRT/ANR;子进程日志静默(ui_marks=3 量级,E/F≈7 条全是 IPC 噪声)
- 32/32 `record.json` status=`foreground_unconfirmed`(runner 启动方式=desktop 点击,但没做后续交互)
- faults-after 里出现的 imehost/sceneboard 崩溃是**全批次共有背景噪声**(与 09-28 的历史 faultlog 同名文件,非本 key 引入)

**为什么空(共性)**:这批全是「数据驱动首屏」app——note/list/editor/calculator 类的第一屏是空列表/空文档/空画布,且无一例外都停在 `SplashActivity → 主 Activity` 的空态,没有 runner 代点。

## 逐 key 表(点哪里=建议点击坐标,屏 1200×1920)

| key | 包名/入口 activity | 为什么空 | 一次点击能否出内容 | 点哪里 |
|---|---|---|---|---|
| cv2-app-varlorg-unote | app.varlorg.unote/NoteMain | 空笔记列表首屏 | 大概率能:列表 app 点 FAB 即建新笔记 | FAB 通常右下 (1080,1750);无 FAB 则点菜单 (60,90) |
| cv2-ca-ramzan-delist | ca.ramzan.delist/common.MainActivity | 空清单 | 能:同上,FAB 新条目 | (1080,1750) |
| cv2-com-alxgnon-postwriter | com.alxgnon.postwriter/MainActivity | 空草稿列表 | 能 | (1080,1750) |
| cv2-com-angrydoughnuts-android-alarmclock | …/AlarmClockActivity | 无闹钟时空态 | 能:点加号建闹钟 | (1080,300) 或菜单 (60,90) |
| cv2-com-cg-lrceditor | com.cg.lrceditor/HomePage | 无歌词文件空态 | 能:点导入/新建 | (600,960) 中心 CTA |
| cv2-com-deva-knot | com.deva.knot/MainActivity | 首页空 | 能 | (1080,1750) |
| cv2-com-emmanuelmess-itsdicey | …itsdicey/MainActivity | 掷骰首屏扁平 | 能:点骰子区即出数 | (600,960) |
| cv2-com-git-itdolan31-crystalpad | …crystalpad/MainActivity | 空画布(几乎全白) | 能:任意处画一笔即有内容 | (600,960) |
| cv2-com-maxistar-textpad | …textpad/EditorActivity | 空编辑器 | 能:点正文区+输入 | (600,960) |
| cv2-com-nathaniel-motus-umlclasseditor | …umlclasseditor…/MainActivity | 空 UML 文档 | 能:点新建 | (1080,1750) |
| cv2-com-nbossard-packlist | …packlist/gui.MainActivity | 空装箱清单 | 能 | (1080,1750) |
| cv2-com-nima-taskmanager | …taskmanager/MainActivity | 空任务列表 | 能 | (1080,1750) |
| cv2-com-nononsenseapps-notepad | …notepad…/ActivityMain_ | 空笔记列表 | 能 | (1080,1750) |
| cv2-com-notecryptpro | …notecrypt…/SelectDatabaseActivity | 首屏=选库/空库 | 能:点 create/new 即出表单 | (600,960) |
| cv2-com-omgodse-notally | …notally…/MainActivity | 空笔记列表 | 能 | (1080,1750) |
| cv2-com-page-bizzle | com.page.bizzle/MainActivity | 空页面 | 能 | (600,960) |
| cv2-com-pep1lo-bakerspercentagecalculator | …bakerspercentage…/MainActivity | 计算器空态 | 能:点数字键即出内容 | (300,1500) 数字区 |
| cv2-com-rafapps-simplenotes | …simplenotes/NotesListActivity | 空笔记列表 | 能 | (1080,1750) |
| cv2-com-wbpxre150-shoppinglist | …wbpxre150…/MainActivity | 空购物清单 | 能 | (1080,1750) |
| cv2-com-willbsp-habits | …willbsp…/MainActivity | 空习惯列表 | 能 | (1080,1750) |
| cv2-com-woefe-shoppinglist | …woefe…/activity.MainActivity | 空购物清单 | 能 | (1080,1750) |
| cv2-de-markusfisch-android-libra | …libra…/SplashActivity | 卡在 Splash(无窗,t20 仅存进程) | 存疑:先点屏幕中心唤醒/等跳转;若 Splash 依赖倒计时则一次点击未必跳 | (600,960);不行标 needs_review |
| cv2-eu-dfdx-jslab | eu.dfdx.jslab/MainActivity | JS 实验场空输入 | 能:点编辑区输入 | (600,960) |
| cv2-org-quicksc0p3r-simplecounter | …simplecounter/MainActivity | 计数器 0 态 | 能:点 +1 即变化 | (900,960) |
| fd-android | net.thunderbird.android/…MainActivity | 邮件首启向导/空收件箱(无窗@t20,进程活) | 存疑:首启向导需多步;一次点击能进下一屏 | (600,960) 向导按钮 |
| fd-binaryeye | …binaryeye…/SplashActivity | 卡在 Splash(无窗) | 存疑:同 libra,点中心试跳 | (600,960) |
| fd-droidify | com.looker.droidify/MainActivity | 商店空仓库(未添加源) | 能:点添加源即出表单 | (1080,1750) 或菜单 |
| fd-gallery | org.fossify.gallery/SplashActivity.Green | 相册无媒体空态(Splash 无窗) | 存疑:无媒体点了也难出内容;但权限授予后可能出文件夹视图 | (600,960) |
| fd-k9 | com.fsck.k9/…MainActivity | 邮件账户设置空态(无窗) | 存疑:同 thunderbird,向导多步 | (600,960) |
| fd-minetest | net.minetest.minetest/MainActivity | 游戏首帧加载/菜单 | 能:主菜单本应可见;点 Play 进世界列表 | (600,1500) |
| fd-notes | org.fossify.notes/SplashActivity.Green | 空笔记列表 | 能 | (1080,1750) |
| newpipe | org.schabi.newpipe/MainActivity(rect 1139 宽,布局异常) | 无网络流空态 | 存疑:离线首屏点哪里都难出流;但点本地 tab 能出页面结构 | 底部 tab (300,1850) |

## 给 cx-bms 合并用的三档标记

- **tap_likely**(一次点击大概率出内容):24 个——全部 list/editor/calc/pad 类 + droidify + minetest
- **tap_try**(点了才知道,首启向导/倒计时类):5 个——libra、binaryeye、fd-android、fd-k9、fd-gallery
- **needs_network_or_review**:3 个——newpipe(离线无流)、fd-gallery(无媒体)、libra(若非倒计时卡死)

## 复核锚点(供 cx-bms 抽查)

- 每条判定依据 = 运行目录的 `processes-t20.txt`(pid 存在)+ `windows-t20.txt`(`pkg/…` 窗口行)+ `record.json`(status/launch_method/bms.desktop_activity);坐标是 1200×1920 屏的 UI 惯例推断(右下 FAB/中心 CTA),**t3 上板时用一次 `uitest dumpLayout` 校正后即可批量代点**
- curation.json 的 32 条 shot 路径全部本地存在(亲验 ok=32/miss=0)
