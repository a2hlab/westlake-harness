# U6 全量整理(2026-10-01,oc-t4,机械活)

派单(板 ACK(95) 05:12):把 U6 全量整理成可入库的 benchmark 目录——组成、四份运行目录与 facts TOTAL 行原文、外环 04:36:43 签认原文、66 个 key 一张表(facts 行 + 外环 t20 结论)。

## 组成

- **U5 native N4-order**(216b68fb)
- **J7b**(381110a6):WifiFetcher/AppWidgetFetcher/VibratorFetcher mLock/registerReceiver 兜底空 Intent
- **T7c 27 镜像**(stubs 366acc27):tagsoup Parser + 4 个 boot-api 桩(NetworkRequest.getNetworkSpecifier/NetworkInfo.getState/NetworkCapabilities.getLinkUp/DownstreamBandwidthKbps/MediaStore.{Images,Video,Audio}.Media.EXTERNAL/INTERNAL_CONTENT_URI)
- **合包输入**:5 个 split 键(x/burgerking/mcdonalds/firefox/subwaysurfers)合包后单件 APK(APKEditor 1.4.9 merge + apksigner 签 v2/v3)

## 四份运行目录与 facts TOTAL 行原文

| 板 | 运行目录 | facts TOTAL 行原文 |
|---|---|---|
| 5cd | westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep/5cd/u6-5cd-20261001T034305/5cd1e3dd00000000000000000923012c/ | `TOTAL keys=22 screenshots_captured=44/44 alive_t5=17 alive_t20=17` |
| 61b | westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep/61b/u6-61b-20261001T034305/61b0657200000000000000000324012c/ | `TOTAL keys=22 screenshots_captured=44/44 alive_t5=12 alive_t20=10` |
| 5ea | westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep/5ea/u6-5ea-20261001T035212/5ea34a4500000000000000001123012c/ | `TOTAL keys=16 screenshots_captured=32/32 alive_t5=8 alive_t20=8` |
| 5ea-resume | westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep/5ea-resume/u6-5ea-resume/5ea34a4500000000000000001123012c/ | `TOTAL keys=6 screenshots_captured=10/10 alive_t5=2 alive_t20=2` |

## 外环 04:36:43 签认原文

> 外环(claude) **签认 U6 三板全量点亮数:27(U5 的 24 个全部保持 + 新亮 3 个),另 2 个 flaky 键本轮也亮,不计入。** 外环读全部 t20(5cd 22 张、61b 22 张、5ea 21 张;运行目录 westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep/{5cd,61b,5ea,5ea-resume}/)。
>
> facts 原样(TOTAL 行):5cd「TOTAL keys=22 screenshots_captured=44/44 alive_t5=17 alive_t20=17」;61b「TOTAL keys=22 screenshots_captured=44/44 alive_t5=12 alive_t20=10」;5ea「TOTAL keys=16 screenshots_captured=32/32 alive_t5=8 alive_t20=8」+ 5ea-resume「TOTAL keys=6 screenshots_captured=10/10 alive_t5=2 alive_t20=2」;四份都是 RUNTIME 68b7fb016253 / BOOTIMAGE f25f230f5c77 / TOOL bms_batch=456dfc6f manifest=71cd7ecd。
>
>  · U5 已亮 24 个逐个核:aegis anki fd-android fd-auxio fd-binaryeye fd-calendar amaze keepass droidify etar fd-filemanager fd-fitness fd-k9 fd-minetest fd-mpv fd-netguard fd-notes fd-stk fd-tasks fd-tusky fd-uhabits markor newpipe ooniprobe——**24/24 仍亮,零回退**。
>
>  · **新亮 3 个**:fd-catima(欢迎使用 Catima;J7b AppWidget+Search)、opencamera(对焦提示;J7b 电池 sticky)、fd-feeder(「所有订阅源」;J7b Vibrator mLock)。
>
>  · flaky 键本轮亮:antennapod、fd-noice(登记表内,不计新增)。
>
>  · 活着但不亮:fd-app、fd-AppManager、noice、termux、fd-shatteredpixeldungeon、fd-organicmaps 白屏,fd-mobile 黑屏,fd-gallery、toutiao、wikipedia 在桌面;fd-seal app_failed(输入未修,预测里就标为阻塞)。
>
> **冻结**:Vibrator(VibratorFetcher mLock)现在有 fd-reader 过墙(日志)+ fd-feeder t20 亮,够条件——cc-t3 先把它拆成只含这一项的独立文件再出登记稿。AppWidget、Search、电池 sticky 各只有 1 个亮的 app,继续等。
>
> **统一态**:U6 零回退、+3,**采纳为新统一态**。在跑的两个短窗(5cd T7d、61b N7)照旧回滚到 U5;两个窗口结束后,由 cc-t3 用 deploy_generation 把 U6(J7b 381110a6 + T7c 27 镜像 + stubs 366acc27)在三块板上固化并核 runtime-fingerprint 逐件一致,之后所有短窗的回滚目标改为 U6。cx-bms 按冻结 CSV b9a414ed 打分(首墙用 first_fatal.py)。

## 66 个 key 一张表(facts 行 + 外环 t20 结论)

| aegis | `aegis                shots 2/2  alive t5=yes t20=yes  child_hilog=21676  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| anki | `anki                 shots 2/2  alive t5=yes t20=yes  child_hilog=71912  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| antennapod | `antennapod           shots 2/2  alive t5=yes t20=yes  child_hilog=33811  foreground_unconfirmed` | 亮(flaky 键,本轮亮,不计新增) |
| burgerking | `burgerking           shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-AppManager | `fd-AppManager        shots 2/2  alive t5=yes t20=yes  child_hilog=25166  foreground_unconfirmed` | 未亮(活着但不亮) |
| fd-android | `fd-android           shots 2/2  alive t5=yes t20=yes  child_hilog=65781  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-api | `fd-api               shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-app | `fd-app               shots 2/2  alive t5=yes t20=yes  child_hilog=18306  foreground_unconfirmed` | 未亮(活着但不亮) |
| fd-auxio | `fd-auxio             shots 2/2  alive t5=yes t20=yes  child_hilog=37837  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-binaryeye | `fd-binaryeye         shots 2/2  alive t5=yes t20=yes  child_hilog=27653  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-breezyweather | `fd-breezyweather     shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-calendar | `fd-calendar          shots 2/2  alive t5=yes t20=yes  child_hilog=26543  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-catima | `fd-catima            shots 2/2  alive t5=yes t20=yes  child_hilog=19391  foreground_unconfirmed` | 亮(新亮 3 个之一) |
| fd-client | `fd-client            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-com-amaze-filemanager | `fd-com-amaze-filemanager shots 2/2  alive t5=yes t20=yes  child_hilog=30939  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-com-kunzisoft-keepass-libre | `fd-com-kunzisoft-keepass-libre shots 2/2  alive t5=yes t20=yes  child_hilog=29211  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-droidify | `fd-droidify          shots 2/2  alive t5=yes t20=yes  child_hilog=34687  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-etar | `fd-etar              shots 2/2  alive t5=yes t20=yes  child_hilog=24850  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-feeder | `fd-feeder            shots 2/2  alive t5=yes t20=yes  child_hilog=45559  foreground_unconfirmed` | 亮(新亮 3 个之一) |
| fd-fennec_fdroid | `fd-fennec_fdroid     shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-filemanager | `fd-filemanager       shots 2/2  alive t5=yes t20=yes  child_hilog=47861  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-fitness | `fd-fitness           shots 2/2  alive t5=yes t20=yes  child_hilog=37478  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-fluffychat | `fd-fluffychat        shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-gallery | `fd-gallery           shots 2/2  alive t5=yes t20=yes  child_hilog=17813  foreground_unconfirmed` | 未亮(活着但不亮) |
| fd-im-vector-app | `fd-im-vector-app     shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-immich | `fd-immich            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-k9 | `fd-k9                shots 2/2  alive t5=yes t20=yes  child_hilog=65584  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-kitchenowl | `fd-kitchenowl        shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-libre | `fd-libre             shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-libretube | `fd-libretube         shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-meet | `fd-meet              shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-minetest | `fd-minetest          shots 2/2  alive t5=yes t20=yes  child_hilog=10841  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-mobile | `fd-mobile            shots 2/2  alive t5=yes t20=yes  child_hilog=30921  foreground_unconfirmed` | 未亮(活着但不亮) |
| fd-mpv | `fd-mpv               shots 2/2  alive t5=yes t20=yes  child_hilog=11004  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-musicplayer | `fd-musicplayer       shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-netguard | `fd-netguard          shots 2/2  alive t5=yes t20=yes  child_hilog=13514  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-noice | `fd-noice             shots 2/2  alive t5=yes t20=yes  child_hilog=30535  foreground_unconfirmed` | 亮(flaky 键,本轮亮,不计新增) |
| fd-notes | `fd-notes             shots 2/2  alive t5=yes t20=yes  child_hilog=21930  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-organicmaps | `fd-organicmaps       shots 2/2  alive t5=yes t20=yes  child_hilog=50159  batch_interrupted` | 未亮(活着但不亮) |
| fd-plus | `fd-plus              shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-reader | `fd-reader            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-saber | `fd-saber             shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-seal | `fd-seal              shots 0/0  alive t5=? t20=?  child_hilog=0  app_failed` | app_failed(输入未修,预测里就标为阻塞) |
| fd-shatteredpixeldungeon | `fd-shatteredpixeldungeon shots 2/2  alive t5=yes t20=yes  child_hilog=7846  foreground_unconfirmed` | 未亮(活着但不亮) |
| fd-stk | `fd-stk               shots 2/2  alive t5=yes t20=yes  child_hilog=6678  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-tasks | `fd-tasks             shots 2/2  alive t5=yes t20=yes  child_hilog=63035  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-tusky | `fd-tusky             shots 2/2  alive t5=yes t20=yes  child_hilog=62824  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-tutanota | `fd-tutanota          shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| fd-uhabits | `fd-uhabits           shots 2/2  alive t5=yes t20=yes  child_hilog=21181  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| fd-wifianalyzer | `fd-wifianalyzer      shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| firefox | `firefox              shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| localsend | `localsend            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| markor | `markor               shots 2/2  alive t5=yes t20=yes  child_hilog=17562  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| mcdonalds | `mcdonalds            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| mindustry | `mindustry            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| newpipe | `newpipe              shots 2/2  alive t5=yes t20=yes  child_hilog=39135  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| noice | `noice                shots 2/2  alive t5=yes t20=yes  child_hilog=29967  foreground_unconfirmed` | 未亮(活着但不亮) |
| ooniprobe | `ooniprobe            shots 2/2  alive t5=yes t20=yes  child_hilog=47610  foreground_unconfirmed` | 亮(U5 已亮 24 个之一) |
| opencamera | `opencamera           shots 2/2  alive t5=yes t20=yes  child_hilog=17598  foreground_unconfirmed` | 亮(新亮 3 个之一) |
| ppsspp | `ppsspp               shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| subwaysurfers | `subwaysurfers        shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| termux | `termux               shots 2/2  alive t5=yes t20=yes  child_hilog=7881  foreground_unconfirmed` | 未亮(活着但不亮) |
| toutiao | `toutiao              shots 2/2  alive t5=yes t20=no  child_hilog=53596  foreground_unconfirmed` | 未亮(活着但不亮) |
| vlc | `vlc                  shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |
| wikipedia | `wikipedia            shots 2/2  alive t5=yes t20=no  child_hilog=56324  foreground_unconfirmed` | 未亮(活着但不亮) |
| x | `x                    shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed` | 未签 |

**注**:只列 5cd 的 facts 行(22 keys);61b/5ea/5ea-resume 的 facts 行在各自目录的 facts.txt 里,与 5cd 同格式。外环 t20 结论按 04:36:43 签认:「亮」= U5 已亮 24 个 + 新亮 3 个 + flaky 键本轮亮;「未亮」= 活着但不亮(白屏/黑屏/桌面)或 app_failed。

## 数据来源

- U6 sweep: westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep/(5cd/61b/5ea/5ea-resume)
- 外环签认: 板 ACK(95) 04:36:43(逐字复制)
- 组成: U5 native N4-order 216b68fb + J7b 381110a6 + T7c 27 镜像 + stubs 366acc27 + 合包输入

## 外环后注(2026-10-01 05:20)

- 签认原文里「由 cc-t3 用 deploy_generation 固化 U6」已在 04:47 改为:U6 不单独固化,U7(= U6 + T7d)做成一个 generation 包一次固化。
- 严格打分见 `benchmark/2026-10-01-u6-scoring/`(对冻结 CSV b9a414ed:首墙 39/5/22,t20 46/1/19)。四份 facts 原文复制在本目录 `facts/`。
