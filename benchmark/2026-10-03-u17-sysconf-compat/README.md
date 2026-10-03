# U17 sysconf-compat: corpus scan + libbionic_compat gap + first-fatal accounting + source-verified translation table

#90, offline, nothing deployed. cc-t3. Follow-on to `2026-10-03-u17-native-crash-static` (fennec + im-vector both crash
on the bionic↔musl `sysconf` `_SC_*` numbering mismatch). This quantifies the blast radius across the whole app corpus,
checks whether our runtime already compensates, ranks the fix by first-fatal, and aligns the remap table to BOTH headers'
original text.

## ④ Source-verified translation table (bionic NDK23 vs OH musl — file paths + line numbers, NOT from memory)
bionic: `~/Library/Android/sdk/ndk/23.1.7779620/.../sysroot/usr/include/bits/sysconf.h`
musl:   OH sysroot `.../oh610_lts_source/prebuilts/ohos-sdk/linux/23/native/sysroot/usr/include/unistd.h`
        (identical numbering in the OH musl source tree `third_party/musl/include/unistd.h`)

| selector (meaning) | bionic # (hex) [sysconf.h line] | musl # [unistd.h line] | if app passes the BIONIC #, musl reads it as | fatal? |
|---|---|---|---|---|
| `_SC_PAGESIZE` | 39 (0x27) [L77] | 30 [L326] | **39 = `_SC_BC_STRING_MAX` → `_POSIX2_BC_STRING_MAX` = 1000** (limits.h:155) | **YES** |
| `_SC_PAGE_SIZE` | 40 (0x28) [L78] | 30 [L325] | **40 = `_SC_COLL_WEIGHTS_MAX`** (a locale limit, not page size) | **YES** |
| `_SC_NPROCESSORS_CONF` | 96 (0x60) [L126] | 83 [L365] | 96 = beyond the common musl table / unrelated | perf-only |
| `_SC_NPROCESSORS_ONLN` | 97 (0x61) [L127] | 84 [L366] | 97 = unrelated | perf-only |
| `_SC_PHYS_PAGES` | 98 (0x62) [L128] | 85 [L367] | 98 = unrelated | mem-sizing |
| `_SC_CLK_TCK` | 6 (0x06) [L43] | 2 [L297] | 6 ≈ `_SC_2_C_*` region | timing |
| `_SC_ARG_MAX` | 0 (0x00) [L37] | 0 [L295] | 0 = `_SC_ARG_MAX` (COINCIDES — safe) | no |
musl `sysconf.c` (OH `out/.../musl_src_ported/src/conf/sysconf.c`): `[_SC_PAGE_SIZE=30]=JT_PAGE_SIZE→PAGE_SIZE` (real,
L64/199-200); `[_SC_BC_STRING_MAX=39]=_POSIX2_BC_STRING_MAX=1000` (L73); `[_SC_COLL_WEIGHTS_MAX=40]=COLL_WEIGHTS_MAX` (L74).
The numberings coincide only in a low prefix and diverge by `_SC_CLK_TCK` (6 vs 2) onward — a full remap table is needed;
the FATAL entries are the two page-size selectors (39, 40).

## Remap the shim must apply (bionic # → musl #)
39→30, 40→30, 6→2, 96→83, 97→84, 98→85, … (map the whole diverging range; both tables are fixed and in-repo under
evidence/). The fatal two (39,40→30) are mandatory; CPU/mem/clk are correctness-not-crash.

## ① Corpus scan (scan.py — machine-readable evidence/sysconf-scan.{json,csv})
**Upper bound** (every arm64 app-native .so importing `sysconf`, `nm -Du`; evidence/sysconf-importers.txt):
**73 distinct keys, 552 libs.** This is the UPPER bound of keys the mismatch *could* touch — most import `sysconf` for
benign queries; only page-size callers (39/40) are fatal.

**Constant detail** (disasm the w0 immediate at each `sysconf` call; libs >12 MB recorded upper-bound-only — see the
`unscanned` rows; the two confirmed crash libs are ≤12 MB and fully scanned). See evidence/sysconf-scan.csv. The
page-size (fatal) callers and the significant (page/cpu/mem) callers are summarised in `summary.keys_with_page_size_const`.
Scan result counts:
- **73 keys** import `sysconf` (broadest upper bound).
- **63 keys** call page-size `sysconf(0x27/0x28)` among the scanned (≤12 MB) libs — the upper bound of *page-size-sensitive*
  keys. **CAVEAT: this is NOT a crash count.** Most native libs query the page size for benign mmap-alignment and tolerate
  a wrong value (the kernel still maps at the real 4 KiB); only code that (a) asserts the value is a power of two
  (mozjemalloc/scudo-style allocators) or (b) sizes an mmap/translation table directly from it (Realm) actually crashes.
- **67 keys** call a significant selector (page/cpu/mem).
- **48 libs** are recorded upper-bound-only (`unscanned`, >12 MB — libxul ×2, libroblox, il2cpp engines, **anki
  librsdroid 22 MB (Realm)**, …); their page-size use is unknown, so the true page-size upper bound is ≥63 (≤73).

**Fatal-confirmed** (crash actually observed, 2026-10-03-u17-native-crash-static, disasm on the crashing build-ids):
- fd-fennec_fdroid / libmozglue.so: `sysconf(0x27=39)` ×5 (mozjemalloc) → MOZ_CRASH (power-of-two assert).
- fd-im-vector-app / librealm-jni.so: `sysconf(0x27=39)`+`sysconf(0x28=40)` (Realm SlabAlloc) → NULL translation table.
- mcdonalds / librealmc.so: same Realm family (C2b). anki / librsdroid.so (Realm): page-size use UNSCANNED (22 MB) —
  likely but unconfirmed.
The 63 is the page-size upper bound; the fatal subset is the allocator/Realm families above. Rank the fix by the fatal
subset, not the 63.

## ② Does the runtime already compensate? NO — and where app `sysconf` binds
Current deployed `libbionic_compat.so` (73 dynsyms; e.g. b80 payload `d977bd15`) exports only bionic-specific APIs
musl lacks — `android_fdsan_*`, `android_log_*`, `android_logger_*`, `android_get_abort_message`,
`add_sysprop_change_callback`, `android_mallopt_*`. It exports **NO `sysconf` and NO `getpagesize`**. Therefore app-native
`sysconf` (UND import) resolves to **musl libc** (ld-musl, the single libc shared by all namespaces) — i.e. the broken
numbering, unmitigated. Confirmed by `readelf --dyn-syms`.
**Namespace attribution (open_site_scan, evidence/open-site-ns.txt + .json)** — the sealed child / app-native namespace is
built by `appspawn-x StockCreateConfiguredNamespaces` with two `dlns_inherit` calls whose `shared` lists ARE the child's
inherited symbol scope:
- inherit from `default`: `shared = libc.so:libdl.so:libm.so:libEGL.so:libGLESv3.so:libsurface.z.so:liboh_android_runtime.so:`**`libbionic_compat.so`**`:liblog.so:libc++.so:libstdc++.so:libOpenSLES.so`
- inherit from `westlake.sealed.child`: `shared = liboh_android_runtime.so:`**`libbionic_compat.so`**`:liblog.so:libc++.so`

So **libbionic_compat IS inherited into the app-native scope** (a viable host for the wrapper) — **but `libc.so` precedes
it in the shared list**. app-native `sysconf` (UND) therefore resolves to musl libc first; a `sysconf` merely ADDED to
libbionic_compat would NOT win.
**Interposition requirement for the fix**: libbionic_compat must be made to override libc for `sysconf` — reorder the
`dlns_inherit` shared list to put libbionic_compat ahead of `libc.so`, OR load it RTLD_GLOBAL before libc, OR interpose at
another point. Note: `getpagesize()` in OH musl returns the REAL page size (`JT_PAGE_SIZE→PAGE_SIZE`), so apps using
`getpagesize()` are NOT affected — only DIRECT `sysconf(39/40)` callers (mozjemalloc, Realm) crash; the wrapper is scoped
to those.

## ③ First-fatal accounting (vs 2026-10-03-u13-first-fatal-clusters; U13/U14 window 1–4)
The `sysconf` page-size crash is a **second-order** wall: for every confirmed victim it sits BEHIND an earlier
native-link wall, so standalone it moves **0** current first-fatals.
| key | lib | current first-fatal (cluster) | wall owner | sysconf is next? |
|---|---|---|---|---|
| fd-fennec_fdroid | libmozglue | `__gnu_strerror_r` (C2a) | native_abi 7605812c (U14, owned) | yes |
| firefox | libmozglue | C2a | native_abi 7605812c (U14, owned) | yes |
| fd-im-vector-app | librealm-jni | `_ctype_` (C2b, bind_failed) | UNOWNED | yes |
| mcdonalds | librealmc | `_ctype_` (C2b) | UNOWNED | yes |
| anki | librsdroid (Realm, 22MB) | unscanned by scan.py (>12MB); Realm family | – | likely (Realm), unconfirmed |
- **Moves now (needs native_abi 7605812c on board):** fd-fennec_fdroid, firefox → 2 keys.
- **Moves after the Realm `_ctype_` native-domain wall is also fixed:** fd-im-vector-app, mcdonalds (+anki if Realm page
  path) → 2–3 keys.
- **Must ship PAIRED** with: native_abi 7605812c (mozglue family) and a `_ctype_` provider for the Realm native domain
  (C2b, currently unowned). Per the priority rule, do NOT open the sysconf fix as a solo wall (immediate first-fatal
  move = 0).

## Fix (restated, with the interposition caveat)
A `sysconf()` (and `getpagesize()`) wrapper in `libbionic_compat.so` translating bionic `_SC_*` → musl before delegating,
scoped to app-native callers, PROVIDED libbionic_compat interposes ahead of musl libc in the app-native namespace (② —
confirm via open_site_scan). Not a stub, not don't-fix.

## Files
- scan.py — the corpus scanner (corpus dir is an arg; no hardcoded user path).
- evidence/sysconf-importers.txt — upper bound (73 keys / 552 libs).
- evidence/sysconf-scan.{json,csv} — per-call-site constants (≤12 MB libs; giants upper-bound-only).
- evidence/open-site-ns.txt — namespace attribution (open_site_scan).
- evidence/bionic-sysconf.txt, evidence/musl-sysconf.txt — the two headers' `_SC_*` lines (source of ④).
