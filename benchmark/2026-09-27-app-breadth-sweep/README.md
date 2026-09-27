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

**Swept 56 (batch1 19 incl. wikipedia + b2 37) · LIT 13 · 点亮率 ~23%.** 尾部 10 个商业 app 因板中途
掉线后补扫(见文末)。判据 = **逐张读图**(自动化 `alive=yes` 只表示 appspawn-x child 起活,不等于点亮;
未亮 app 屏幕停在 OH host launcher 兜底,进程活但无窗口)。

### 能力边界（一句话）
**轻量本地 View app 点亮;重度原生渲染 / GL / 浏览器 / Flutter / 多媒体卡在窗口·首帧 bring-up。**

### LIT 13（全名）
wikipedia · termux · ooniprobe · antennapod · aegis · fd-AppManager · fd-auxio ·
fd-com-amaze-filemanager · fd-com-kunzisoft-keepass-libre · fd-droidify · fd-fitness · fd-netguard · fd-noice

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
- **(a) OH 6.1.0.31 不提供 libGLESv1_CM.so**（legacy GLES 1.x fixed-function Common-Lite profile）；只有
  GLESv2/v3（可编程 shader pipeline）。STK 的报错本身即经验证据（linker 在 search path 里找不到该文件）。
- **(b) libSDL2.so DT_NEEDED 了 libGLESv1_CM.so**（与 libGLESv2.so 并列），且 **`FLAGS: BIND_NOW`（eager
  绑定）** + UND 引用 10 个 GLESv1-only fixed-function 符号（glMatrixMode/glColor4f/glEnableClientState/
  glDisableClientState/glLoadIdentity/glOrthof/glColorPointer/glTexCoordPointer/glTexEnvf/glVertexPointer）
  + 4 个 OES 扩展（glBindFramebufferOES/glGenFramebuffersOES/glBlendEquationOES/glDrawTexfOES）。
- **判定**：见 `glesv1cm-crux/DECISION.md`。纯 symlink→libGLESv2 **不够**（BIND_NOW 会因这 14 个符号在 v2
  不存在而 "cannot locate symbol"）；**薄 stub**（只导出这 14 个 no-op 符号）可满足加载，STK 走 GLES3 路径
  运行时不调 fixed-function → 不崩；**gl4es 不需要**。快测脚本 `glesv1cm-crux/`。

### 尾部 10（板回挂后补扫）
mcdonalds(重扫) · burgerking · subwaysurfers · firefox · vlc · localsend · ppsspp · mindustry · x · noice
→ 结果见本表更新 / RESULTS.md。
