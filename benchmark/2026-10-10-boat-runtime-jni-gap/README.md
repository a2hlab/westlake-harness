# Boat shared-runtime JNI gap: exact ELF and source witnesses

## Evidence and correction

The Boat renderer's successful five-touch/LAP test did not establish shared JNI compatibility. **Boat overlaid the runtime path with its patched libandroid blob**, not a new full U13 runtime. `adc125f4` is a 49-byte derivative of the old `libandroid.so` 9ccf64f8, **not** a drop-in replacement for U13 runtime `18763dd4`. The SQLite failure is missing registration, not SQLite CANTOPEN or an SELinux diagnosis. Earlier reports saying the U13 runtime cannot be reproduced are superseded by t2c's two clean, byte-identical 71-object builds.

| Exact artifact | Bytes | Defined dynamic exports | Detected native-table rows |
|---|---:|---:|---:|
| Boat `adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130` | 744856 | 268 | 1095 |
| U13 `18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae` | 3194328 | 787 | 1443 |

Inputs are independently SHA-checked before parsing (`results.json`). `exports.json`: 267 common names, 520 U13-only names, one Boat-only name (`JNIEnv::CallObjectMethod`, a C++ header helper, not a new Android feature). Complete exports, tables, registrar addresses and TU names accompany this report. This audit used local files only; no board, VM, SSH, build or candidate change.

## Origin and wrong-path verdict

`libandroid-origin.json` independently checks three objects: deployed U13 libandroid `9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db`, the Boat assembled file named `libandroid.so`, and the Boat-layer file named `liboh_android_runtime.so`. The latter two are **byte-identical adc125f4**. Against 9ccf64f8: same 744856-byte size, exactly **49 changed bytes**, **268/268 exports identical**, all scanned JNI tables identical, all decoded registration dispatch rows identical, and the same four weak SQLite no-op targets. No new SQLite regression was introduced by those 49 edits: it is the pre-existing libandroid runtime surface being substituted for the much larger U13 runtime.

The label `CLASSNAME_FIX` does **not** describe all 49 changes: **two non-executable bytes** change `AppSchedulerBridgX` to `AppSchedulerBridge` (slash/dot forms, offsets `0x2ab5a` and `0x2ca52`); **47 executable bytes** lie in `nwfs_seed_window_geometry`, `BBQ_nativeUpdate`, `ANativeWindow_setBuffersGeometry`, and `ANativeWindow_fromSurface`. Complete byte/owner records and old/new instruction excerpts are in `libandroid-origin.json` and `evidence/{libandroid-base,boat}-patch-sites.txt`. Therefore do not infer that the binary difference is a harmless class-name-only edit or that it cannot affect rendering.

**Wrong-path conclusion: YES, for the shared runtime contract.** The old libandroid-derived blob lacks the real SQLite registrars. Historical `boat-side-facts.txt:8–9` explicitly assigned the same adc blob to both names; the current Boat overlay `westlake-u13-boat-overlay.sh:12,34` binds it over `/system/android/lib64/liboh_android_runtime.so` and expects to replace 18763dd4. `evidence/source-9.txt` and `source-10.txt` preserve those path/SHA statements. This closes the identity chain independently of a missing Boat compile run.

Naming alone does not make the old blob a pure NDK shim: **9ccf64f8, adc125f4 and 18763dd4 all have SONAME `liboh_android_runtime.so`** (`evidence/*-dynamic.txt`). Separately loading adc under the libandroid alias can select the wrong existing owner or add an old runtime copy; a filename-only remedy is not a single-owner proof.

## The registration entry is startReg, not JNI_OnLoad

**Neither ELF exports `JNI_OnLoad`.** Both export `android::AndroidRuntime::startReg(JNIEnv*)`: Boat `0x3b148`, U13 `0x190f34`. `registration-dispatch.json` decodes relocated name/function pairs in `kRegJNI`, rather than guessing classes from strings. Boat's main table has 36 entries; U13 has 40. Each also has three entries in `kRegJNI_GL`. U13-only main dispatch names are AudioSystemCapabilities, AudioProductStrategy, VelocityTracker and CommonEvent.

`evidence/source-2.txt` quotes the actual t2c input `smoke-markers/src/AndroidRuntime.cpp`: `startReg` at line 347, SQLite dispatch at 245–252, loop at 411–421. That loop prints `ok` whenever a registrar returns nonnegative. Its `JNI_OnLoad` lookup at line 381 is for **libjavacore**, not an entry exported by this runtime. The static tables prove binding; they do not prove every table was executed on a particular run.

## SQLite: why Boat reports registration success but nativeOpen is absent

| Registrar | Boat target / binding / size | U13 target / binding / size |
|---|---|---|
| SQLiteConnection | `0x4040c`, WEAK, 8 | `0x1a3608`, GLOBAL, 772 |
| SQLiteGlobal | `0x40414`, WEAK, 8 | `0x1a5d9c`, GLOBAL, 340 |
| SQLiteDebug | `0x4041c`, WEAK, 8 | `0x1a59b8`, GLOBAL, 800 |
| CursorWindow | `0x40424`, WEAK, 8 | `0x19ff88`, GLOBAL, 716 |

All four Boat bodies are exactly `e0031f2ac0035fd6`: **`mov w0, wzr; ret`**. All four remain pointed to by its main registration table at `0x81960/70/80/90`. Thus this is **not** an omitted dispatch entry: it dispatches to an empty success-returning implementation. See `evidence/boat-{1,2,3,4}.txt`, versus the real U13 bodies in `evidence/u13-{1,2,3,4}.txt`.

The actual U13 registration TU is:

`$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b87-native/adapter/framework/android-runtime/src/android_database_SQLiteConnection.cpp:960`.

Its `sMethods` begins at 903, contains **27 methods**, and line 972 calls `RegisterMethodsOrDie(env, "android/database/sqlite/SQLiteConnection", sMethods, NELEM(sMethods))`. `nativeOpen(Ljava/lang/String;ILjava/lang/String;ZZII)J` is its first entry and is absent from Boat tables. This file and the three sibling SQLite/CursorWindow registration sources were freshly checked against t2c's exact source inventory; hashes and excerpts are in `evidence-index.json` and `evidence/source-{3,4,5,6}.txt`.

Boat-source corroboration is explicit: `$WORKSPACES/../00.Workspace-games-ad1ab0a7/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp:56–69` says the Unity/render build intentionally does not compile SQLite and defines these four weak return-zero fallbacks. Its stage2-Unity compile recipe's `SRCS_AOSP` at 366 likewise omits the SQLite group. **This local source is corroboration, not a byte-reproduced source claim for adc125f4.** The ELF independently establishes the missing TU/table and selected empty bodies.

## Missing methods and translation units

`missing-methods.csv` / `.json` list **349 U13 rows absent from the corresponding Boat TU/table scope**, including class, method descriptor, owner TU/table and function/table addresses. **269 distinct name/descriptor pairs** are absent anywhere in Boat scanned tables. Do not turn either number into an app-blocking count. In particular, three generic CursorWindow signatures appear in unrelated Boat tables and do not replace CursorWindow registration.

| Class/table scope | Missing rows |
|---|---:|
| SQLiteConnection / CursorWindow / SQLiteDebug / SQLiteGlobal | 27 / 21 / 1 / 1 |
| GLImpl / EGLImpl | 250 / 28 |
| VelocityTracker | 7 |
| ActivityManagerAdapter CommonEvent additions | 5 |
| AudioSystem additions | 4 |
| BLASTBufferQueue sync additions | 4 |
| EmbossMaskFilter | 1 |

These are scoped table deltas, not a complete list of every possible runtime-provided JNI API. Stack-built/unnamed tables and other libraries require separate attribution; previously reported Camera/AudioProductStrategy unscoped differences are not silently merged into the 349 count. Source/class mappings for the non-SQLite groups follow the existing exact-artifact `boat-full128/jni-diff/source-registration-excerpts.txt`; the four SQLite groups also have fresh exact-input witnesses here.

`translation-units.json`: Boat has **48 STT_FILE names**, U13 **85**; **37 names are U13-only**, none Boat-only. Of those 37, **26 have source witnesses in the t2c inventory**, 11 are compiler-runtime file names, not missing Android registrars. STT_FILE is compiler/linker evidence, not a complete object receipt. `u13-source-witnesses.json` includes archived source SHA for the compiled source set. The 26 names are:

```
CursorWindow.cpp                  android_database_CursorWindow.cpp
android_database_SQLiteCommon.cpp android_database_SQLiteConnection.cpp
android_database_SQLiteDebug.cpp  android_database_SQLiteGlobal.cpp
cutils_ashmem_shim.cpp            sqlite3.c
sqlite3_android_shim.cpp          android_media_AudioSystemCapabilities.cpp
android_view_VelocityTracker.cpp  common_event_registration.cpp
asset-offsets-init.cpp            camera_info.cpp
glimpl_register.cpp               com_google_android_gles_jni_GLImpl.cpp
gl_forwarders.c                   gles1_pointer_bounds.c
oh_egl_impl.cpp                   webview_publication.cpp
SkEmbossMask.cpp                  SkEmbossMaskFilter.cpp
SkMask.cpp                        SkMathPriv.cpp
emboss-base.cpp                   emboss-registration.cpp
```

## Build provenance: do not substitute an older Boat run

- U13: t2c `runtime-reproduction.json` binds two fresh builds, 71/71 historical-equal objects, the exact 18763dd4 output and raw log SHA. Complete inputs are `$WORKSPACES/westlake-inputs/generations/t2c-runtime-reproduction-20261010/runtime187-inputs.tar.gz`, SHA `ba5906c6903dccc35dc07ecd6bbbeea9742fd4d366ab9cb64bd48fa7551c9c88`; persistent remote copy is `hw248:/home/alvin/westlake-t2c-runtime187-repro-20261010T1333/complete-v2/`. t2c recipe lines 371–378 list the SQLite support/registration TUs; line 508 compiles sqlite3.c. See `evidence/source-0.txt` and `source-1.txt` for the recipe and fresh compile log.
- Boat: the exact assembled original is `$WORKSPACES/../00.Workspace-games-ad1ab0a7/.bridge-payload/zigzag-candidates/strict-boat-assembled-20260924T074522Z-25403/files/libandroid.so`, adc125f4. Its 49-byte relation to 9ccf64f8 and its later runtime alias are verified, not inferred from a build log. `benchmark/2026-10-09-local-build-check/README.md` section 4 records the same origin. No adc runtime compile run is expected for this assembled patch. The recorded `hw248:/opt/build-runs/boatattack-runtime-source-20260813T141442Z/` listing has **804736-byte** runtime artifacts (`adapter-buildchain/evidence/hw248-boat-run.txt:2–8`), not adc125f4; it is **not** its provenance. Exact source/compiler provenance for the older 9ccf64f8 baseline remains separate and is not asserted here.

## Minimal repair choices

**Immediate JNI repair: keep `/system/android/lib64/liboh_android_runtime.so` at 18763dd4; remove the adc runtime substitution from Boat's stage/overlay inventory.** Treat adc as a libandroid patch only, not a shared runtime provider. If the outer elects to test it at `/system/android/lib64/libandroid.so`, replace only that alias, preserving all other Boat pieces and the real runtime path, and inspect namespace ownership/maps before declaring it safe. Because the alias has the runtime SONAME, this is a proposed isolated routing experiment, **not** an already-proven unique-owner/rendering fix. It needs outer approval and reboot full128 regression; no such edit was made here.

**Production single-owner repair: preserve the reproducible U13 18763dd4 build closure and port only the required render/class-name delta into the appropriate real owner or a thin libandroid shim that depends on it.** Start from the t2c frozen source/recipe and retain all 71 objects (including publication, SQLite, GL/EGL and Emboss). Use the four changed function owners/47 code bytes above to locate the necessary source delta; the older `boat-pr03-render-port/SOURCE-PATCH-LIST.md` is a locator only, not proof of an adc compile run. Do not wholesale replace AndroidRuntime.cpp, Process, DisplayEventReceiver or remove VelocityTracker. Actual rendering behavior still needs isolated validation; this audit has not implemented a candidate.

**Alternative, narrower SQLite repair on Boat:** link the real nine-TU closure from the exact U13 inputs: four `android_database_{SQLiteConnection,SQLiteGlobal,SQLiteDebug,CursorWindow}.cpp`, `android_database_SQLiteCommon.cpp`, `androidfw/CursorWindow.cpp`, `cutils_ashmem_shim.cpp`, `sqlite3_android_shim.cpp`, and `sqlite/sqlite3.c`, with the frozen recipe's SQLite defines/includes. Real GLOBAL registrars override the existing WEAK fallbacks; no second runtime owner or extra JNI_OnLoad entry is needed. Merely inserting another gRegJNI line or exporting `nativeOpen` does **not** fix registration. This repairs the **50 scoped SQLite-family entries only**, leaving the other **299** scoped gaps to reconcile; not enough to approve a shared-runtime replacement.

Required next gates: four GLOBAL non-empty registrars; complete SQLite family tables; no unintended export/JNI/TU drops relative to U13; sole runtime/AssetManager owner; fresh native/static gates; Boat playable and rebooted full128 non-regression before frozen registration/deployment. Predicted movement is from missing-JNI ULE to a real SQLite open attempt; CANTOPEN, filesystem/SELinux and downstream content are **not** claimed fixed.

## Reproduce and validation

```
python3 benchmark/2026-10-10-boat-runtime-jni-gap/audit.py
python3 benchmark/2026-10-10-boat-runtime-jni-gap/collect_evidence.py
python3 -m unittest discover -s benchmark/2026-10-10-boat-runtime-jni-gap -p 'test_*.py' -v
```

Seven exact-artifact known answers pass; ten registrar/startReg disassemblies plus patch-site/dynamic evidence return 0. Two audit generations are byte-identical. REA tools are not exposed in this session; read-only doctor could not fetch its package (`EPERM`), so installed LLVM and the existing relocation-aware JNI scanner were used. No setup, board operation or artifact rebuild was performed.
