# 外环交接(2026-10-11 ~17:00,Claude → Codex)

先读 `AGENTS.md`、`.octos/KNOWLEDGE-DIGEST.md`(末尾 10 行是今天的结论)、`.octos/OPS-RUNBOOK.md`。黑板:`.octos/boards/app-lighting.md`,按 `#91` 筛 `PROGRESS(91)`/`ACK(91)`。

## 1. 现在在跑的两件事

### A. 61b v1 封板(关键路径,预计 18:10–18:20 完)
- v1 = 统一态 128 app + 头条 Route B + 开机自启,**Permissive**(cmdline `androidboot.selinux=permissive`,用户定)。不带 BoatAttack。
- 61b 14:28 systemdump 死机掉 USB,用户 16:47 重启;冷启无 Mac 自走到 Route B `receipt state=WAITING_FOR_DESKTOP_TAP`(boot 68db8bff)。用户说不深究死因。
- 旧 acceptance/window-auth 绑旧 boot b43cd5fd → 失效。16:52 已批 cc-wiki(w9:p8)走 **②全新 seal run**:driver 快照 + sepolicy 门 → 净重启 → 停在 acceptance 等签 → 20-key run → regression_review 等签 → seal_snapshot → seal.json。
- **plan_sha = `04d640436295c02fb446188037be6d4f1c4444dcbd1fee6bed8b78aeefdd72c7`,不变**;`outer-drafts/authorization.json` 已签此值,不用动。
- 回归口径 = 用户批的方案 2:61b 跑 20 key(`benchmark/2026-10-10-demo-seal-61b/demo-manifest-20.json`)+ 5cd 全量 128 Permissive 预跑做交叉验证(master `54c3220a84`,`benchmark/2026-10-10-5cd-demo-regression/v1-permissive/full128-readout/`)。

### 你要签的两处(都在 westlake-harness-wiki 工作树 `benchmark/2026-10-10-demo-seal-61b/`)
1. **acceptance**(driver 停下时,cc-wiki 会贴 evidence + 新 boot_id):写 `seal-run-<新>/acceptance.json`,字段要齐——driver `scripts/lab/demo_seal_61b.py` L356–377:
   - `checks` 全 True:parent_init、socket_0660、hw_t20_lit、zz_t20_lit、toutiao_desktop_click_refresh_article;
   - `evidence`: `[{path, sha256}]`,每条 SHA 必须和盘上一致(用 driver 自己的 `pinned()` 核);
   - `boot_id` == 当前 boot;`plan_sha256` == 04d64043…;`no_mac_repair` True;
   - **`approved_by` 必须是字面量 `"outer(claude)"`**(driver L362/649/690/695 写死;改 driver 会改 plan_sha、要重签,这次封板别改,当角色名用,v1 后再改)。
   - **先亲眼看 HW/ZZ/头条截图再签**(截图是地面真相)。
   同时把 `outer-drafts/window-authorization.json` 的 `boot_id` 改成新 post-reboot boot,`expires_at` 留足。**两张一起签,只签一次**(用户:别重复签、攒批签)。
2. **regression_review**:同样走 reviewed()(要 checks + evidence)。判法:`judge_regression.sh` 看 diff + contact sheet + 抽看几张,不必每张看(用户:抽查即可)。离线预比(上一 boot)= 17 same / 3 suspect / 0 missing:newpipe、vlc 基线本就不亮(非回退);**fd-binaryeye 基线亮、现 suspect,签前必须看它的 t20 原图**。
- 封完:AGENTS.md 板子纪律加一行登记 61b 为演示板(零改动、只读巡检、解封只有用户批)。

### B. BoatAttack(用户重点)
- **已成功**:5cd 窗9 渲染 + 可交互(外环看图判;`westlake-harness-t3/benchmark/2026-10-11-boat-window9/win-A/boat-A-t45.jpeg`、`boat-A-touch.jpeg`)。配方与截图三坑见 DIGEST 末尾。
- cc-t3(w9:p2)16:46 锁 5cd 做「Boat 开机自起」无 Mac 演练(规格 `benchmark/2026-10-11-boat-autostart-seal/SPEC.md`,已批)。外环已定:runtime 用 stock 18763dd4、不 bind;adapter/jar 是全局件 → **v2 封板前要在空闲板跑 128 全量**(或请用户批子集)。演练截图出来要看图判。

## 2. 车道
| pane | 名 | 在做 |
|---|---|---|
| w9:p8 | cc-wiki (Claude) | 61b 全新 seal run |
| w9:p2 | cc-t3 (Claude) | 5cd Boat 自起演练 |
| w9:p4 | cx-t0 (codex) | 空闲 |
| w9:p7 | cx-bms (codex) | 空闲 |
| w9:p3 | oc-t4 | 空闲 |
- 派单只用 `scripts/lab/lane_send.sh <pane> '<单引号文本>'`(双引号里的反引号会被 zsh 执行)。
- cc 车道也是 Claude,额度耗尽会停。停了就把它在黑板最后的 PROGRESS 转给 codex 车道;注意 codex 会拒内存破坏/hook/二进制补丁类(AGENTS「例外」)。

## 3. 哨兵(一次性,触发后要重挂)
- 正哨:`~/workspace/octoscode/scripts/olp-watch-board.sh "$PWD/.octos/boards/app-lighting.md" "PROGRESS(91): 2026"`(带「: 2026」可跳过批跑分片的无时间戳行)。
- 负哨:`scripts/lab/lane_watch.sh w9:p8 w9:p2`。
- 用前台托管的后台任务跑;**别用 `&`/`disown`**(会断通知或被杀)。别 `pkill -f olp-watch-board`(会误杀进化环的 `改判 --harvest`/`R2 记档 --harvest` 两个常驻收割器)。数进程用 `pgrep -f 'olp-watch-board[.]sh.*PROGRESS'`(裸 pgrep 会匹配到自己)。

## 4. 封完后的待落库
cc-t3 哨兵 supervisor `dbe57d0cf9`、render-verify `00ec936238`、Boat 窗3–9 证据与工具(t3 工作树,最新 `63c332524c`)、recover-v4、place() 去重、preseal_healthcheck 适配新 recover 表 schema(现报假 WINDOW-BLOCKED)。用 `land.py`(自落车道要设 `LAND_REPO`)。

## 5. 用户长期规则(摘要)
- 推送到 a2hlab 已授权;commit 不加 Claude 署名行,不 `--no-verify`;仓库公开,不写密码/账号。
- 截图是地面真相;头条隐私同意**不替用户点**;状态问题先只读事实(`/proc/cmdline`、boot_id)再判断。
- 判证据要对的参照:「MUSL-SIGCHAIN signal:4」是 ART 例行行不是崩溃;errno13 ≠ SIGILL。
- 回复用户用中文。
