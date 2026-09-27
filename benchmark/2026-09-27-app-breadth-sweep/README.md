# 2026-09-27 app-breadth sweep automation (#48 horizontal) — board 5ea34a45 ONLY
Count how many apps the current Westlake runtime lights up (to first usable UI). Automation to stage+
launch each app, wait ~30s, screenshot + capture child stderr, classify LIT vs BLOCKED(category), clean
up, and tally. Board **5ea34a45 only** — hard-guarded; never 61b06572 (Toutiao) / 5cd1e3dd (device farm).

| Path | What |
|------|------|
| scripts/sweep_app.sh | stage+launch ONE app-key via probe_source_app.py (serial-pinned to 5ea34a45), wait, snapshot, capture child stderr, classify LIT/BLOCKED(category), cleanup. ABORTS unless SERIAL=5ea34a45…1123012c |
| scripts/sweep_batch.sh | loop sweep_app.sh over a keys file; accumulate results.tsv + LIT/BLOCKED counts + lit-rate + blocker-category histogram |
| scripts/sweep_config.5ea34a45.sh.template | the 5ea34a45 base-runtime candidate paths the sweep needs (HDC/SERIAL/PROBE/WORKSPACE/WESTLAKE_SOURCE/FRAMEWORK_REPORT/HOST_BUILD/WEBVIEW_INPUT/SOURCE_WEBVIEW_BUILD/APP_INPUT_ROOT/OUT_ROOT) — fill from the assembled 5ea34a45 runtime |
| scripts/keys.fdroid.txt | 66 open/F-Droid app keys (fd-* ≈ fdroid100 + wikipedia/newpipe/anki/… ) — sweep these FIRST (high hit rate) |
| scripts/keys.commercial.txt | 37 co-* commercial keys (heavy, anti-tamper — low hit; sweep last) |
| RESULTS.md | **2026-09-27 run result table**: 56 apps classified, LIT 13 (~23%), BLOCKED 43 by category; markor root-cause (per-app window bring-up, not staging); interrupted by 5ea34a45 detach after mcdonalds |
| screens/&lt;key&gt;.jpeg | per-app first-UI screenshot (the sole LIT/BLOCKED discriminator — read visually) |

Classify: LIT = process alive after WAIT + render markers in child stderr (ANativeWindow/onResume/
render/prewrapped/drawFrame) [+ screenshot saved for manual confirm]; BLOCKED = fatal crash (category:
mallocng-smash / telephony-NPE / flutter-impeller / native-symbol / crash) OR alive-no-render(stuck/
black) OR exited-no-crash-marker.

EXECUTION BOUNDARY: staging uses the board runner's probe_source_app.py with the assembled 5ea34a45
runtime-candidate inputs (framework/host/webview/shim builds). The board runner (claude-2/codex-2) owns
that assembled runtime + the board; run sweep_batch.sh after sourcing sweep_config.5ea34a45.sh (filled
with the 5ea34a45 candidate paths). claude-3 aggregates/classifies the results.tsv. Prioritize
keys.fdroid.txt, then keys.commercial.txt. Skip already-lit (wikipedia/toutiao/mcdonalds) + parked
deep-walls (localsend/X) or let them re-confirm.

---

## 收官总表 (2026-09-27, board 5ea34a45, LocalSend framework-2 base runtime a2hlab-framework-cab462ff)

**Swept 66 launches (batch1 19 incl. wikipedia + b2 37 + tail 10) · 13 distinct apps LIT · 点亮率 ~23%
(15 LIT launches / 66; 13 distinct — `noice`≡`fd-noice`, and `burgerking` renders McDonald's, see anomaly).**
判据 = **逐张读图**(自动化 `alive=yes` 只表示 appspawn-x child 起活,不等于点亮;未亮 app 屏幕停在 OH host
launcher 兜底,进程活但无窗口)。

> 运维坑(尾部补扫时踩): systemdump 后板会**熄屏→重锁**,`snapshot_display` 抓到黑屏/锁屏(多张字节全同=同一
> 黑帧)。修复:`power-shell wakeup` 只点亮不解锁;真解需 `uinput -T` 上滑 + `power-shell timeout -o 3600000`
> (1h 熄屏超时,防扫描中重锁)。

### 能力边界（一句话）
**轻量本地 View app 点亮;重度原生渲染 / GL / 浏览器 / Flutter / 多媒体 / 游戏卡在窗口·首帧 bring-up。**

### LIT 13 distinct（全名）
wikipedia · termux · ooniprobe · antennapod · aegis · fd-AppManager · fd-auxio ·
fd-com-amaze-filemanager · fd-com-kunzisoft-keepass-libre · fd-droidify · fd-fitness · fd-netguard · fd-noice
（`noice` = `fd-noice` 同一 app 重复,不重复计。`burgerking` key **不**计为独立胜绩,见异常。）

### 异常: burgerking key = McDonald's APK 错标 + 同一 McD app 两 key 两结果
- `burgerking.jpeg` 渲染的登录页 T&C 明写 **"McDonald's Terms & Conditions" + "California Privacy Notice"**
  → `burgerking` 这个 app-input 实为**麦当劳 APK 错标 key**,不是独立 Burger King 胜绩。
- 更值一提:**同一麦当劳 app,`mcdonalds` key 回落 host launcher(未亮),`burgerking` key 渲染出登录页(亮)**。
  同 app 两 key 两结果 ⇒ 差异在**启动路径 / launch Activity / 基座**,不在 app 本身 —— 佐证本轮主结论
  "窗口/Activity bring-up + 基座是变量,而非 app 天然不兼容"。

### 尾部 10（板回挂后补扫,已完成）
LIT 2 launches(`burgerking`=McD 登录[见异常,不计独立]、`noice`=fd-noice 重复);未亮 8(全 host-launcher):
`mcdonalds`(base-mismatch,同 toutiao)、`subwaysurfers`(Unity 游戏)、`firefox`(浏览器)、`vlc`(媒体)、
`localsend`(Flutter Impeller 深墙)、`ppsspp`(PSP 模拟器 GL)、`mindustry`(libGDX 游戏)、`x`(Twitter WebView 深墙)。

### 未亮 43 按现象分类
| 类别 | 数量 | 说明 / 样例 |
|------|------|------------|
| host-launcher 兜底 / alive-no-render | ~38 | 进程活但 RS 渲染树无该 app 的 `*.MainActivity_content` 节点 = 窗口/Activity 起栈静默失败（**非 staging bug**，见下）。anki/newpipe/markor/opencamera/fd-fennec(Firefox)/fd-im-vector(Element)/fd-libretube/fd-minetest/fd-mpv/fd-organicmaps(GL 地图)/fd-tusky/fd-shatteredpixeldungeon(游戏)/… |
| native-lib 缺失（**金发现**，见下节） | 1 | fd-stk(SuperTuxKart) 渲染自己 SDL 弹窗报缺 `libGLESv1_CM.so` |
| black-render | 1 | fd-mobile（拿到窗口，内容画黑） |
| blank-white | 1 | fd-client（拿到窗口，无内容） |
| exited-to-desktop | 1 | fd-binaryeye（进程没留住，掉回 OS 桌面；二维码扫描吃相机 HAL） |
| base-mismatch | 1 | toutiao（此板用通用 LocalSend 基座，头条需自己的 delivery 基座@61b06572，非根本墙） |

### 主墙根因（markor probe 取证）
**不是 staging bug。** probe 正确 stage APK 并 direct-launch 精确 `MainActivity`（`ASX_DIRECT_LAUNCH=1`、
`host_spawn result=0`、child alive、touchfwd 挂上）。决定性证据（OH RenderService hilog）：**只有点亮的
app 在 RS 树里有 `*.MainActivity_content` 渲染节点**（auxio/aegis/ooniprobe/wikipedia/antennapod），未亮
app 进程活但**从没创建窗口/渲染节点**。同管线 13/56 点亮 ⇒ 墙是**逐-app 运行时窗口/Activity 起栈不兼容**。

### 🏆 GLESv1_CM 金发现（单列，最可行动）
`fd-stk`（SuperTuxKart）是唯一渲染了**自己错误 UI** 的未亮 app：SDL 弹窗
`Error loading shared library libGLESv1_CM.so: (needed by .../libSDL2.so)`。
- **(a) OH 6.1.0.31 无任何 Khronos GLESv1 表面**（机测 5ea34a45）：`/system/lib64/ndk/libGLESv2.so` 在 app
  namespace 搜索路径上(所以 libSDL2 的另一 DT_NEEDED libGLESv2.so 本就满足,报错只提 GLESv1_CM);但**无**
  libGLESv1_CM.so,且 `/vendor/lib64/chipsetsdk/libGLESv1_impl.so`(Mali 后端 16.7MB)`readelf --dyn-syms`
  **导出 0 个 gl\* 符号**(内部 backend,非 Khronos 名),且该 vendor 目录**不在** app namespace 搜索路径上。
  → **设备上没有任何库导出这 14 个 GLESv1 符号可供 symlink**。
- **(b) libSDL2.so DT_NEEDED libGLESv1_CM.so**(与 libGLESv2.so 并列),**`FLAGS: BIND_NOW`(eager)** + UND 引用
  10 个 GLESv1-only fixed-function 符号(glMatrixMode/glColor4f/glEnableClientState/glDisableClientState/
  glLoadIdentity/glOrthof/glColorPointer/glTexCoordPointer/glTexEnvf/glVertexPointer)+ 4 个 OES 扩展
  (glBindFramebufferOES/glGenFramebuffersOES/glBlendEquationOES/glDrawTexfOES)。libmain.so 不直接引用 gl\*。
- **判定(机测坐实,见 `glesv1cm-crux/DECISION.md`)**:**任何 symlink 都不行**(设备无库导出这 14 符号 → BIND_NOW
  "cannot locate symbol");**薄 stub 是唯一路且已建**(`glesv1cm-crux/libGLESv1_CM.so.stub`,14632B,sha256
  `a1ae3950…b37bf`,精确导出 14 符号,被调时打 stderr);**gl4es 不需要**(STK 走 GLES3)。
- **部署(需 board-runner 一行集成)**:改 APK 被 probe 拒(`Changed original APK input`),per-run staged 目录
  临时不可预置 → 把 stub 加进 fd-stk 的 `native_libraries`(app-inputs.lock.json,指向 stub sha256)让 probe
  staging 带上,再正常带窗口跑 → 定论 STK 点亮 / 是否真调 fixed-function。stub 是**所有 SDL2/ES1 app 通用一文件 shim**。
