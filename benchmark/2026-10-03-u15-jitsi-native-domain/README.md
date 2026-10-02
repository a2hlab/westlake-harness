# org.jitsi.meet into the native domain: both lists the domain hangs on are changed consistently — ANL eebd62f2 → `b96a8991` (+1 package), U15 host 08175d18 (cc-wiki) → `9e3ad72e` (+ native_cluster_path, + needs_runtime); ABI/open sites unchanged; fd-meet replays 0 LIBC missing

#90, native, offline. No board touched.
- **ANL:** built on hw248 with frozen clang feef13a3 in the 58-char mirror.
- **Host:** built on the Mac with cc-wiki's own builder and recipe, stacked on their U15 host, not a second line.
- **Why:** `2026-10-03-u15-compat-v3`. fd-meet's normal domain cannot see libbionic_compat. The native domain's
  RTLD_GLOBAL native_abi v2 (f8619ad5) carries all 14 missing LIBC symbols.

## 1. The lists the domain depends on (static)

| list | where | what it decides | change |
|---|---|---|---|
| ANL `native_cluster_path()` | `libapp_native_loader` (deployed eebd62f2; source `bms-deploy benchmark/2026-09-30-n3-native/flutter/app_native_loader.c:62-66`) | `domain->native_selected` → the app search path starts with `/system/android/lib64/westlake_native:` | **+ `"org.jitsi.meet"`** |
| host `native_cluster_path()` | U15 appspawn-x host (cc-wiki 08175d18, `candidate-stock-host.c:123-128`) | together with that search prefix, `native_private`: the owner inherit edges, **RTLD_GLOBAL native_abi**, and no compat inherit | **+ `"org.jitsi.meet"`** |
| host `needs_runtime` | same file `:285-290` | publish the resident `liboh_android_runtime.so` RTLD_GLOBAL by absolute path into the app namespace (one runtime instance) | **+ `"/org.jitsi.meet/"`** |

**Why both `native_cluster_path` lists.** The host requires **both** conditions: the ANL's westlake_native prefix and
its own list. Either one alone leaves `native_private` false, so there is no native_abi, and fd-meet keeps the
`__register_atfork` wall.

**Why `needs_runtime` too.** Its members are exactly the native-cluster apps whose startup libraries NEED
`libandroid.so` (in the native domain that is `westlake_native/libandroid.so`, which NEEDs the runtime). Counts of
arm64 libraries that NEED libandroid:

| group | apps (libraries that NEED libandroid) |
|---|---|
| in `needs_runtime` | burgerking 26, Element 9, mcdonalds 7 |
| not in it | anki, Unciv, SPD, vlc, mindustry: 0 each |

fd-meet's SoLoader startup set (fbjni, reactnative, rnscreens, rnworklets, hermestooling) NEEDs libandroid, the same
shape as its React-Native siblings bk and mcdonalds. **Without the publish, those NEEDs could map a second runtime
copy.**

## 2. ANL: faithful eebd62f2, then +1 package (`build_anl_hw248.sh`, `src/anl/`)

**Faithful reproduction.** The recipe's two ANL lines verbatim give `3ded3fe0…` ×2. Against eebd62f2
(`evidence/anl-faithful-3ded3fe0-vs-eebd62f2.txt`):
- allocated sections identical;
- remaining bytes only in `.debug_*` / `.symtab`;
- string multisets equal;
- `dwarfdump` with strings resolved: 8228 lines, **0 different**.

**The change.** `src/anl/app_native_loader.c` = the n3 source + `"org.jitsi.meet"` at the end of the array
(`src/anl/app_native_loader-vs-n3.diff`). `flutter_domain.inc` is copied verbatim beside it, because the quoted include
resolves relative to the source file.

**Build.** **`b96a8991ef5a2a6e800029aed968b2442f50786466ac2a1a19979959b56d8bbc`** ×2, rc 0, no compiler output.

## 3. Host: cc-wiki's U15 host + the jitsi lines (`recipe/build_u15j_host.py`)

**Reusing cc-wiki's builder.**
- `build_u15j_host.py` imports cc-wiki's `build_u15_host.py` from master: recipe receipt, compiler-sha gate,
  reused-object allowlist, `build_one()`, and both of their patches (Wall-1 public libs, mindustry audio verify).
- Only the output directory and `inputs/` point here.
- `inputs/` holds cc-wiki's 5 inputs, copied verbatim. The candidate source equals master's (`8be12abc`). master lacks
  the two headers it includes, `zlib-route.h` and `resident-compat.h`. That was an environment failure, fixed by
  copying them.

**Two builds, each run twice.**
- base (their u15 source, rebuilt here) = `1e96bdb2…` ×2;
- jitsi = **`9e3ad72e1ff5de52435ce2ca91eacf5346f18aaadcdb96824b6713f3f849de09`** ×2.
- The base equals 08175d18 under A′ (different directory). The only differences are the `__FILE__` path string and
  `.bss` attribution. cc-wiki's own A′ note says the same.
- The source change from base to jitsi is two lines (`src/host-u15-vs-jitsi.diff`).

## 4. Gates (`gates.py` → `evidence/gates.txt`)

| pair | dynsym | NEEDED/SONAME | open sites (`open_site_scan`, address-free) | dlopen / dlopen_ns / dlsym calls | strings added (non-path) | functions changed (`equiv.py`) |
|---|---|---|---|---|---|---|
| ANL eebd62f2 → b96a8991 | 46 = 46 | equal | 0 = 0 | 0/0/1 = 0/0/1 | **`org.jitsi.meet`** | `native_cluster_path` and its copy inlined in `ANL_Dlopen`: loop bound `cmp #0xc` → `#0xd` (13 → 14 packages) |
| host base 1e96bdb2 → jitsi 9e3ad72e | 216 = 216 | equal | 8 = 8, identical | 1/7/15 = 1/7/15 | **`org.jitsi.meet`**, **`/org.jitsi.meet/`** | `native_cluster_path` bound +1; `StockCreateConfiguredNamespaces` 581 → 586 insns (the extra `strstr`); `main` only the `__FILE__` name; `ProcessSignal` only `.bss` attribution |
| host 08175d18 → jitsi | 216 = 216 | equal | 8 = 8, identical | equal | same two | as above + the A′ path |

**Strings removed: none, apart from build-path strings.**

## 5. Replay in the native domain (`evidence/replay-fd-meet-native.txt`)

**Setup.** `../2026-10-03-u15-compat-v3/replay_normal.py --native-domain` with these globals:
- native_abi v2 f8619ad5 (host RTLD_GLOBAL);
- the resident runtime (U15 94c31177, published RTLD_GLOBAL by `needs_runtime`).

**Result.**
- **12 of 13 libraries: 0 missing.**
- libjsctooling lacks the JavaScriptCore API (`JS*`). It NEEDs `libjsc.so`, which the APK does not ship, so a Hermes
  build never loads it.
- The control in the same file (normal domain) reproduces the boards' U12 lines: `__register_atfork` and
  `android_set_abort_message`.

## 6. Prediction (first fatal)

| key | prediction |
|---|---|
| **fd-meet** | **moves past `__register_atfork` (high)**: every LIBC import resolves in the native domain. Next wall unknown (RN/Hermes init, Jitsi's WebRTC). Lit low. |
| the 13 existing native members | 0. Their list entries, branches and the order of checks are unchanged; only the loop bound grows by one |
| normal / Flutter keys | 0. The string matches only `/org.jitsi.meet` path components |

**Watch on the board.**
- fd-meet's hilog shows `[N2-OWNER] org.jitsi.meet… ABI global ready` and `[N3-OWNER] resident runtime published`.
- One `liboh_android_runtime.so` in its maps.
- No `relocating failed`.

## Release (for cx-bms / U15)

`$WORKSPACES/westlake-inputs/generations/u15-jitsi-native-domain-v1/` holds:
- `payload/android/lib64/libapp_native_loader.so` = **b96a8991** (replaces eebd62f2, in both the lib64 and route
  aliases);
- `payload/host/appspawn-x` = **9e3ad72e**: the U15 host slot, replacing cc-wiki's 08175d18;
- `builds/` (ANL a/b + faithful repro; host base/jitsi ×2), `logs/` (hw248 ANL logs, host compile/link logs), both host
  sources;
- `SHA256SUMS` (23).

**Both files have to ship together**: either alone does not change fd-meet's domain.

**Alignment with cc-wiki.** The host is 08175d18 + two lines. If cc-wiki issues another U15 host, these two lines go
onto it.

## Files

- `build_anl_hw248.sh`, `src/anl/` (source, include, diff).
- `recipe/build_u15j_host.py`, `inputs/`, `src/host-u15-vs-jitsi.diff`.
- `gates.py`.
- `evidence/`: `anl-faithful-*`, `anl-*.log`, `gates.txt`, `replay-fd-meet-native.txt`.
- `results.json`.
