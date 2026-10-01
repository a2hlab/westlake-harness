# U10 window plan — SKELETON / DRAFT

**Status:** NOT runnable. This is the window skeleton (patrol dispatch ①). It fixes the gate, the
regression-control roster, the three-board sharding and the smoke spec. The **native合包 is now pinned**
(`bbe46462b`; compat `015aa3a6`, libnativeloader policy `621caec4`, appspawn-x host `62debf19`). Still DRAFT:
finalize the combined jar+native `runtime_fp`, the per-board keys files and the deploy/rollback argv (see
`finalize-checklist`).

Lead lane: cc-t3. Boards (all experiment boards since 2026-09-28): `5ea34a45…`, `5cd1e3dd…`, `61b0657200…`.
Discipline: 三板统一态、全量分片; one on-board task per board at a time; ≤45 min for a batch window; release
the lock the instant on-board work ends; screenshots are ground truth (ACK quotes `facts.txt` verbatim).

## 1. Candidate artifacts under test

| Layer | Artifact | SHA / id | State |
|---|---|---|---|
| JAR | `/system/android/framework/oh-adapter-runtime.jar` (U10) | `37465d6d7f5e3d7be52929c2b43faf99315f86f0c23cc70e4aa858cb2ff98c59` | built, deterministic (build-receipt-u10.json); jar-only runtime_fp `1833eb39872f`, boot `4db882a81732` |
| JAR (unchanged) | `/system/android/framework/adapter-mainline-stubs.jar` (T7e stubs) | `f3bcc9d7c76cb73487837d7ad92fccba3d595d313ada7403bed99c4f11c2a8c2` | unchanged from U9 (must stay) |
| native | libnativeloader policy: `native_bridge_policy.v1.json` shared_sonames `+= libstdc++.so` **only** (wall-1, master 504b66cea; **libjnigraphics deferred to U11**) | `621caec4` | staged (cx-bms) |
| native | compat: GNU `strerror_r` exposed to app namespace (firefox, fd-fennec_fdroid) | `015aa3a6` | staged (cx-bms) |
| native | appspawn-x host: `U10ShareResidentCompat` — `android_set_abort_message` abort-owner visibility (fd-meet); **no OpenSLES — deferred to U11** | `62debf19` | staged (cx-bms) |
| native | U10 native合包 (overall) | `bbe46462b` | staged (cx-bms) |

One generation, one window: JAR 37465d6d bound onto the runtime jar **+** the cx-bms native payload, deployed
together. Rollback target = **U9** (fingerprints `565fc6fdc116` / `a2919b793eb6`, `boot 4db882a81732`, 318
identity assertions — as given by outer ACK(90); the current signed unified state, **not** U8). Deploy mechanism
(`sweep_bind_deploy` multi-bind vs `deploy_generation --upgrade`) chosen with cx-bms when the native package
is staged.

## 2. Gate — `check_frozen` against the U10 candidates (before any deploy)

Run in the window worktree before `after_lock` binds anything; a mismatch refuses the deploy (do not land):

```
python3 scripts/lab/check_frozen.py \
  --registry   knowledge/frozen/frozen.json \
  --fingerprint $WORKSPACES/westlake-generation-u10-staging/runtime-fingerprint.txt \
  --package     $WORKSPACES/westlake-generation-u10-staging/<cx-bms U10 native generation dir> \
  --source-root $WORKSPACES/westlake-harness-walls \
  --git master
```

- `--fingerprint` — every path in the U10 runtime-fingerprint.txt that is a frozen artifact (FZ-001 libbms /
  libapk_installer, FZ-003/005 boot image + toolchain-built classes, FZ-006..008 BCP adapter stubs, etc.)
  must still carry its frozen sha256. The U10 jar (37465d6d) and the two added shared_sonames are **new**
  behaviour on non-frozen files, so they are not violations — but if the native合包 touches a frozen `.so`
  path, its sha must match the registry or be re-registered first (reason=platform/defect, single-variable
  `compare_runs`, every FZ evidence app re-lit, outer/user approval).
- `--source-root` + `--git master` — every frozen **source** file (FZ source records) must still resolve to
  its frozen git blob; U10's new source (Predicate.java, J10f defaults, split files) sits in non-frozen files.

**Gate result required before the window opens: `check_frozen` prints 0 violations.**

## 3. Three-board sharding — full unified-state sweep (166 keys)

Carry forward each key's **U9 board assignment** (from `benchmark/2026-10-01-u9-sweep/outer-signoff.json`
`shard` field) so every key is compared against its own prior round on the same board (apples-to-apples
regression). The window adds, per board, its beneficiaries + 3 canaries + the FZ-evidence controls that live
on that board. Each board runs its ~1/3 slice; one on-board task per board at a time.

| Board | Beneficiaries placed here | Role |
|---|---|---|
| `5ea34a45…` | `toutiao` (libstdc++ only; libjnigraphics→U11 — **first-wall-move, not lit**), `fd-meet` (abort-owner visibility via U10ShareResidentCompat), `fd-tutanota` (J10f defaults → **white window**, not lit) | native + jar |
| `5cd1e3dd…` | `firefox` (strerror_r), `cv2-com-nbossard-packlist` (Predicate, jar) | native + jar |
| `61b0657200…` | `fd-fennec_fdroid` (strerror_r) | native |

Native fixes are unified-state (identical on all three boards per `runtime-fingerprint.txt`), so spreading the
beneficiaries buys 3 independent board observations of one shared-layer change. `fd-plus` (Surface
software-lock) and `mindustry` (OpenSLES facade) are **not** U10 beneficiaries — both deferred to U11;
mindustry keeps its U9 `dead` verdict (prediction v3), so it runs in the sweep purely as a carry-forward key,
not a beneficiary. `fd-seal` included only if it installs on U10; drop at finalize if `bm install` fails.

## 4. Regression-control roster

### 4a. FZ-evidence apps (frozen behaviour must not regress)

These are already past a frozen wall with recorded t20 evidence; if any goes dark or its frozen API error
reappears, U10 broke a frozen fix — roll back. From `knowledge/frozen/frozen.json`:

| FZ | API (frozen behaviour) | Evidence apps (run on their U9 board) |
|---|---|---|
| FZ-001 | installer START_ABILITIES_FROM_BACKGROUND | fd-tusky, fd-k9, fd-android, fd-filemanager |
| FZ-002 | Android child ActivityThread 8 MiB pthread stack | fd-tusky, antennapod*, markor, fd-k9, fd-auxio, helloworld, zigzag |
| FZ-003 | AssetManager.nativeOpenAssetFd real PFD | newpipe, fd-uhabits* |
| FZ-004 | JAR-layer jar-verification provider | fd-droidify, fd-com-amaze-filemanager, antennapod* |
| FZ-005 | dex2oat-once toolchain | helloworld, zigzag, aegis, ooniprobe |
| FZ-006 | VibratorManager.getVibratorIds()→int[0] | fd-feeder, fd-reader |
| FZ-007 | boot-classpath tagsoup | fd-libretube, wikipedia* |
| FZ-008 | boot-classpath SSLSockets stub | noice*, wikipedia*, fd-noice* |

`*` = also in `flaky-keys.json` — judged by **log** (the frozen API failure stays absent, first fatal
unchanged), not by a one-run t20 verdict.

### 4b. Per-shard canaries (3 each; "lit in two rounds", non-flaky)

**Selection rule:** a canary is lit in the U9 sweep **and** independently lit before (FZ t20 evidence or the
prior sweep's `facts.txt` in `outer-signoff.json` `runs[]`), and is **not** in `flaky-keys.json`. Preference
to FZ-evidence apps (double-duty: stable control + frozen-API check). Confirmed lit in U9; the second-round
`facts.txt` cross-check is a finalize step.

| Board | Canaries | Second-round source |
|---|---|---|
| `5ea34a45…` | `aegis` (FZ-005), `fd-feeder` (FZ-006), `ooniprobe` (FZ-005) | frozen.json t20 + U9 5ea |
| `5cd1e3dd…` | `fd-droidify` (FZ-004), `markor` (FZ-002), `newpipe` (FZ-003) | frozen.json t20 + U9 5cd |
| `61b0657200…` | `fd-k9` (FZ-001/002), `fd-com-amaze-filemanager` (FZ-004), `fd-libretube` (FZ-007) | frozen.json t20 + U9 61b |

### 4c. Launch-only controls (every board, every window)

`helloworld`, `zigzag` (`knowledge/smoke/controls-apps.json`, FZ-002/005) — the activation smoke's always-lit
pair; if either fails the smoke, stop and retain the lock (bad deploy, not an app wall).

## 5. Smoke spec — `knowledge/smoke/u10.json`

Current draft asserts jar-only `runtime_fp 1833eb39872f` + jar sha 37465d6d + unchanged stubs f3bcc9d7, with
`helloworld`/`zigzag` launch-only and the N copy probe (libart/libopenjdkjvm single-copy, bridge/runtime ×2).
**Finalize:**
- replace `expect.runtime_fp` with the **combined jar+native** runtime_fp (self-computed from the U10 native
  manifest, same value filled into the plan and `u10.json`);
- add the native artifacts to `probe.files` (policy json + rebuilt `libapp_native_loader.so` sha);
- add per-beneficiary `fixes[]` markers once the native shim's log tags are known (cf. J10g `[J10g-WEBVIEW]`
  markers), e.g. a `[U10-NATIVE] libstdc++ exposed` tag on the toutiao/libflipped path.

## 6. offline_precheck (per board, `board_run.py` contract: expect.confirm / expect.refute)

- **hypothesis:** U10 (Predicate in the jar + libstdc++ in the app-inheritable shared_sonames — libjnigraphics
  → U11 — + strerror_r via compat / android_set_abort_message abort-owner visibility via U10ShareResidentCompat)
  clears each beneficiary's current first wall **generically** (shared layer), with no regression to
  controls/canaries/FZ apps. (OpenSLES and libjnigraphics → U11, so mindustry is a carry-forward `dead` key and
  toutiao is a first-wall-move `dead` key, neither a lit beneficiary.)
- **evidence:** `benchmark/2026-10-01-u10-prediction/{predictions-v4.csv,README.md}` (current = v4; see v1→v4
  history in README), `benchmark/2026-10-01-toutiao-on-unified/native-closure-prediction.md`,
  `benchmark/2026-10-01-u10-jar/{u10-classlist-diff.md,j10f-websettings-defaults.md}`.
- **expect.confirm:** per beneficiary the current first fatal is GONE and the app proceeds — toutiao:
  libflipped→libstdc++ private-closure resolves so the **first wall moves**, but the next wall is a
  libjnigraphics feature lib (now U11), so toutiao is **not** expected to light in U10 (verdict `dead`,
  first-wall-move verified from the window hilog); packlist: no `ClassNotFoundException com.android.internal.util.Predicate`;
  fd-meet/firefox/fd-fennec_fdroid: their bundled `.so` that DT_NEED the exposed symbols/libs load
  without the dlopen/NEEDED error; **fd-tutanota: NPE on null UA gone → white window (WebView web-client UI,
  no renderer on route-A; wall moved, not lit)**. All controls/canaries/FZ apps stay at their U9 state.
- **expect.refute:** any beneficiary still hits the SAME loader/Predicate error (fix didn't take), OR any
  control/canary/FZ app regresses (new loader error, a previously-lit key dark, or a frozen API error returns)
  → shared-layer change not clean; roll back, do not land U10.

## 7. after_lock / before_unlock (FILL at finalize)

`after_lock` = deploy U10 (jar 37465d6d bind + cx-bms native payload) via the chosen mechanism, then the
activation smoke (`u10.json`) incl. the identity/fingerprint assertions and the N copy probe.
`before_unlock` = roll back to **U9** (`565fc6fdc116` / `a2919b793eb6` / `boot 4db882a81732`, 318 identity
assertions), verify byte-identical RUNTIME/BOOT and 0 residual mounts. Both are `board_run.py` argv lists
(cf. approved-j10g `native_window.py`).

## finalize-checklist

1. cx-bms U10 native合包 `bbe46462b` staged — policy `621caec4` (`+= libstdc++` only), compat `015aa3a6`
   (GNU strerror_r), appspawn-x host `62debf19` (U10ShareResidentCompat / abort-owner visibility);
   **OpenSLES and libjnigraphics deferred to U11**. [DONE — SHAs pinned per outer ACK(90)]
2. combined jar+native `runtime_fp` self-computed and filled into §1, §5 (`u10.json`) and the precheck.
3. `check_frozen` (§2) prints 0 violations against the staged U10 fingerprint/package/source.
4. `after_lock`/`before_unlock` argv concretized (deploy + rollback to U9 565fc6fdc116/a2919b793eb6); `board_run.py` precheck_problem PASS.
5. `u10.json` finalized: combined runtime_fp, native probe.files, per-beneficiary native markers.
6. oc-t4 `libstdcxx` consumer scan cross-checked against the beneficiary list (the `libjnigraphics` scan now feeds U11, not U10).
7. per-board keys files written (carry-forward U9 assignment + beneficiaries + canaries + FZ controls);
   `land.py --preflight` on the plan + keys files.

## What this sets

The regression surface is defined **before** the window: every frozen behaviour (FZ-001..008) has a named
evidence app on its board, each board has 3 non-flaky canaries, and `check_frozen` mechanically refuses a
deploy that would alter a frozen artifact. A U10 regression is therefore a named, falsifiable event — a
specific control/canary/FZ app going dark or a frozen-API error returning — not a diffuse "sweep looks worse".
