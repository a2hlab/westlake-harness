# Window5: three native loading roots, not three generic missing libraries

## Correction and rule

`F02-A12-UNCLASSIFIED`, `F02-A12-UNSUPPORTED-SYMBOL` and a SoLoader wrapper are classifications, not root causes. In particular, **Meet is not a permissions repair**: it reaches relocation both in the installed directory and after extraction into `lib-main`. Also, absence from compat's dynsym is not absence from the deployed provider inventory.

Use the app PID, full-file line numbers, terminal exception and its cause chain. Compare the actual consumer SHA, all `DT_NEEDED` entries and every strong UND symbol. Distinguish inventory presence, namespace accessibility and the linker's saved relocation scope. This delivery is **read-only: no candidates, builds, devices or package edits**.

## Identity and scope

- Window5 sources are the canonical `candidate-first-fatal-clusters/sources.json`; all three keys use the 5ea A5-r2 unlit-original attempt. `log-index.json` pins the full hilog/record/native-assembly SHA and retains original line numbers.
- U10.1T8 bundle `190afedd3ddb…`, host `65cc3535`, ANL `eebd62f2`, compat `015aa3a6`, audio facade `5891f899`, private ABI `d2053066`. `identity.json` gives complete SHA; `evidence/artifact-identity-t8.txt` proves the relevant files match the three-board expected map.
- Five selected consumers: Realm, libarc, Meet's libc++/Hermes/React Native. Every assembly member in these three inputs was SHA checked. **1,150 strong + 2 weak UND entries** and all NEEDED rows are compared in `consumer-comparison.json`, with explicit provider indices into **153 inventory paths**. The inventory union has no uncovered strong UND entry for these five consumers **after including the separately captured real OH audio ELF**. This is not proof that these paths are visible or ABI-compatible.
- `deployed_whois` was run for each relevant name against T8. Its maps section remains explicitly **historical U9**; never interpret that section as a window5 mapping. Window5 fallback files themselves were not captured: public native members are verified, but fallback SHA/selected GOT owner remain unknown.

## Decisions and predictions

| Key | Window5 terminal root | Verdict and minimum repair layer | Conditional first-fatal moves vs T8 | New moves beyond U12 |
|---|---|---|---:|---:|
| fd-im-vector-app | `librealm-jni` NEEDED `libz.so` missing in `westlake.anl.app.26007.3` | Repair viable, **already covered by reviewed U12** private alias/provider and narrow host route | 1 | 0 |
| mindustry | `libarc` cannot resolve `slCreateEngine`; app domain also rejects real OH audio absolute path | Conditional native audio-facade/owner-route repair; raw OH replacement is rejected | 1 | 1, not implemented/admitted |
| fd-meet | public Hermes/React Native lack `__register_atfork` in scope; fallback libc++ lacks `android_set_abort_message` in scope | Conditional common namespace/unique-owner scope repair; permission-only/export-only prescriptions rejected | 1 | 1, not implemented/proved |

**Observed moves: 0. Current delivered U13 draft adds 0 moves over U12 for this trio.** Three is the conditional repair-plan bound, not three delivered fixes or three new lit apps. All exact next first-fatal results and t20 results remain unknown. U12's Element observation has not been borrowed from a later run.

## 1. Element: private SONAME closure, not SoLoader directory permission

PID **26007**, main TID26030. Full original lines are in `evidence/fd-im-vector-app-context.json`:

```text
25555: load libz.so failed, namespace=westlake.anl.app.26007.3, errno=2
25556: Error loading shared library libz.so: (needed by /data/app/el1/bundle/public/im.vector.app/android/lib/arm64-v8a/librealm-jni.so)
25559: load libz.so failed, namespace=westlake.anl.app.26007.3, errno=2
25560: Error loading shared library libz.so: (needed by /data/app/el2/100/base/im.vector.app/app_lib/librealm-jni.so.10.19.0)
25664: [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.UnsatisfiedLinkError: F02-A12-UNCLASSIFIED: dlopen_ns failed for /data/app/el2/100/base/im.vector.app/app_lib/librealm-jni.so.10.19.0: Error loading shared library libz.so: (needed by /data/app/el2/100/base/im.vector.app/app_lib/librealm-jni.so.10.19.0)
```

Public Realm SHA `7693a9d2…`: NEEDED `liblog.so, libandroid.so, libz.so, libm.so, libdl.so, libc.so`; 252 strong UND entries. **Direct strong UND zlib imports: 0**, but the retained NEEDED still has to load, as the actual failure proves. T8 WHOIS shows **no libz.so anywhere in this bundle**, although real `libshared_libz.z.so` is present. Therefore this is a missing alias in the selected namespace, not a missing zlib implementation. A globally installed provider under a different SONAME does not satisfy Realm's NEEDED.

Reuse `benchmark/2026-10-02-u12-private-zlib/inputs/zlib-route.h:20`: Element is explicitly selected at line22. The final U12 has host `2a87118e`, **private** alias `50b9ab6a` (SONAME `libz.so`, NEEDED `libshared_libz.z.so`) and provider `ab0820c6` (NEEDED `libc.so`). `results.json` lists the exact zlib imports supplied by that provider. Do not put the alias at root or copy a private libc. The provider is byte-identical to T8's existing root/route zlib implementation; raw strings diff is **0 drop/0 add**. The host comparison preserves its raw **2 drop/5 add** result (two embedded source paths change, plus route formatting/root/log literals); it is a previously reviewed U12 change, not a new candidate or a zero-delta claim.

Next: exact fatal unknown. Realm also imports `android_set_abort_message@LIBC`; its successful binding must be observed rather than inferred from the symbol inventory. The old libz terminal should move conditionally by **1 versus T8, 0 additional versus U12**.

## 2. Mindustry: missing audio exports plus inaccessible OH owner

PID **6536**, main TID6560, public libarc SHA `03275660…`; NEEDED `libm.so, liblog.so, libOpenSLES.so, libc.so, libdl.so`; 78 strong UND entries.

```text
19400: load absolute_path /system/lib64/libOpenSLES.so: check ns accessible failed namespace=westlake.anl.app.6536.3.
19403: relocating failed: symbol not found. dso=/data/app/el1/bundle/public/io.anuke.mindustry/android/lib/arm64-v8a/libarc.so s=slCreateEngine use_vna_hash=0 van_hash=0
19404: [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.ExceptionInInitializerError
19427: Caused by: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el1/bundle/public/io.anuke.mindustry/android/lib/arm64-v8a/libarc.so: Error relocating /data/app/el1/bundle/public/io.anuke.mindustry/android/lib/arm64-v8a/libarc.so: slCreateEngine: symbol not found
```

The **four-export** Android facade `5891f899` does not export `slCreateEngine`, `SL_IID_ENGINE`, `SL_IID_VOLUME` or `SL_IID_PLAY`. It does export the Android extension IID `SL_IID_ANDROIDSIMPLEBUFFERQUEUE`. The captured **140-export** real OH owner `05d8ac90` supplies the other four, but line19400 proves the consumer app namespace cannot directly access its canonical path. Inventory presence is not the app's resolved provider. Adding a compat symbol or merely a manifest row cannot implement this API.

Minimum load-wall repair requires both **narrow access to the unique OH owner and a complete Android-facing ABI adapter** for the five libarc imports. Android/OH scalars are 32/64-bit and IIDs 16/24 bytes: replacing the Android facade with the OH file is unsafe. Existing `u11-native-batch` and `u12-upstream-audio` evidence is design/reference only; audio candidate0e9b is not admitted or in U12/U13.

The known next capability boundary is unchanged: libarc calls PLAY RegisterCallback/set-mask at `a2290/a22a4`, OH05d8 returns **12 FEATURE_UNSUPPORTED**. That is not a measured next fatal or proof of dead UI. The conditional load-wall move is **1**, but the current delivered package predicts **0** for Mindustry. No PLAY completion implementation is started here.

## 3. Meet: two-stage scope failure, not an unpacking-denial wall

PID **28539**, main TID28563, background create-react-context TID28583. Public verified SHAs: libc++ `3e852764`, Hermes `ebf7bc5c`, React Native `f5e13c08`.

```text
25374: relocating failed: symbol not found. dso=/data/app/el1/bundle/public/org.jitsi.meet/android/lib/arm64-v8a/libhermes.so s=__register_atfork use_vna_hash=1 van_hash=50d63
25376: relocating failed: symbol not found. dso=/data/app/el1/bundle/public/org.jitsi.meet/android/lib/arm64-v8a/libreactnative.so s=__register_atfork use_vna_hash=1 van_hash=50d63
25477: Reunpacking BackupSoSources ... libreactnative.so: __register_atfork: symbol not found ...
25483: extracting DSO libc++_shared.so
25507: relocating failed: symbol not found. dso=/data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so s=android_set_abort_message use_vna_hash=1 van_hash=50d63
25527: [CHILD_CK] J_invokeStaticMain_main_threw: com.facebook.soloader.B: java.lang.UnsatisfiedLinkError: F02-A12-UNSUPPORTED-SYMBOL: dlopen_ns failed for /data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so: Error relocating /data/app/el2/100/base/org.jitsi.meet/lib-main/libc++_shared.so: android_set_abort_message: symbol not found
```

SoLoader logs a warning about removing write permission, but then extracts and reaches the native linker. **Permission-only repair moves 0**: both public and fallback paths fail at symbol relocation, not an EACCES open. The later background `[B8-UEH] process kept alive` log cannot erase the main terminal.

| Required symbol | Actual deployed providers | Why not a global missing-export diagnosis |
|---|---|---|
| `android_set_abort_message@LIBC` | compat015aa, unversioned GLOBAL; ABI/libc/log/pthread-bridge have LIBC providers | Same-PID `owner_verified` queries precede failure; handle visibility is not consumer relocation scope |
| `__register_atfork@LIBC` | pthread bridge and private ABI d205 export `__register_atfork@@LIBC` | Compat015aa omits it, factory fd3c omits it, but the deployed provider inventory does not |

`selected-provider-facts.json` and the original `-V`/dynsym output show versions. `van_hash=0x50d63` is LIBC. Do not declare version mismatch: matching LIBC atfork providers exist, and the previously audited fd3c behavior accepts unversioned providers with absent version tables. Reference source is not claimed to reproduce fd3c.

Static route: receipt-selected ANL eebd's `native_cluster_path:63-67` **does not include org.jitsi.meet**. Its `ANL_Dlopen:450-473` passes the ordinary app namespace, unlike Element/Mindustry's selected private branch. The log prints B8 runtime-CL namespace creation, **not the numerical namespace of these SoLoader calls**; do not invent `app.28539.N` or equate it to that B8 namespace. ANL's opens and namespace construction are callback-indirect, so `open_site_scan` has zero direct sites/edges for ANL; source plus disassembly supplies this limitation, not proof of no operations.

Host r3 scanner retains **8 opens, 17 namespace edges, 0 INHERIT-REPEAT, 4 old INHERIT-AFTER-OPEN may-path findings**. The ordinary app already has a compat edge at `cffc`; adding its name again is not the missing remedy. Coordinate the N11h/Gecko common constructor and arrange the **existing unique compat and atfork owner in the consumer's actual saved relocation scope before app relocation**, then verify selected addresses on both public and fallback paths. Preserve once-only inheritance. Do not blindly whitelist Meet into the private old-runtime route: React Native imports six AAsset operations and can expose the known duplicated AssetManager/runtime owner problem.

Conditional complete scope repair moves **1 key**, not one per failed symbol/retry/thread. Abort-only visibility leaves the preceding atfork recovery root; exact next fatal after both owners are accessible is unknown. No export/route candidate is produced here.

The scope diagnosis is the leading explanation from the route and matching-version inventory, **not a captured selected-owner/GOT oracle**. `results.json` marks that evidence boundary explicitly. The old r3 `owner_verified` log is not promoted to a successful consumer relocation proof.

## Reproduction and audit

```sh
export PATH=/opt/homebrew/opt/llvm/bin:$PATH
python3 benchmark/2026-10-02-u13-native-load-3/collect.py
python3 benchmark/2026-10-02-u13-native-load-3/report.py
python3 benchmark/2026-10-02-u13-native-load-3/test_analysis.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test u13_native_load_3
```

Collection reads persistent Mac evidence only. Tests read committed JSON/output and do not require `.artifacts`, sibling worktrees, devices or VM connectivity. `raw-evidence.json` gives every private original output path/SHA and the published normalized/excerpt path/SHA. The full public log snippets preserve native library/device paths and original file line numbers; personal host prefixes are replaced at directory boundaries.

`landing-paths.txt` contains only this report/collector/evidence, two contracts and one Rust test wrapper. `documentation.json` supplies the root Layout and DIGEST additions for outer land. No active native package, registry or bms/src source is changed.
