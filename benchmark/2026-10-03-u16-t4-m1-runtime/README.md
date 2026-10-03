# U16 t4 — M1 split onto the U15 runtime native (oc-t4, offline)

Per `specs/u16-batch/t4-m1-freeze.spec.md` + cc-wiki's `benchmark/2026-10-03-m1-split/`.
**Not deployed, no freeze registration** (the outer registers FZ-009 after the 3-app
re-verify on this build).

## Base (verified, not from memory)

`$WORKSPACES/westlake-inputs/generations/u15-runtime-m3-v1/payload/android/lib64/
liboh_android_runtime.so` = `94c31177709dbea0…` (the U15 M3 candidate; results.json
`release` field + re-hashed locally).

## Build (hw248, mirrors the M3 recipe's link mechanics)

`build_t4_hw248.sh` (this dir, run on hw248's live cc-t3-u15rt-m3 mirror):

1. argv sanity: pristine `link-argv.txt` = 112 items.
2. Per pass: `EGLImpl.o` keeps the **m3-a** object (M3's EGL fix stays in);
   `android_graphics_compat_shim.o` → **shim_split.o** (the m1-split round's object,
   `003a4edb…`, compiled with the same frozen recipe — that round reproduced the deployed
   baseline `40aa2f5f` and M1 `612236be` bit-for-bit); **m1_copy.o** (`3e2b4323…`) appended
   right after it; output redirected to `t4-<tag>/out/`. Rewrites asserted ==1 each.
3. Result: **113 argv items** (112 + m1_copy.o); passes a and b → **byte-identical**
   (`cmp` clean). Candidate SHA: `1d42dbfb473f87e8…` (full hash in the ACK).

`evidence/link-pass-a.log` = pass-a link log (tee'd from hw248); the two split objects were
SHA-verified again on hw248 before linking.

## A′ proof (evidence/, verbatim outputs)

- **`a-prime-symbols.txt`** (script `a_prime_symbols.sh`):
  - existing **787 exports identical** (base vs candidate sorted dynsym diff empty);
  - **+1 export = `android::m1_native_window_from_other_copies`** — the split TU's entry
    (the documented TU-boundary consequence; the base had it inlined/file-local, symbol name
    `…12_GLOBAL__N_112_GLOBAL__N_1…m1_find_own` there);
  - undefined dynsym diff empty (the pair resolves inside the .so);
  - **NEEDED identical**; `M1-COPY` byte count 1 = 1 (candidate vs base).
- **`a-prime-insns.txt`** (script `a_prime_insns.sh`): `m1_find_own` and `m1_collect_others`
  normalized disassembly (addresses/relocations masked) **IDENTICAL** to the base's copies —
  the moved scan logic is instruction-for-instruction the same.
- **`a-prime-opensites.txt`**: open_site_scan 197 sites / 0 edges **= 197 / 0** — no new
  open sites, no namespace edges.
- The shim's "+1 call only" was proven at object level in the m1-split round
  (`shim_split.o` = baseline + one contiguous call region; 0 m1 symbols/strings/relocs) —
  the same two objects (same SHAs) are what this link consumes.

## Files

- `payload/liboh_android_runtime.so` — the artifact (not in landing-paths; U16 generation
  bundle; FZ-009 pending the 3-app re-verify)
- `build_t4_hw248.sh`, `evidence/{link-pass-a.log, a_prime_symbols.sh, a-prime-symbols.txt,
  a_prime_insns.sh, a-prime-insns.txt, a-prime-opensites.txt}`
- `README.md`, `landing-paths.txt`
