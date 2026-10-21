# G28 ordinary-icon launch: main-library failure advanced to `_ctype_`

The first **reported main-library blocker in the termination chain** is now
`libyuanshen.so: _ctype_@LIBC`, not G24's `__register_atfork`. This does not establish
which provider resolved atfork, nor complete relocation or game execution.
No device calls, builds, game/runtime edits or new REA calls were performed.

## Observed chain (original hilog line numbers)

| Time | Lines | Evidence |
|---|---|---|
| 22:02:07.947–.948 | 3118–3119, 3144–3145 | MHYComboCrypto cannot resolve `__assert2`; retry also fails. Later activity/load work continues. This is not proved to cause termination. |
| 22:02:08.430 | 3259 | Exact `libyuanshen.so` relocation cannot find `_ctype_`, version hash `50d63` (LIBC). |
| 22:02:08.432–.433 | 3260–3263 | Unity cannot load yuanshen, attempts main; main lookup fails in explicit `westlake.anl.app.14857.3`. |
| 22:02:08.814 | 3671–3675 | Uncaught `UnsatisfiedLinkError`: UnityPlayer.nativeRestartActivityIndicator; resume/onResume stack. |
| 22:02:08.871 | 3722 | Parent12781 reports child14857 exit code1. |

The exact game import is **OBJECT `_ctype_@LIBC`**, not a function. The reused
G04 `UnityPlayer.loadLibraryStatic` REA (raw SHA rechecked) shows System.loadLibrary
at source line4, success true at5, and UnsatisfiedLinkError catch/log/false at11–15.
The existing `<clinit>` DEX evidence selects yuanshen, then main on false. This
explains the generic Unity messages without inventing a successful library load.
The explicit namespace is printed for main; assigning that same namespace to
yuanshen remains an inference from the adjacent call flow.

G24's original L3276 reported atfork for the same exact main ELF. G28 has zero
atfork messages for PID14857 and reports `_ctype_` instead. This is evidence that
the observed blocker moved, not proof of the winning atfork address or semantics.

Both original images were read directly: first is white, later is the launcher
with the game icon. Neither contains a game frame. Images remain in private
originals, pinned in `input-sha.json`; no guessed alive counts are used.

## What the maps prove

Stat before/after both identify PID14857, PPID12781, birth1768375; all three reads
returned rc0. The name changes and R→S state do not change this identity. UID20011077
comes from the contemporaneous process record. The maps sample is at
**22:02:06.658**, approximately1.77 seconds before the `_ctype_` error.

System and route ANL paths map the same dev/inode `103:30/130771` at two distinct
address ranges; system and route nativeloader map different inodes130772/130774.
`libbionic_compat.so` is mapped at inode15381. No matching proc-root stat/hash was
supplied alongside these map rows. A namespace/caller winner is not encoded by
maps, and same bytes/inode do not imply a single loaded instance. Absence of
libyuanshen/d205 at this early sample does not prove absence during later loading.

## Next candidate cluster: analysis only

1. **First priority: existing locale/ctype ABI visibility.** Reuse the local
   `bionic_locale_compat.c` implementation (source SHA and lines in
   `source-excerpts.json`): `_ctype_` is an exported pointer to a257-byte table,
   EOF at0 and byte c at c+1; `strtoll_l`/`strtoull_l` forward to their non-locale
   counterparts. These three are imported at LIBC by the exact main ELF, and none
   is exported by d205. Only `_ctype_` is the current actual main-library failure.
2. **Existing providers already contain implementations.** Local exact payload
   bridge db31 exports all three as `@@LIBC`; compat b8a exports unversioned names.
   Neither fact establishes current app-domain visibility. Do not claim the linker
   must reject unversioned exports: the previously reviewed OH lookup can accept
   them under some version states. First decide whether to expose the existing
   same-owner implementation or deliberately consolidate the three into the
   already selected native ABI; no new single-symbol leaf is proposed here.
3. **Do not import a whole Unity stub unit.** `unity_libc_stubs.c:100–169` records
   the same historical pointer/table ABI and an OpenBSD/bionic source attribution,
   but neighboring unrelated stubs are out of scope. The original AOSP file bytes
   and exact build-to-export lineage of this locale TU are not independently
   closed by this addendum. Its comments are provenance claims, not new upstream
   verification. Existing compatibility source is local; no VM/network fetch was
   needed for this first slice.
4. **Batch review, without escalating all gaps to observed failures.** Check the
   above three exact names, LIBC versions, OBJECT size8/table257, symbol owner and
   all normal-domain regression cases together. Validate EOF/ASCII/high-byte
   classification and integer parsing/overflow/locale behavior in a future
   authorized implementation task. `__ctype_get_mb_cur_max` exists in the exact
   local musl reference; `__sF` is already in d205—do not duplicate them.
   `__assert2` is also a main-ELF import and absent from the inspected three bridge/
   compat/native ABI export sets; retain it as a secondary static gap plus MHY
   background error, not an observed main-library fatal. No game protections are
   modified or bypassed.

The older disk-closure model's empty native unresolved list did not prove runtime
visibility; this observed `_ctype_` miss is the concrete counterexample. The
minimal missing evidence is late app-domain owner/binding evidence for existing
ctype providers, or an exact source/ELF ownership proof sufficient to define the
next candidate. This report contains no dynamic-hook or device procedure.

## Recheck / references

`check.py` verifies the exact small packet, source/input SHA references and actual
stat/log relationships. `input-sha.json` binds full private hilog651400 bytes,
map/stat receipts, images, local provider ELFs, source excerpts and the reused REA.
`provider-matrix.json` describes **local reference objects**, not fresh winning
providers. `$REPO`, `$WORKSPACES` and `$HOME` are explicit storage aliases.
Large raw logs and readelf output remain private. Old G16/G24/G26 packets are unchanged.
