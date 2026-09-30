# U7 Sweep — Evidence-First Report (2026-10-01, oc-t4, offline)

Dispatch (board ACK(95) 05:20, updated 06:39:59): benchmark/2026-10-01-u7-sweep/README.md (English, evidence-first) from the board's outer-loop sign-off text only. All three shards signed (5ea 06:33:44, 5cd 06:25:18, 61b 06:39:59); cx-bms formal scoring landed (see Scoring).


## Result

**U7 total: 34 lit across 66 keys** (5ea 15 [06:33:44] + 5cd 10 [06:25:18] + 61b 9 [06:39:59]).
Same-criteria comparison with U6 (antennapod and fd-noice counted as "intermittent"): **U7 = 32 + 2 intermittent (both lit this round), U6 = 27 + 2 intermittent. Net +5: fd-gallery, fd-libretube, fd-organicmaps, fd-reader, noice; zero regressions.** The three T7d-expected keys (gallery/libretube/noice) delivered; organicmaps and reader were unpredicted gains (pending cx-bms first-wall analysis). Alive but white/black: 7 (fd-app, fd-AppManager, fd-shatteredpixeldungeon, termux, wikipedia, x — white; fd-mobile — black) — the #80 first-frame wall.

U7 is adopted as the next unified-state candidate: it will be frozen onto all three boards by cx-t0's production executor; boards stay untouched until then.

## Composition

- **U6 base**: runtime J7b 381110a6 (unchanged), native N4-order, boot 36 files
- **T7d 27 images + stubs d8b2406e** (replaces T7c's 27 images + stubs 366acc27)
- **Merged input**: 5 split keys (x/burgerking/mcdonalds/firefox/subwaysurfers) merged single APKs (APKEditor 1.4.9 merge + apksigner v2/v3)
- **fd-seal/toutiao input**: quarantined (VM side 03:32, Mac side 04:58)

## 5ea Shard

**Run directory**: `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25/`

**`python3 scripts/lab/run_facts.py <run dir>` output** (verbatim, re-run now):

```
RUNTIME fingerprint=68b7fb016253 files=119 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
FROZEN checked=4 violations=0
BOOTIMAGE fingerprint=8fe2e5fd7d65 files=36 (boot-image-fingerprint.txt; not part of RUNTIME)
TOOL bms_batch=456dfc6f head=380e9450d manifest=71cd7ecd (plan.json tool)
aegis                shots 2/2  alive t5=yes t20=yes  child_hilog=21682  foreground_unconfirmed
anki                 shots 2/2  alive t5=yes t20=yes  child_hilog=71960  foreground_unconfirmed
antennapod           shots 2/2  alive t5=yes t20=yes  child_hilog=32739  foreground_unconfirmed
burgerking           shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-AppManager        shots 2/2  alive t5=yes t20=yes  child_hilog=25138  foreground_unconfirmed
fd-android           shots 2/2  alive t5=yes t20=yes  child_hilog=64459  foreground_unconfirmed
fd-api               shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-app               shots 2/2  alive t5=yes t20=yes  child_hilog=18346  foreground_unconfirmed
fd-auxio             shots 2/2  alive t5=yes t20=yes  child_hilog=37401  foreground_unconfirmed
fd-binaryeye         shots 2/2  alive t5=yes t20=yes  child_hilog=27638  foreground_unconfirmed
fd-breezyweather     shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-calendar          shots 2/2  alive t5=yes t20=yes  child_hilog=26502  foreground_unconfirmed
fd-catima            shots 2/2  alive t5=yes t20=yes  child_hilog=19413  foreground_unconfirmed
fd-client            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-com-amaze-filemanager shots 2/2  alive t5=yes t20=yes  child_hilog=30877  foreground_unconfirmed
fd-com-kunzisoft-keepass-libre shots 2/2  alive t5=yes t20=yes  child_hilog=28362  foreground_unconfirmed
fd-droidify          shots 2/2  alive t5=yes t20=yes  child_hilog=34477  foreground_unconfirmed
fd-etar              shots 2/2  alive t5=yes t20=yes  child_hilog=24831  foreground_unconfirmed
fd-feeder            shots 2/2  alive t5=yes t20=yes  child_hilog=45574  foreground_unconfirmed
fd-fennec_fdroid     shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-filemanager       shots 2/2  alive t5=yes t20=yes  child_hilog=38642  foreground_unconfirmed
fd-fitness           shots 2/2  alive t5=yes t20=yes  child_hilog=37407  foreground_unconfirmed
TOTAL keys=22 screenshots_captured=44/44 alive_t5=17 alive_t20=17
```

**Outer-loop sign-off** (verbatim, from ACK(95) 06:33:44):

> **U7 5ea 片正式签认**(补签,见下条 R2)。运行目录 westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5ea/20261001T054212-a6397b25;run_facts.py 原样(身份+总计):【RUNTIME fingerprint=68b7fb016253 files=119;BOOTIMAGE fingerprint=8fe2e5fd7d65 files=36;TOOL bms_batch=456dfc6f head=380e9450d manifest=71cd7ecd;TOTAL keys=22 screenshots_captured=44/44 alive_t5=17 alive_t20=17;】FROZEN checked=4 violations=0。contact_sheet 读全部 22 张 t20:
>
>  · **亮 15**:aegis(欢迎使用)anki(AnkiDroid 工具栏)antennapod(欢迎使用 AntennaPod;历史上时亮时不亮)fd-android(更新数据库)fd-auxio fd-binaryeye(扫码)fd-calendar(九月)fd-catima(欢迎使用)fd-com-amaze-filemanager fd-com-kunzisoft-keepass-libre(KeePassDX)fd-droidify fd-etar(2026年9月)fd-feeder(所有订阅源)fd-filemanager fd-fitness(设置参数)。
>
>  · 不亮 7:桌面 5(burgerking fd-api fd-breezyweather fd-client fd-fennec_fdroid);活着但白 2(fd-app fd-AppManager)。**活着 17 ≠ 亮 15**。
>
>  · 对 U6 同 22 key(U6 5cd 片):亮集合完全相同,零回退、零增量。

**Lit list** (15, from the sign-off, NOT from alive count): aegis anki antennapod fd-android fd-auxio fd-binaryeye fd-calendar fd-catima fd-com-amaze-filemanager fd-com-kunzisoft-keepass-libre fd-droidify fd-etar fd-feeder fd-filemanager fd-fitness

**Not lit list** (7): burgerking fd-api fd-breezyweather fd-client fd-fennec_fdroid (desktop); fd-app fd-AppManager (alive but white). **alive_t20 17 (lit 15 + white 2) ≠ lit 15**.

## 5cd Shard

**Run directory**: `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd/20261001T054910-73c67347/` (main) + `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/5cd-resume/20261001T061216-7af5a7e8/` (resume)

**`python3 scripts/lab/run_facts.py <run dir>` output** (verbatim, re-run now):

Main:

```
RUNTIME fingerprint=68b7fb016253 files=119 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
FROZEN checked=4 violations=0
BOOTIMAGE fingerprint=8fe2e5fd7d65 files=36 (boot-image-fingerprint.txt; not part of RUNTIME)
TOOL bms_batch=456dfc6f head=7cf1908d6 manifest=71cd7ecd (plan.json tool)
fd-fluffychat        shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-gallery           shots 2/2  alive t5=yes t20=yes  child_hilog=44694  foreground_unconfirmed
fd-im-vector-app     shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-immich            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-k9                shots 2/2  alive t5=yes t20=yes  child_hilog=63846  foreground_unconfirmed
fd-kitchenowl        shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-libre             shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-libretube         shots 2/2  alive t5=yes t20=yes  child_hilog=31033  foreground_unconfirmed
fd-meet              shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-minetest          shots 2/2  alive t5=yes t20=yes  child_hilog=10952  foreground_unconfirmed
fd-mpv               shots 2/2  alive t5=yes t20=yes  child_hilog=11008  foreground_unconfirmed
fd-musicplayer       shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-netguard          shots 2/2  alive t5=yes t20=yes  child_hilog=13542  foreground_unconfirmed
fd-noice             shots 2/2  alive t5=yes t20=yes  child_hilog=31229  foreground_unconfirmed
fd-notes             shots 2/2  alive t5=yes t20=yes  child_hilog=21946  foreground_unconfirmed
fd-organicmaps       shots 2/2  alive t5=yes t20=yes  child_hilog=57613  batch_interrupted
TOTAL keys=16 screenshots_captured=32/32 alive_t5=9 alive_t20=9
```

Resume:

```
RUNTIME fingerprint=68b7fb016253 files=119 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
FROZEN checked=4 violations=0
BOOTIMAGE fingerprint=8fe2e5fd7d65 files=36 (boot-image-fingerprint.txt; not part of RUNTIME)
TOOL bms_batch=456dfc6f head=1411276f5 manifest=71cd7ecd (plan.json tool)
fd-mobile            shots 2/2  alive t5=yes t20=yes  child_hilog=30926  foreground_unconfirmed
fd-plus              shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-reader            shots 2/2  alive t5=yes t20=yes  child_hilog=54513  foreground_unconfirmed
fd-saber             shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-seal              shots 0/0  alive t5=? t20=?  child_hilog=0  app_failed
fd-shatteredpixeldungeon shots 2/2  alive t5=yes t20=yes  child_hilog=7848  foreground_unconfirmed
TOTAL keys=6 screenshots_captured=10/10 alive_t5=3 alive_t20=3 alive_unknown=1
```

**Outer-loop sign-off** (verbatim, from ACK(95) 06:25:18):

> U7 5cd 片读图签认(contact_sheet 读全部 t20)。facts 原样(run_facts.py,现已带身份行):主段【RUNTIME fingerprint=68b7fb016253 files=119 (runtime-fingerprint.txt; compare before blaming the JAR across boards) BOOTIMAGE fingerprint=8fe2e5fd7d65 files=36 (boot-image-fingerprint.txt; not part of RUNTIME) TOOL bms_batch=456dfc6f head=7cf1908d6 manifest=71cd7ecd (plan.json tool) TOTAL keys=16 screenshots_captured=32/32 alive_t5=9 alive_t20=9 】resume【TOTAL keys=6 screenshots_captured=10/10 alive_t5=3 alive_t20=3 alive_unknown=1 RUNTIME/BOOTIMAGE 同上】。

**Lit list** (10, from the sign-off continuation lines 5278-5281, NOT from alive count): fd-gallery fd-k9 fd-libretube fd-minetest fd-mpv fd-netguard fd-noice fd-notes fd-organicmaps fd-reader

**Not lit list** (12, from the sign-off continuation): fd-fluffychat fd-im-vector-app fd-immich fd-kitchenowl fd-libre fd-meet fd-musicplayer fd-plus fd-saber (desktop); fd-mobile (black); fd-shatteredpixeldungeon (white); fd-seal (app_failed, input blocked)

## 61b Shard

**Run directory**: `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269/` (rollback byte_identical, 0 residual mounts)

**`python3 scripts/lab/run_facts.py <run dir>` output** (verbatim, re-run now):

```
RUNTIME fingerprint=68b7fb016253 files=119 (runtime-fingerprint.txt; compare before blaming the JAR across boards)
FROZEN checked=4 violations=0
BOOTIMAGE fingerprint=8fe2e5fd7d65 files=36 (boot-image-fingerprint.txt; not part of RUNTIME)
TOOL bms_batch=456dfc6f head=f9200da2b manifest=71cd7ecd (plan.json tool)
fd-stk               shots 2/2  alive t5=yes t20=yes  child_hilog=6674  foreground_unconfirmed
fd-tasks             shots 2/2  alive t5=yes t20=yes  child_hilog=63262  foreground_unconfirmed
fd-tusky             shots 2/2  alive t5=yes t20=yes  child_hilog=62176  foreground_unconfirmed
fd-tutanota          shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-uhabits           shots 2/2  alive t5=yes t20=yes  child_hilog=21283  foreground_unconfirmed
fd-wifianalyzer      shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
firefox              shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
localsend            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
markor               shots 2/2  alive t5=yes t20=yes  child_hilog=17559  foreground_unconfirmed
mcdonalds            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
mindustry            shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
newpipe              shots 2/2  alive t5=yes t20=yes  child_hilog=39346  foreground_unconfirmed
noice                shots 2/2  alive t5=yes t20=yes  child_hilog=31008  foreground_unconfirmed
ooniprobe            shots 2/2  alive t5=yes t20=yes  child_hilog=47020  foreground_unconfirmed
opencamera           shots 2/2  alive t5=yes t20=yes  child_hilog=17141  foreground_unconfirmed
ppsspp               shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
subwaysurfers        shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
termux               shots 2/2  alive t5=yes t20=yes  child_hilog=7881  foreground_unconfirmed
toutiao              shots 2/2  alive t5=yes t20=no  child_hilog=53000  foreground_unconfirmed
vlc                  shots 2/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
wikipedia            shots 2/2  alive t5=yes t20=yes  child_hilog=56131  foreground_unconfirmed
x                    shots 2/2  alive t5=yes t20=yes  child_hilog=72819  foreground_unconfirmed
TOTAL keys=22 screenshots_captured=44/44 alive_t5=13 alive_t20=12
```

**Outer-loop sign-off** (verbatim, from ACK(95) 06:39:59):

> **U7 61b 片签认 + U7 全量总数**。运行目录 westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/20261001T060453-7a751269(回滚 byte_identical、0 残留 mount);run_facts.py 原样:【RUNTIME fingerprint=68b7fb016253 files=119;FROZEN checked=4 violations=0;BOOTIMAGE fingerprint=8fe2e5fd7d65 files=36;TOOL bms_batch=456dfc6f head=f9200da2b manifest=71cd7ecd;TOTAL keys=22 screenshots_captured=44/44 alive_t5=13 alive_t20=12;】。contact_sheet 读全部 22 张 t20:
>
>  · **亮 9**:fd-stk(SuperTuxKart 闪屏)fd-tasks(添加账号)fd-tusky(登录页)fd-uhabits(Loop 欢迎)markor(主界面)newpipe(直播标签栏,内容区空)noice(欢迎)ooniprobe(什么是 OONI Probe)opencamera(存储权限对话框)。
>
>  · 不亮 13:桌面 10(fd-tutanota fd-wifianalyzer firefox localsend mcdonalds mindustry ppsspp subwaysurfers vlc toutiao——toutiao t5 活、t20 已退);活着但白 3(termux wikipedia x)。
>
>  · 对 U6 同 22 key(U6 61b 亮 8):**+noice**,其余 8 个全保持,零回退。
>
> **U7 三片合计 66 key:亮 34**(5ea 15 [06:33:44] + 5cd 10 [06:25:18] + 61b 9)。按 U6 同一口径(antennapod、fd-noice 记「时亮」):U7 = 32 + 2 时亮(本轮两个都亮),U6 = 27 + 2 时亮。**净增 5:fd-gallery fd-libretube fd-organicmaps fd-reader noice;零回退**。T7d 预期的 gallery/libretube/noice 三个兑现;organicmaps、reader 在预测外(待 cx-bms 解释)。活着但白/黑仍 7 个:fd-app fd-AppManager fd-shatteredpixeldungeon termux wikipedia x(白)+ fd-mobile(黑)——#80 的首帧墙。
>
> U7 采认为下一统一态候选:按 cx-t0 的生产执行器固化(三板),固化前不动板;cx-bms 正式 66 key 打分,oc-t4 补 README 61b 节。

**Lit list** (9, from the sign-off, NOT from alive count): fd-stk fd-tasks fd-tusky fd-uhabits markor newpipe noice ooniprobe opencamera

**Not lit list** (13): fd-tutanota fd-wifianalyzer firefox localsend mcdonalds mindustry ppsspp subwaysurfers vlc toutiao (desktop; toutiao alive at t5, gone by t20); termux wikipedia x (alive but white). **alive_t20 12 (lit 9 + white 3) ≠ lit 9** (alive_t5 13 — toutiao alive at t5, gone by t20).

## cx-bms Scoring

Formal 66-key three-axis scoring is out: [`benchmark/2026-10-01-u7-scoring/formal-66/results.json`](../2026-10-01-u7-scoring/formal-66/results.json) (landed d155dcdb5).

Numbers verbatim from cx-bms PROGRESS(95) 06:49:27:

- **t20 axis: 59 hit / 1 false positive / 6 unknown** — known-denominator 60 = **98.33%**, full 66 = **89.39%**. The single t20 false positive is **organicmaps**: predicted not-lit, but its own splash screen lit. **reader** stays frozen unknown (no back-filling a hit).
- **first-wall axis: 48 hit / 18 unknown** — 0 new first-wall misses; the 18 unknowns are listed separately as SCAN-GAPS.
- **checkpoint axis: 51 NA / 15 unknown** — no named positive-call receipts, so no UI-assisted scoring.
- reader mechanism-matches but the named positive call was never recorded → unknown; organicmaps process vanishes without cause in both U6 and U7 → cannot claim the first wall moved or which T7d method fixed it → explicitly unknown.
- fd-plus first termination is the MapInfoLayer null at 60342→60357; the earlier caught ColorMatrix.set at 50986 is not substituted for it.

## Notes

- **No self-judgment**: lit/not-lit lists are copied verbatim from the outer-loop sign-off; oc-t4 does not judge.
- **Sources**: board ACK(95) 06:33:44 (5ea formal sign-off), cc-wiki PROGRESS(80) 06:08:37 (5ea facts), ACK(95) 06:25:18 (5cd sign-off), cc-wiki PROGRESS(80) 06:19:27 (5cd run directories), ACK(95) 06:39:59 (61b sign-off + U7 totals), cx-bms PROGRESS(95) 06:49:27 (formal scoring).
