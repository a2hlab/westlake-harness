# G16: observed load failures, exact providers, and bounded reuse

The final Unity JNI exception is not the first loader error. This slice does not
modify or run the game. It also does not treat an installed SONAME or a parent map
as a provider selected by the exited child.

- Original log SHA `8a82fca6c80d4baa42e3c26ac0bfe01dbdd5d73ddd6ba8c0a5962d3e0fa8aa4f`,
  647865 bytes: original lines 3103–3104 / 3129–3130 show `__errno` relocation
  failures. Execution continues. Lines 3244–3249 show `libGLESv2.so` unavailable
  to `libyuanshen.so` in `westlake.anl.app.10029.2`, then the fallback main load
  fails. Lines 3652 / 3674 / 3703 record the unbound Unity JNI method, initChild
  failure and exit code 1. Public references use the new `exit-log-excerpt.txt`
  and `log-provenance.json`, snapshotted under `sources/`.
- Five real system ELF files and six route ELF files passed before/receive/after
  SHA checks. `/system/android/lib64/libEGL.so` was **not** received: both SHA
  and receive stdout report failure despite transport rc0. Stock platform EGL
  is a distinct path/object; see the independent graphics peer reference.
- Exact `libnativeloader b8be63d2` has a seven-entry shared-name array at VA
  `0xa528`, size `0x70`. PT_LOAD plus RELATIVE relocations yield android, EGL,
  log, mediandk, z, pthread-bridge and stdc++. GLESv2 is absent. The archived U13
  `u10-1-native-policy.h:47–55` agrees; current MAIN's six-entry source does not
  reproduce that table. The independent peer has closed the exact U13 source/build chain and 15 raw
  logs; G16 did not replay the build or verify all 607 headers. Shared seven
  was already baseline; U13 changed the separate system_libraries media_jni alias.
- Exact `libbionic_compat b8a87f6f` does not define `__errno`; it imports
  `__errno_location`. `native_abi.c:43–46` supplies the existing public adapter.
  A current map/export script alone cannot prove that code was in this child.
- Exact `libGLESv2 befb6ec7` exports only `_init/_fini`, needs libc and has the
  GLESv2 SONAME. **This does not require replacing it:** exact Genshin has zero
  direct GL imports. Peer reports stock GLESv3 142/142 GLES2-core coverage and
  stock EGL 18/18 direct Genshin EGL imports, but GLESv3 has a different SONAME.
  Dynamic extensions and native-window/display/context ABI remain unproven.

## Smallest next step

1. Do not rerun the game merely to obtain an expired child map. Static proposal
   can proceed, while the final loader deployment path remains unapproved:
   system and route `74d1` loaders are byte-identical; route `74e6` differs.
   Runtime-provider line 2756 does not prove which loader was selected. Parent
   6274 birth 245324 is stable across collection but cannot replace child maps.
2. Use the peer-verified seven-entry U13 input and build chain,
   rather than editing the current six-entry header. A narrowly derived policy
   can expose the existing needed GLESv2 name while retaining all prior names.
   No GLES implementation rewrite is justified by current direct imports.
3. Keep the public `__errno -> __errno_location` implementation as a deferred
   reuse option, not part of this minimal change. The errno failure was caught
   and execution continued; there is no direct evidence that it caused this
   exit. Only the GLES dependency visibility failure is the current candidate
   for removing the observed exit-related blocker for `genshin`. A future errno
   change must independently bind its provider scope. Do not inject the whole
   native cluster or Boat private C7/C4 patches.

The existing five REA method raw files were SHA-checked; no new REA was run.
Unity loadLibraryStatic logs and returns false on load error; its fallback is
not successful loading. FMOD's AudioTrack code is static only. Prior Boat or
Toutiao sound and signal fixes do not establish this game's runtime path.

`evidence-index.json` pins source snapshots and line ranges. `evidence/exact-elf.json`
contains actual ELF findings; `evidence/llvm-index.json` binds real local tool
argv/stdout/stderr/rc. Private originals remain under the documented aliases.
No devices, builds, deployment orchestration, game changes, or protection changes
were performed. Child maps/environ were not captured; parent environ was not read.
