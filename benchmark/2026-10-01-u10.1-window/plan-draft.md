# U10.1 window plan — SKELETON / DRAFT

Round = **U10.1 native + U11i JAR** (`5ae3dd29…`). Prediction = `benchmark/2026-10-01-u10.1-prediction/predictions-v5.csv`.
**Status:** DRAFT — the **native合包 SHA is blank** (pending cx-bms U10.1 native) and the U10.1 host marker regex
is cx-bms-defined. Finalize per `finalize-checklist`.

Lead lane: cc-t3. Boards: `5ea34a45…` / `5cd1e3dd…` / `61b0657200…`. Discipline: 三板统一态、全量分片; one
on-board task per board; ≤45 min; release the lock when done; screenshots are ground truth (ACK quotes `facts.txt`).

## 1. Candidate artifacts

| layer | artifact | sha / id | state |
|---|---|---|---|
| JAR | `/system/android/framework/oh-adapter-runtime.jar` (U11i) | `5ae3dd29d45c2270e8a53a9dc4bbeeca8972b9b092f91898a15d605bc1cc0108` | built, deterministic (build-receipt-u11h.json) |
| JAR (unchanged) | `adapter-mainline-stubs.jar` (T7e stubs) | `f3bcc9d7c76cb73487837d7ad92fccba3d595d313ada7403bed99c4f11c2a8c2` | unchanged |
| native | U10.1 native合包 (libstdc++ policy via libnativeloader + the U10.1 host r3 shim; strerror_r/abort as in U10) | `<FILL cx-bms U10.1 native合包 SHA>` | **PENDING cx-bms** |

One generation, one window: U11i JAR + the cx-bms U10.1 native payload. **Rollback target = U9**
(`565fc6fdc116` / `a2919b793eb6` + boot `4db882a81732` + 318 identity assertions).

## 2. Gate — `check_frozen` before deploy

```
python3 scripts/lab/check_frozen.py --registry knowledge/frozen/frozen.json \
  --fingerprint $WORKSPACES/westlake-generation-u11-staging/runtime-fingerprint.txt \
  --package <cx-bms U10.1 native generation dir> --source-root $WORKSPACES/westlake-harness-walls --git master
```
0 violations required. U11i jar + the JAR fixes are new behaviour on non-frozen files; the native合包 must match
any frozen `.so`/BCP path it declares.

## 3. Three-board keys — carry forward the U10 sharding

Reuse the U10 window keys **unchanged** (full 166-key sweep, carried forward from the U9 shard assignment — same
file set, no re-spread):
`benchmark/2026-10-01-u10-window/keys-5ea.txt` (55), `keys-5cd.txt` (55), `keys-61b.txt` (56).

| board | v5 lit? beneficiaries (carry-forward) | revert-controls (U9-lit) |
|---|---|---|
| `5ea34a45…` | `fd-api` (appcompat J10d alias guard) | — |
| `5cd1e3dd…` | `fd-client` (ssl-engine WlSSLEngine) | `opencamera` (back to U9 lit) |
| `61b0657200…` | `x` (phone TelephonyFetcher), `cv2-com-nononsenseapps-notepad` (content-provider) | `fd-organicmaps` (back to U9 lit) |

`toutiao` (61b): libstdc++ cleared, first wall → OkHttp conscrypt (dead, first-wall-move read from hilog).
`fd-meet` (5ea) / `fd-fennec_fdroid` (5cd) / `firefox` (61b): stay dead (U10 observed native no-ops).

## 4. Smoke spec — `knowledge/smoke/u10.1.json`

**helloworld markers (always printed — run per bridged app at bind, so the always-launched control triggers them):**
- `WL-KS-PROBE-SELFTEST`: `\[WL-KS-PROBE\] selftest` — cluster 4 KeystoreBoardProbe.selfTest() (key-independent).
- `B8-FETCH-PHONE`: `\[B8-FETCH\] phone fetcher replaced` — cluster 1 TelephonyFetcher.install().
- `B8-PROV-INSTALL`: `\[B8-PROV-INSTALL\] installed ` — cluster 5 AppContentProviders.install() (helloworld logs `0/0`).
- `U10.1-HOST-R3`: **FILL** (cx-bms-defined native host marker, printed per bridged app like U10's `[U10-COMPAT-VISIBLE]`).

**FINALIZE:** `expect.runtime_fp` = combined jar+native fp (now `FILL_COMBINED_JAR_NATIVE_FP`); add the native
artifacts to `probe.files`; fill the `U10.1-HOST-R3` regex. Controls/boot_fp/jar+stubs probe are final.

**Specific-app markers → read offline from each app's hilog (not helloworld), see §6 expect:** `x`
`\[B8-FETCH\] phone TelephonyManager allocated` (only when an app queries phone); `notepad`
`\[B8-PROV-INSTALL\] installed [1-9]` + its authority; `fd-api` `\[J10d-THEME\] .*skipped: alias target theme
owned by AliasTargetTheme`; `fd-client` has no log (read t20).

## 5. offline_precheck (per board, `board_run.py` expect.confirm / expect.refute)

- **hypothesis:** U10.1 native (repairs the U10 regression on opencamera/organicmaps; strerror_r/abort as U10,
  observed no-ops on fd-meet/fennec) + U11i JAR (phone/ssl-engine/content-provider/appcompat-guard) match
  `predictions-v5.csv`: 112 lit + **4 lit?** (`x`, `fd-client`, `cv2-com-nononsenseapps-notepad`, `fd-api`), zero
  regression (112 lit + 3 lit→flaky = 115 baseline).
- **evidence:** `benchmark/2026-10-01-u10.1-prediction/{predictions-v5.csv,README.md}`,
  `benchmark/2026-10-01-u11-jar/build-receipt-u11h.json`, `benchmark/2026-10-01-toutiao-on-unified/okhttp-platform.md`.
- **expect.confirm:** per beneficiary — `x`: `getSystemService("phone")` non-null, telephony cast passes (t20 lit);
  `fd-client`: createSSLEngine non-null → Dagger graph builds → accountManager non-null (t20 lit); `notepad`: its
  own ContentProvider installed (`[B8-PROV-INSTALL] installed ≥1`) → query non-null (t20 lit); `fd-api`:
  `[J10d-THEME] … skipped` → AppCompatActivity starts (t20 lit). `opencamera`/`fd-organicmaps` back to lit.
  All controls/canaries/FZ/79-provider-declarers stay lit. `toutiao` dead (first wall moved to conscrypt).
- **expect.refute:** any lit?/revert-control not reaching its state, OR any lit control/canary/FZ/provider-declarer
  regresses (→ regression, roll back to U9, do not land), OR the stock-okhttp controls (`fd-droidify`/`newpipe`)
  go dark (the toutiao conscrypt finding must not touch the stock path).

## 6. Regression controls

- **FZ-evidence apps + per-board canaries:** carried from `benchmark/2026-10-01-u10-window/keys-roles.md`
  (5ea aegis/fd-feeder/ooniprobe; 5cd fd-droidify/markor/newpipe; 61b fd-k9/fd-com-amaze-filemanager/fd-libretube;
  FZ-001..008 evidence apps on their boards).
- **Provider-cluster controls (79):** `benchmark/2026-10-01-u10.1-prediction/regression-controls-provider.txt` —
  already-lit keys that declare ≥1 ContentProvider; U11i `AppContentProviders` installs app providers at bind, so
  these 79 must stay lit (no provider-onCreate crash).
- **okhttp controls:** `fd-droidify`, `newpipe` (stock okhttp 4.x, no conscrypt dependency) must stay lit.

## 7. after_lock / before_unlock (FILL at finalize)

`after_lock` = deploy U11i JAR + cx-bms U10.1 native, then the activation smoke (`u10.1.json`) incl. identity/
fingerprint + the N copy probe. `before_unlock` = roll back to **U9** (`565fc6fdc116`/`a2919b793eb6` /
`boot 4db882a81732`, 318 assertions), verify byte-identical RUNTIME/BOOT + 0 residual mounts. `board_run.py` argv.

## finalize-checklist

1. cx-bms U10.1 native合包 staged + SHA pinned; the `U10.1-HOST-R3` marker regex defined.
2. combined jar+native `runtime_fp` self-computed → `u10.1.json` `expect.runtime_fp` + the precheck.
3. native artifacts added to `u10.1.json` `probe.files` (libnativeloader.so policy + the host shim).
4. `check_frozen` 0 violations; `board_run.py` precheck_problem PASS; `land.py --preflight` on the plan.
5. `after_lock`/`before_unlock` argv concretized (deploy + rollback to U9).
6. keys files confirmed reused from the U10 window (carry-forward).
