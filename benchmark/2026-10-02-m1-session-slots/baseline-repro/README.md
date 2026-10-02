# Baseline first: bridge 84695d62 cannot be rebuilt byte-identically from any source we have

The outer loop asked for a baseline before the M1 change (2026-10-02). The bridge build scripts on master are now
hardened: `9c14005a01` / `0c8639ba1b` (cx-bms B10 #72, `bb12d761ed`) turn missing sources, headers and link inputs
into `exit 1`. With those scripts, first reproduce the deployed bridge `84695d62` byte for byte; if that fails,
report the differences before touching the M1 cpp.

**Answer, static, before any build: it cannot be reproduced.** Three independent differences, each enough on its own.
`source_match.py` → `source-match.txt`.

## 1. The window client version in 84695d62 is not in any source tree

**Search.** Every copy of `oh_window_manager_client.cpp` that has the deployed binary's
`refusing orphan child` string:
- local: 22 files, 7 distinct versions;
- plus this repo's `bms/src`, and real-work's `oh61-v7-b2133b5b` snapshot.

**Two-way check against the binary's window-client strings.** Adjacent literals are joined before comparing.

| version | copies | source-not-in-binary | binary-not-in-source |
|---|---|---|---|
| `0b816fe6271c` (bms-deploy 2026-09-29 unlocked-generation, cc-wiki-b1 tree) | 7 | 3 | 2 |
| **`89183eb549d9`** (real-work oh61-v7, bms-deploy b87-native, …) | 9 | 2 | 3 |
| other 4 versions | 1–2 each | 2–3 | 3–5 |
| `bms/src` (this repo) | 1 | 19 | 15 |

Every version misses the binary's process-published RSSurfaceNode path:
- `getRSSurfaceNode: no local or process-published RSSurfaceNode for sessionId=%d`;
- `getRSSurfaceNode: acquired process-published cross-namespace surface sessionId=%d node=%p`.

Each version instead still has the older `getRSSurfaceNode: unknown sessionId` / `has no RSSurfaceNode` strings,
which the binary does not have.

**Not found in any of the three places**, in the source lookup order:
- **local:** every `*.cpp/*.h/*.cc/*.patch/*.diff` under `$WORKSPACES`;
- **a2hlab:** `$HOME /opt /srv /data`, `*.cpp`;
- **hw248:** `/home/alvin` `*.cpp/*.patch/*.diff`, `grep` rc=1 in 17 s (complete, no match). Tarballs were not
  unpacked.

The window client that went into 84695d62 is a version newer than every copy we have.

## 2. `oh_canvas_renderer.cpp` was not in the deployed build; the hardened script compiles it

- Its 18 literals of ≥ 16 characters: **0 in the binary**. It is the only translation unit (TU) of the 49 with ≥ 3
  literals and none present.
- `OHCanvasRenderer::drawRect / drawText / drawPath / drawBitmap / clipRect / clipPath / drawColor`: **0** in the
  binary's dynamic symbols.

This fits the outer's guess: the 2026-09-28 scripts skipped a missing or failing source with `continue`, so the
bridge was built without it. The hardened script globs `framework/surface/jni/*.cpp` and now compiles it. A rebuild
gains a TU the deployed bridge never had.

## 3. `display_manager_adapter_jni.cpp`: the deployed bridge used the oh61 copy, the script forces the other

| copy | literals in binary |
|---|---|
| oh61-v7 snapshot copy | 3/4 |
| `bms/src/.../framework/window/jni` copy | 3/16 |

The hardened script deliberately excludes the oh61 copy and compiles the framework copy (comment: "selecting that
copy would silently hide fixes"). A rebuild changes this TU too.

## Also: this repo cannot run the hardened script as is

`OH61_WINDOW_SOURCE_ROOT` defaults to `$ADAPTER_ROOT/sources/oh61-v7-b2133b5b/framework/window/jni`, and
`bms/src/adapter/sources/` does not exist. The hardened script therefore exits 1 at the first window source. That is
correct behavior; the 2026-09-28 script would have built a bridge without the window client.

The window cohort the bridge really uses is the oh61-v7 snapshot, not `bms/src/.../framework/window/jni`. The M1
patch in `../bridge-m1.patch` is written against the `bms/src` copy. The deployed lineage carries the same single-slot
code (`publishProcessWindowTarget` / `readProcessWindowTarget`, 3 references in `89183eb549d9`), so the same change
has to be ported to the oh61-v7 copy if this route is taken.

## What this means for M1

A baseline that matches 84695d62 needs all three of these, and none exists:
- the missing window client version;
- a source set with `oh_canvas_renderer.cpp` excluded;
- the oh61 `display_manager_adapter_jni.cpp`.

So "two builds byte-identical; `deployed_strings_diff` vs 84695d62 differs only in M1" is not reachable. Per the
dispatch, no M1 build was started.

**Options for the outer:**

- **(a) Reconstruct the source.** Recover the missing window-client version (ask cx-bms / the B6–B8 lanes where the
  process-published RSSurfaceNode change was written) and pin the oh61-v7 cohort into a repo path. Rebuild with
  `oh_canvas_renderer.cpp` excluded and the oh61 display-manager copy, check against 84695d62, then apply M1.
- **(b) Accept a new bridge baseline** built from the hardened set: whole-library change, `abi_diff.py` exit 0,
  full sweep.
- **(c) Put M1 in the runtime's compat shim** (R3 in `../README.md`). The runtime has a per-object reproducible
  chain (N10b `build-runtime.py`), and only `android_graphics_compat_shim.o` changes.
