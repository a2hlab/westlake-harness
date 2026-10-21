# G26 exact native-cluster candidate (offline only)

G24's observed first fatal was `libyuanshen.so` missing `__register_atfork@LIBC`.
The existing native-cluster ABI also covers the two exact main-library FD imports.
Membership alone would omit `libmediandk.so` from the native app's shared edge.
This candidate changes three copied source files: exact package membership in host
and ANL, plus mediandk in the exact Genshin native domain's app-to-bridge shared list.
It adds no leaf library, owner, open-site, runtime/audio publication, or game patch.

| Build | Baseline reproduced | Candidate | Bytes |
|---|---|---|---:|
| Host | `2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e` | `ee5649f2778430e1c997f4bb2d4d4f42f53a46208b4a1b1bbaca185ddf401887` | 646840 |
| ANL | `eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c` | `640b3c87e2f0f86d31b7defbd8b892515636afa61dcbbab5030d422ec1fb7d86` | 60208 |

All eight compile/link commands returned zero. Host was executed by inner on Mac;
ANL was executed by outer using the frozen inner recipe after the inner OrbStack
entry timed out (rc124). No VM restart or alternate compiler was used. The first
mistaken orbctl pathname (rc127), Git ref rejection (rc128), and case-insensitive
fixture-directory collision remain recorded. The latter was fixed in test setup;
production sources did not change. Both builds preserve recorded DWARF source and
working-directory identities via explicit path mappings. Neither old stage script
nor historical source/output was modified.

## Validation and exact scope

- 255 peer-listed inputs were independently rehashed. Frozen registry check:
  **8 entries, 30 checked, 0 violations**; this is not full runtime closure approval.
- Actual production ANL C and host namespace functions execute with fake OH boundary
  callbacks: **37 ANL domains and 50 host routes per version**, baseline and candidate.
  Tests capture exact shared strings, all 13 existing native and 6 Flutter selectors,
  three Genshin input sources, lookalikes/case changes, reuse, private-root admission,
  caller GLOBAL rejection, foreign namespace and owner lookup failure.
- Host's 216 normalized dynamic symbols and ordered 12 NEEDED entries are unchanged;
  ANL's 46 symbols and single NEEDED entry are unchanged. Comparison includes version,
  binding, visibility, type and OBJECT/TLS size. Both have no TEXTREL. Repository
  `abi_diff.py` also passed for both. This is not a function-prototype inference.
- Exact game `3dd8a20d…` imports `__register_atfork`, `__FD_SET_chk`, `__FD_ISSET_chk`
  at LIBC; unchanged private ABI `d2053066…` defines all three at LIBC. Its known
  atfork DSO-unload/unregistration limitation remains.

## mediandk and owner boundary

`evidence/owner-source/native_loader.cpp:97-99,118-120` passes policy bridge paths.
`native_bridge_policy.h:19-26` names `/system/android/lib64` and
`/system/lib64/platformsdk`. Candidate ANL `flutter_domain.inc:42-51` adds mediandk
only for Genshin native selection. Host `candidate-stock-host.c:329-334` inherits
that exact shared list from the configured bridge. The bridge is created with
CREATE_INHERIT_DEFAULT at lines 185-186. **mediandk is not in the host direct-owner
list at lines 278-284.** This is the existing configured bridge route, not a new
GLOBAL publication or an observed runtime winner.

The exact payload `libmediandk.so` is `8fc0752d…`, NEEDED only libc, with no strong
runtime/dlsym import. Native `libandroid.so` `ee2fb82c…` needs runtime/surface/libc;
existing default and sealed-child inheritance remains unchanged. `needs_runtime`
(lines 285-290) is unchanged and does not gain Genshin. Native GLESv2 `4b653941…`
needs GLESv3/libc; native zlib `50b9ab6a…` needs shared_libz. No additional resident
or audio publication was justified or added. Existing native system-OpenSLES
behavior is not a claim that the game reaches or successfully uses audio.

The exact host scanner records eight existing named open-sites. Its zero named
ANL open-sites does not mean zero opens: ANL uses host callbacks (`ANL_Dlopen`
0x4230; `flutter_prepare` namespace callback 0x46e8 and Flutter-only preload
callbacks 0x472c/0x4758/0x4784). Actual OH inheritance resolution and provider winner
remain UNKNOWN, as do complete loading, frames, audio, later failures and playability.
This does not support changing an already initialized domain across applications.

## Reproduction and retained inputs

Run `check_delivery.py --routes` for local C regression and fixed receipt checks.
Use `build_host.py --variant baseline --out NEW` then candidate with
`--baseline-receipt`; use Linux `build_anl.py --out NEW` for gated baseline then
candidate. `--workspaces` explicitly selects the retained workspace inputs. Both
refuse an existing output directory. Recipes use the exact U13 baseline pair and
N3 ANL commands; no N5 replacement and no runtime/ABI rebuild.

`evidence/raw-index.json` binds real argv/stdout/stderr/rc, receipts and dependency
outputs. Raw stderr and binaries stay private. `evidence/input-closure.json` binds
135 actual dependency/link-input copies (7,965,046 bytes) under
`$G26/.private/input-closure/`; source snapshots are public. The host reuses original
stock objects/archives and provider libraries: this is **not a full-source clean
rebuild**. Exact toolchain hashes and original paths are indexed; no tools were
installed. Historical source reconstruction beyond these inputs is not claimed.

Aliases: `$G26` is this directory in the producing worktree; `$WORKSPACES` its
workspace parent; `$HOME` is the private artifact owner's home; `$MAIN` is the
outer canonical checkout. The raw locations are persistent local evidence, not a
claim of remote archival. This report grants no deployment authorization.
