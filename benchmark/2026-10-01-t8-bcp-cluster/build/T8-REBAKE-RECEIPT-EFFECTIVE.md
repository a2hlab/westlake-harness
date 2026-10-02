# T8 re-bake — EFFECTIVE base (rebuild receipt; fixes ACK(90) 2026-10-02 10:50:30)

**Date** 2026-10-02 · **Lane** cc-wiki · **Base** deployed U9 `j10g-238ffc14`, **effective** BCP.
**No deploy** — the deploy window is the outer ring's (held on the U9-vs-U10.1 base decision).

## Why this rebuild
The first T8 bake (`T8-REBAKE-RECEIPT.md`, stubs `255aad61`) patched `adapter-mainline-stubs` on the
generation's **native/payload UNDERLAY** (`beb369a1`). The board runs the **framework/ EFFECTIVE** copy
(`f3bcc9d7`), which carries three frozen APIs the underlay lacks: **FZ-007** (full tagsoup, `Parser`
super=`DefaultHandler`), **FZ-008** (`android.net.ssl.SSLSockets`) and `android.net.NetworkInfo$State`.
Baking from the underlay would have dropped them on deploy. rb/t4b/G1/G2 missed it because they compare
the candidate against an **image reference**, not the deployed jar; the new gate `deployed_class_diff.py`
(master `458ff94e`) compares against the deployed jar and catches it.

**The generation is an overlay**: `framework/` overrides only `adapter-mainline-stubs.jar` (f3bcc9d7) and
`oh-adapter-runtime.jar`; the other 8 boot jars have no override, so their effective copy is the
`native/payload/android/framework/` one. The effective 9-jar BCP boot set is therefore
**`native/payload` ×8 + `framework/` adapter-mainline-stubs (f3bcc9d7)**.

## What changed vs the first bake
- `adapter-mainline-stubs` base: `beb369a1` (underlay) → **`f3bcc9d7` (effective)**. Patches unchanged:
  **① add** `com.android.org.conscrypt.SSLParametersImpl` presence stub; **③a replace** the phonenumber
  shells with the full real AOSP libphonenumber. FZ-007 / FZ-008 / NetworkInfo$State are left untouched.
- `oh-adapter-framework` base: `f38ec312` (single copy, unchanged) + **② getInstallSourceInfo** → all-null
  `InstallSourceInfo` via the PUBLIC 4-arg ctor. Same as the first bake.
- Build script `GEN` is now explicit effective/underlay paths (no glob): `build_t8_effective.sh`.
- ③a reuses the already-compiled `t8-rebake/intermediate/libphonenumber.dex` (`dff827b5`, same source) →
  **no VM needed**; all smali/baksmali on the Mac.

## New SHAs
| jar | base | patched (T8 effective) | dex |
|---|---|---|---|
| adapter-mainline-stubs.jar | `f3bcc9d7` (effective) | **`2f365a75581bb739041390ac35bc0e39e894ac9e80c990bb64cfe7016d781ba5`** | 039 |
| oh-adapter-framework.jar | `f38ec312` | **`2257b835afda730a684fe6da81ac9658211af426e440da50f7d97762b2482cc1`** | 039 |

Boot image: `boot.art` **`d5b43805…`**, `boot.oat` **`4ba08485…`**, `boot.vdex` `23c1f5b0…`.
(The first, wrong bake was `art 54d37790 / oat 6c0569c8`.) Full lists: `receipt/{jar,image}-sha256.txt`.

## Gate — deployed_class_diff.py (the gate that caught the bug), both jars exit 0
`scripts/lab/deployed_class_diff.py` (master `458ff94e`). Raw output: `class_diff-*-effective.txt`.
- **adapter-mainline-stubs (2f365a75) vs deployed f3bcc9d7** `--frozen --allow-add
  Lcom/android/i18n/phonenumbers/ Lcom/android/org/conscrypt/ --allow-reshape Lcom/android/i18n/phonenumbers/`
  → `0 dropped, 0 reshaped, 0 added (after allow lists), 0 frozen class(es) broken` — **exit 0** (206→265 classes).
- **oh-adapter-framework (2257b835) vs deployed f38ec312** `--frozen`
  → `0 dropped, 0 reshaped, 0 added, 0 frozen broken` (58→58 classes; method body only) — **exit 0**.
- Pre-check confirmed the frozen APIs survive in the candidate stubs: FZ-007 `Parser` super=`DefaultHandler`,
  FZ-008 `SSLSockets` present, `NetworkInfo$State` present (25), `android/compat` leak 0.

## Four gates — all PASS (hw248 bake, `gate-rb-effective.txt`, `gate-g1g2-effective.txt`)
| gate | result | evidence |
|---|---|---|
| **rb** | **PASS** | oat **230**, `concurrent-copying=false` (RB-off, matches board R155), image **108** → safe to board |
| **t4b** | **PASS (satisfied)** | image-only, **libart untouched**; rb confirms oat230/CC=false/img108 = what board libart expects |
| **G1** | **PASS** | 7 unchanged segments checksum-identical to the stock-effective reference; the 2 patched = `swap(deployed together)` |
| **G2** | **PASS** | probe `java.lang.String#hashCode`: cand=36 insns, ref=36 insns → identical (explicit suspend-check) |

The **reference** image is a fresh stock-effective bake (`ref-jars9`: f3bcc9d7 stubs unpatched + 8
native/payload) so G1/G2 compare patched-vs-stock on the SAME effective base; its oatdump BCP is `ref-jars9`
(not native/payload, whose underlay stubs would checksum-mismatch the effective reference image).

## Toolchain (`receipt/toolchain-hashes.txt`)
- jar patch (Mac, java 21.0.6): baksmali/smali/dexlib2/util 2.5.2 + full guava 31.1-jre; `smali a -a 29` → dex 039.
- re-bake: **hw248** `dex2oat64` `/home/alvin/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64`
  (`ae865ddd…`, the proven RB-off baker of deployed U9; cmdline embedded in U9 boot.oat), RB-off,
  args byte-identical to deployed U9. **VM `out-aot42/tools/dex2oat` SIGSEGVs on a full boot-image compile
  (stock jars too), so bake stays on hw248.**
- ③a libphonenumber: reused `t8-rebake/intermediate/libphonenumber.dex` (`dff827b5`), source snapshot shared
  from `t8-rebake/src-snapshot/libphonenumber/` (byte-identical, same AOSP repackaged source).

## Landing (persistent archive)
`$WORKSPACES/westlake-inputs/generations/t8-rebake-effective/` (not in git; git records paths+hashes here):
- `jars9/` — the 9 effective BCP jars (7 base + 2 patched) fed to the bake
- `ref-jars9/` — the 9 stock-effective reference jars
- `image/` — the 27-file candidate boot image; `/tmp/u9-fresh-ref-eff/arm64/` — reference image (ephemeral)
- `receipt/` — `jar-sha256.txt`, `image-sha256.txt`, `ref-jar-sha256.txt`, `ref-image-sha256.txt`, `toolchain-hashes.txt`
- shared from `t8-rebake/`: `src-snapshot/libphonenumber/`, `intermediate/libphonenumber.dex`
- hw248: `/home/alvin/t8-cc-wiki/{incoming-eff,out-eff,ref-incoming-eff,ref-out-eff,bake_eff.sh,bake_ref_eff.sh}`

Repo: `build_t8_effective.sh` (the corrected builder), `class_diff-*-effective.txt`, `gate-rb-effective.txt`,
`gate-g1g2-effective.txt`, this receipt.

## Reproduce
```
source ~/orca/workspaces/westlake-inputs/env-mac.sh
bash benchmark/2026-10-01-t8-bcp-cluster/build/build_t8_effective.sh     # jars (Mac)
GATE=$WORKSPACES/westlake-harness/scripts/lab/deployed_class_diff.py
GEN=$WORKSPACES/westlake-generation-u9-j10g-238ffc14
python3 $GATE jars9/adapter-mainline-stubs.jar --deployed $GEN/framework/adapter-mainline-stubs.jar \
  --frozen --allow-add Lcom/android/i18n/phonenumbers/ Lcom/android/org/conscrypt/ --allow-reshape Lcom/android/i18n/phonenumbers/
python3 $GATE jars9/oh-adapter-framework.jar --deployed $GEN/native/payload/android/framework/oh-adapter-framework.jar --frozen
# bake on hw248: bake_eff.sh + bake_ref_eff.sh ; then rb + image_predeploy_gate.py (see gate-*.txt)
```

**Status: built + all gates PASS + deployed_class_diff clean on the effective base. Not deployed — for outer review.**
