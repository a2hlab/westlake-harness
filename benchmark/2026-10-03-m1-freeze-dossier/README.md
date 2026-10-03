# M1 freeze dossier — materials for freezing the `[M1-COPY]` cross-copy Surface rescue (register after U13 promotes)

#90, offline, no board. **Materials only — this does not touch `knowledge/frozen/`.** M1 = the `[M1-COPY]`
cross-copy window/Surface lookup in `android_graphics_compat_shim.cpp`, carried in the deployed U13 runtime
`18763dd4`. M1 has cleared the freeze bar in the signed U13 stage-A decision; this dossier assembles the
pinned identities, the ≥2-app evidence, and the file-split plan so the outer can register it **after U13
promotes to the unified state**. (`frozen-entry.draft.json` = the draft entry; `evidence/m1-identities.txt`
= every SHA/blob; `evidence/verified-apps.txt` = the apps; `evidence/split-plan.md` = the granularity plan.)

## What M1 is (mechanism, one paragraph)
The process has **two loaded copies** of `liboh_adapter_bridge.so`; each owns its own
`OHWindowManagerClient::sessions_` and answers only through a single last-published-window slot. The runtime
compat-shim's resolved bridge copy is **not** the one that ran `createSession`, so for a **multi-window** app
the first-created (top) Activity misses and gets an **empty Surface → white** (this was the Jetpack-Compose
"alive but white", not a Compose-pipeline wall). `[M1-COPY]` (R3): when the resolved copy returns null, ask
**every other loaded bridge copy** — located by `dl_iterate_phdr`, matched by byte-identical code at the same
executable offset (same file) — and return the first non-null `OHNativeWindow`. Only the null-miss path
changes. (Full mechanism: `benchmark/2026-10-02-m1-session-slots`; closure: `benchmark/2026-10-03-wikipedia-m1-closure`.)

## Freeze bar — MET and exceeded (AGENTS 做事方式 3 / FROZEN.md)
Rule: **≥2 different apps past the wall, ≥1 lit at t20**, the others shown by log (that API's failure gone,
first fatal moved). Here **3 apps pass**, **2 lit at t20 by read screenshot**, each carrying the `[M1-COPY]`
rescue log — the API-level proof, not just the app:

| app | board | k/n | t20 (ground truth) | `[M1-COPY]` rescue log |
|---|---|---|---|---|
| **fd-uhabits** | 5ea | 6/6 | **LIT** — Loop "欢迎" welcome page (read) | `hilog:26912 sessionId=1243 resolved by bridge copy …(resolved copy …returned null)` |
| **wikipedia** | 5cd | 6/6 | **LIT** — onboarding "全世界的知识" + globe (read) | `hilog:20769 sessionId=954 resolved …` |
| **noice** | 61b | 1/1 | signed LIT — own welcome page | `hilog:33018 sessionId=964 resolved …` |
| fd-noice (corrob.) | 5ea | 6/6 | — (lottery-tagged) | `hilog:15830 sessionId=1255 resolved …` |

Signed by the outer in `benchmark/2026-10-03-u13-stage-a-decision/outer-stage-a-common.json`
("fd-uhabits 6/6 own welcome page … M1 runtime shim"; "noice (61b) 1/1 … M1"; "wikipedia 6/6 window1").
**Caveat (honest):** these Compose runs recorded `foreground_unconfirmed` (no view-tree/input dump) — a
capture limitation, not a regression; "lit own-UI" is supported (signed t20 + controls phase), full input
dispatch is not programmatically proven. One tap/scroll probe at freeze time would certify interactivity.

## Pinned identities (see `evidence/m1-identities.txt` for the full list)
| what | identity |
|---|---|
| source (R3 snapshot) | `android_graphics_compat_shim.cpp` blob **`8ad95199`** (westlake-harness master, commit `64d7e6594b`); content sha `e28f4bc3` |
| M1 needle | `…/patch/android_graphics_compat_shim.cpp.patch` blob **`7521ab2b`** (`@@ -442 +442,90 @@`, the isolated change) |
| alt bridge route (not deployed) | `bridge-m1.patch` blob **`f6545404`** |
| changed object | `android_graphics_compat_shim.o` **`612236be`** (baseline/control **`40aa2f5f`**) |
| deployed runtime (.so, not frozen whole) | `/system/android/lib64/liboh_android_runtime.so` **`18763dd4…fbae`** |
| build | `build_runtime_u13.py` + receipt; clang `b107ce03`, recipe_n4 `b318681e`; `u13 == u13-repeat` byte-identical |

**Single-variable proof the `.o` delta *is* M1:** the build receipt's `control` variant (`ac59dec0` = all
U13 fixes **minus** M1) has `shim.o = 40aa2f5f` = baseline; `m1` and `u13` have `612236be`. A′ faithfulness
(commit `64d7e6594b`): exports identical, undefined `+dl_iterate_phdr` only, strings `+[M1-COPY]` only,
dlopen open-sites `198 == 198`.

## How to register — the file split (the dispatch's core ask; full detail in `evidence/split-plan.md`)
M1 sits **inside the multi-purpose `liboh_android_runtime.so`**, in the **shared**
`android_graphics_compat_shim.cpp` (also SQLite stub / AAssetManager / BBQ Surface / EGL). The granularity
rule forbids freezing the whole `.so` (locks every other U13 fix) **and** freezing the shared `.cpp` blob
(freezes unrelated code). Because the M1 change is already an isolated `namespace { … }` block (needle
`7521ab2b`):
- **Preferred:** split it into its own file `android_graphics_m1_copy.cpp` (the `m1_*` helpers +
  `m1_native_window_from_other_copies`), leave one call line in the shim, rebuild, re-verify
  (new `android_graphics_m1_copy.o` carries M1, `shim.o` returns to `40aa2f5f`, runtime stays abi-`18763dd4`,
  3 apps stay lit), then **freeze that new file's source blob** (like FZ-003/004/006/007/008).
- **Fallback (if split deferred to the next U15 rebuild):** register provisionally by pinning the shared-file
  source blob `8ad95199` **+** the needle blob `7521ab2b` **+** the object `612236be` **+** runtime `18763dd4`
  as context — weaker (pins a shared file's whole content), so treat as temporary and split at the first
  rebuild.

## This round's rule
Freeze a runtime fix at the **source granularity that keeps other fixes landable**: for a fix buried in a
shared file inside a multi-purpose `.so`, the materials must carry (a) the isolated needle so the change can
be lifted into its own file, (b) the single-variable `.o` proof that the object delta *is* the fix, and
(c) the A′ faithfulness of the built `.so` — so the outer can split-then-freeze a source blob rather than
freeze a whole artifact. The ≥2-app t20 bar is about the **API** (every app carries the `[M1-COPY]` log),
not any one app.

## Files
- `frozen-entry.draft.json` — the draft registry entry (schema-matched; `status: draft-pending-promotion`).
- `evidence/m1-identities.txt` — every SHA/blob, the receipt variant table, the single-variable proof, build.
- `evidence/verified-apps.txt` — the 3 (+1) apps: board, run, t20 path, `[M1-COPY]` hilog line, facts.
- `evidence/split-plan.md` — the file split (preferred) vs `.o`+source-blob (fallback) + check_frozen wiring.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push. **Does not modify `knowledge/frozen/`** — registration is the outer's after U13
promotion (FROZEN.md: register first, deploy second; the outer assigns the FZ-00N id). The split-to-own-file
is a build step for the runtime owner (cc-t3). Sources read read-only: the M1 source/patch/receipt
(`westlake-harness benchmark/2026-10-02-m1-session-slots`), the signed decision
(`benchmark/2026-10-03-u13-stage-a-decision`), the stage-A runs + t20 jpegs (`westlake-harness-u7-executor`),
the frozen schema (`westlake-harness knowledge/frozen/{frozen.json,FROZEN.md}`).
