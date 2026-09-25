# #41 — Bionic in the real app domain, and what metasec actually does

**Board entry:** `#41` in `.octos/OUTER_LOOP_REVIEW.md`
**Date:** 2026-09-25 · **Board:** 5cd1e3dd
**Mode:** read-only analysis + minimal on-board test. Only `/data/local/tmp` and one scratch subdir of an existing app runtime root were written; no `/system`, no remount, no app launched.

Two questions gate the Bionic route ([#37](../2026-09-25-bionic-libc-feasibility/), [#39](../2026-09-25-bionic-pt-interp-poc/)):

1. **T1** — in the *real* app process context (appspawn-x child, app uid, app SELinux domain), can it exec a PT_INTERP=Bionic program and mmap-execute Bionic files?
2. **metasec cost** — under the current best Toutiao config (#38), how is `libmetasec_ml` handled: loaded / failed / skipped, does it crash, and what is the effect on visible features — compared to the Android reference?

**Answers.** ① **Yes** — the app domain loads Bionic linker64/libc exactly as it already loads libart, 0 denials, no policy change. ② metasec **loads but does not initialize** on OH (its `MSTaskManager::DoLazyInit` never runs, whereas it runs on Android); it does not crash and is not today's visible-feature blocker.

---

## ① The app runs code by fork+setcon, never execve — so the right question is *mmap*, not *exec*

The app child's identity is authoritative from the appspawn-x child stderr (#38 runs):

```
[AppSpawnX] Applying DAC: uid=20010053 gid=20010053
[AppSpawnX] applySELinux: apl=normal pkg=org.westlake.imehost hapFlags=0 uid=20010053
[AppSpawnX] applySELinux: child secon transitioned successfully (apl=normal)   => u:r:normal_hap:s0
```

So the app domain is **`u:r:normal_hap:s0`**, uid **20010053**. Crucially, appspawn-x **forks and `setcon`s** the child into normal_hap and the child then **dlopen/mmap**s its native code — it never `execve`s a binary. That distinction decides the whole question:

- **`execve` of a binary** needs `entrypoint` on the file's type — normal_hap does not have it for app files, and the app never needs it. My `execve` test under normal_hap correctly fails (`EXIT 126`), and that is *expected and irrelevant*.
- **`mmap(PROT_EXEC)` of a .so** needs `file:execute` — this is the real `.so` load permission, and it is what normal_hap uses in production to load libart + the 57 framework libs + the APK's own native libs.

### Label + namespace: the app never touches `data_local_tmp`

`source_app_namespace` sets up a private mount namespace and **bind-mounts the appdat runtime root → `/data/local/tmp/asx`** and the app's private-tmp → `/data/local/tmp`. SELinux labels follow the inode, not the mount point, so inside the child `/data/local/tmp` is **`appdat`**, not `data_local_tmp`.

| path | label |
|---|---|
| global `/data/local/tmp/*` (what #39's su test used) | `u:object_r:data_local_tmp:s0` |
| app runtime root `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-*` | `u:object_r:appdat:s0` |

This retires the #39 red herring: the su-domain `data_local_tmp` denials the outer loop corrected me on have **nothing to do with the app path** — the app loads from `appdat` inside its private namespace.

### The controlled experiment (`scripts/verify_t1.sh`, `scripts/dommap.c`)

`dommap` is an OH-native (musl) helper that `setcon`s to a target domain (the same dyntransition appspawn does to the forked child), then tests `open` + `mmap(PROT_READ|PROT_EXEC)` on a file and `mprotect` of anon memory to PROT_EXEC. Results are encoded in the exit code because stdout writes fail once the process leaves su: `1`=mmap-exec file, `2`=execmem, `4`=open, `8`=setcon, `16`=in target domain; **31 = all OK**. dmesg is bounded by `/dev/kmsg` markers and read by content, never by line count (the ring buffer wraps — the #39 lesson).

| test | domain | file (label) | result |
|---|---|---|---|
| control | su (permissive) | Bionic libc (data_local_tmp) | 31 (all ok) |
| global path | normal_hap | Bionic libc (appdat / data_local_tmp) | **26** — `open` fails: normal_hap can't *traverse* the `data_local_tmp` dir |
| execve | normal_hap | tp_probe41 binary | EXIT 126 (no entrypoint; expected, app never execve's) |
| **private ns** | **normal_hap** | **Bionic libc.so (appdat, /asx)** | **31 — all OK** |
| **private ns** | **normal_hap** | **Bionic linker64 (appdat, /asx)** | **31 — all OK** |
| private ns (control) | normal_hap | production libart.so (appdat, /asx) | 31 — identical |

`normal_hap` denials on the success path: **0**. `execmem` (anon mprotect PROT_EXEC) is allowed under normal_hap — matching ART's `WESTLAKE-OH-JIT ... anonymous cache with RWX` fallback; `memfd` RX is denied (13), but Bionic loads `.so` by file-mmap, not memfd, so that doesn't block it.

**Answer ①: YES.** In the real app context (u:r:normal_hap:s0, uid 20010053, private namespace) the Bionic linker64 and libc are `open`+`mmap(PROT_EXEC)`-able from the appdat runtime root — the *identical* result to the production libart.so the app already loads — with **0 SELinux denials and no sepolicy change**. Bionic would be loaded by the same fork+setcon+dlopen path the app already uses.

---

## ② metasec: loaded, never initialized, not the blocker

Config: #38 best (`libmetasec_ml.so` routed through ART's isolated namespace with the `libwebview_bionic_shim.so` bionic-ABI boundary). Examined `process-identity-11/{toutiao-1,2,3}`; compared to Android reference `N100CU025C18D000128`.

| | Android reference (S2 logcat) | OH westlake (toutiao-1/2/3, consistent) |
|---|---|---|
| dlopen | `Load …libmetasec_ml.so … : ok` (**once**) | attempted **repeatedly** from `/asx/lib/arm64-v8a` and `/data/data/com.ss…/app_lib`, via the bionic shim; **no load error** |
| **init `MSTaskManager::DoLazyInit()`** | **runs** (`E METASEC : …`) | **never — 0 occurrences in all 3 runs** |
| crash | none | **no metasec crash**; an intermittent SIGSEGV at ~75s (2 of 3 runs) is in `libart.so` on `Worker-thread-1` (the #38 bd_tracker/ART worker crash), stack entirely libart.so; the #23 static-`vfork` crash (0x2043b8) did **not** occur |
| feed | full | renders — view-tree shows `SSTabHost / StreamViewPager / FeedCommonRefreshView / FeedCommonRecyclerView itemCount=3` |
| app reach | `Displayed MainActivity +4s`, tab switches, refresh | privacy-consent dialog + populated feed; article-open blocked by input/focus (#34/#38) |

So on OH metasec sits in a **loaded-but-not-initialized** state: the loader keeps resolving it through the shim (vs Android's single `ok`) but the actual security init `MSTaskManager::DoLazyInit` never fires. The initial feed does not hard-depend on it (3 items render), but signed/deep operations (login, video, personalized refresh) do and are at risk. `DoLazyInit` is exactly where metasec's Bionic-ABI assumptions live — `pthread_self()==tls[1]`, `cached_pid@+20`, the static `vfork` (per [#35](../2026-09-25-hanbin-toutiao-port/)) — and under OH musl + shim that init does not complete.

**Answer ②:** metasec is **loaded** (dlopen via shim, no error, no crash) but **not functionally initialized** — `MSTaskManager::DoLazyInit` runs on Android and never on OH. metasec does not crash and is **not** the current visible-feature blocker (input/focus + the ART worker crash are). Its anti-tamper/signing is inert/unconfirmed under musl+shim.

---

## Recommendation: advance Bionic, but stage it behind the current blockers

- **Advance.** ① removes the SELinux unknown — real Bionic is loadable in the app process with no policy change (0 denials). ② shows the concrete payoff: metasec's `DoLazyInit` doesn't run under musl+shim, and real Bionic (whose ABI those checks assume) is the principled way to make it run as on Android.
- **But not as a quick unlock.** metasec is not today's binding blocker — the feed already renders; the visible failures are input/focus (#34/#38) and an ART worker crash. Bionic is a **stability/correctness investment** (~98 person-days of client shims + ART boot-image matching, per [#39](../2026-09-25-bionic-pt-interp-poc/)), sequenced after those blockers.
- **Next Bionic step** is #43 (M2): run `dalvikvm64` on AOSP14 ART/i18n APEX + boot image + BCP + the #39 Bionic linker/libc, to prove ART itself runs on real Bionic before committing to the 57-library rebuild.

## What is verified vs not

**Verified:** app domain = u:r:normal_hap:s0 (uid 20010053); Bionic linker64+libc mmap-PROT_EXEC-able in that domain in the private ns (== production libart), 0 denials; metasec loads on OH; metasec `DoLazyInit` does **not** run on OH (runs on Android); no metasec crash; feed renders.
**Not verified / deferred:** metasec functional signing on OH (no gorgon/argus markers — likely inert); login/video/personalized-refresh under OH metasec; whether real Bionic makes `DoLazyInit` run (that is #43→); the ART worker (bd_tracker) SIGSEGV root cause.

## Layout

| path | what |
|---|---|
| `results.json` | machine-readable answers, tests, verdicts |
| `evidence/t1-namespace-mmap.log` | the ① exit-code matrix + app-domain facts |
| `evidence/t1-run.log` | raw board transcript of the initial (global-path) T1 runs |
| `evidence/metasec-evidence.txt` | ② OH-vs-Android metasec grep evidence |
| `evidence/faultlog-toutiao1.txt` | the 75s ART worker SIGSEGV faultlog (not metasec) |
| `scripts/dommap.c` | OH-musl setcon→mmap(PROT_EXEC) helper (exit-code encoded) |
| `scripts/tp_probe41.c` | #39 probe + self-reported SELinux domain |
| `scripts/verify_t1.sh` | push-and-run T1 driver (kmsg-bounded avc, only /data/local/tmp) |
