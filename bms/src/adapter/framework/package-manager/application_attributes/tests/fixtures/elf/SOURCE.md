# ELF fixture provenance

These are real ET_DYN ELF objects, built from the adjacent C files with GNU gcc
11.4.0 / binutils on Linux x86_64. `rebuild.sh OUTPUT_DIRECTORY` builds both
32-bit i386 and 64-bit x86-64 without a C runtime or platform SDK. The fixtures
are read as data, never executed. The build machine/location is not an input to
the analyzer or test command.

Each consumer has exactly four PT_LOAD segments, one DT_NEEDED
`libfixturedep.so`, the export `fixture_export` and the required symbol
`fixture_dependency`. The dependency fixture really exports that symbol.
The test's segment values are taken from GNU `readelf -h -l -d -s`, not from a
second implementation of the analyzer. Both SysV and GNU hash tables are present.
Stripped-section and rejection cases are explicit byte mutations of these
compiler outputs; the entry digest is recomputed for structure mutations.

| Artifact | SHA256 |
|---|---|
| consumer.c | `da7c22a4e369523f483149dd00554f9aab8d7809cecabb774c81cebbbeec3df0` |
| consumer32.elf | `93e7df829459ca6068fef3eaed5e41b298a328a807cdb4bfe037fd12aa76d81f` |
| consumer64.elf | `1e5e4069e2b3c350ce4d2230cb9a8e7e1482682e877b8dd6db51874a0e6d3a27` |
| dependency.c | `0a1a37bfe95845f36817bd07fffdfb3bd8a8258a066dfda43e9f8a0b921c2c04` |
| dependency32.elf | `fae5a45a8482f45d263416899ecf01b2fdf8a98ad0c7eb89a933c53da2e0fa51` |
| dependency64.elf | `a5da3b97751ffbd15cf209cb78da948feaa89d267f31595d712edce89b5fb803` |
| middle.c | `6e58ec2b405345b5a3327aea7bc0c5999f166a8d49ef9f559cf0ced46112393d` |
| middle32.elf | `481610ce624978c480cf9cea4447750f8c0839ac4afb483234c80de7730011c3` |
| middle64.elf | `7378d076636580446349f269e29c158da769fde53911c76cd7790aa80503ab5d` |
| rebuild.sh | `0d36055e983825eb3146c629411364dd2f021f927eecd299ec7d4a1c00600c24` |
| root.c | `637b40d607a69dae068095cbf9fb323980b33b1285b9cf5b27cf1250e5d6813c` |
| root32.elf | `920a3bae6abc5a526dce3de1c6499f116524f29dc7f942dcd571b14ae26c57a6` |
| root64.elf | `8f29627a20791ab4be75c2e99ea1e52b79703a61fd31b055c47fdab3296275b6` |

Format references: [System V ELF header](https://gabi.xinuos.com/elf/02-eheader.html),
[program headers](https://gabi.xinuos.com/elf/07-pheader.html),
[dynamic linking](https://gabi.xinuos.com/elf/08-dynamic.html).
Android r4 source checks below bind the class/machine, program range, dynamic
string/symbol and GNU/SysV hash formats. This analyzer is read-only. It does not
load, relocate or install the library, and is not evidence of loader/CTS success.

- [bionic/linker/linker_phdr.cpp](https://android.googlesource.com/platform/bionic/+/android-16.0.0_r4/linker/linker_phdr.cpp), SHA256 `943673b813f671c5f17c72571bd00b56416ff4e61f76d13a77ddb37bdbe684cf`.
- [bionic/linker/linker.cpp](https://android.googlesource.com/platform/bionic/+/android-16.0.0_r4/linker/linker.cpp), SHA256 `6281c8bd8bd8c3904c910740a5e31f8357aeb63b4194898a47c221670881c89b`.

Second-round fixtures add real GNU-built ELF32 and ELF64 chains:
`libroot.so → libmiddle.so → libfixturedep.so`. The root imports
`fixture_dependency`, exported by the leaf, while declaring only the middle
as DT_NEEDED. Full available facts resolve this transitive symbol; a missing
leaf is rejected as a dependency error. These use the same `rebuild.sh` and no
additional compiler requirement. The independent review originally reproduced
the case with Zig ELF64; committed cases are rebuilt from that C source in both
GNU fixture architectures.

Negative PT_DYNAMIC cases alter its virtual address to an unmapped range or to
a different file-backed LOAD region while retaining the original p_offset. The
analyzer must reject both rather than report facts from bytes the loader would
not read. Android r4 `linker_phdr.cpp:1647` uses load_bias + p_vaddr;
`linker.cpp:1793–1804` builds its symbol lookup group from the dependency tree.
