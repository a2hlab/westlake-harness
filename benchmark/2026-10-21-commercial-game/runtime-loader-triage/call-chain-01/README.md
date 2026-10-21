# G16 static call chain and the original paired publication rule

Equal file bytes and mapped addresses do not identify an active loader winner.
This slice closes the static call chain and the historical publication rule,
not the missing runtime relocation or deployment-ownership evidence.

## Exact chain

| Object | ELF location | Established operation |
|---|---|---|
| archived libart 59e1bb45 (same G05 file fingerprint) | LoadNativeLibrary call 0x4f52c4; JUMP_SLOT 0x94ee40 | imports OpenNativeLibrary@WESTLAKE_NATIVELOADER_1; DT_NEEDED libnativeloader.so |
| deployed/received libnativeloader b8be63d2 | OpenNativeLibrary 0x38f8; call0x3b1c | class-loader path enters its Registry::Open at0x5ec4; null class-loader uses SystemLoader instead |
| same libnativeloader | call0x5b60 / slot0xaa10 | Registry::GetOrCreate calls ANL_CreateDomain |
| same libnativeloader | call0x6588 / slot0xaa40 | Registry::Open calls ANL_Dlopen |
| deployed/received ANL eebd62f2 | ANL_CreateDomain0x31f4; indirect call0x35dc | formats app PID/id name, invokes configured namespace host callback |
| deployed/received host2a87118e | StockCreateConfiguredNamespaces0xcc68 / StockOpenNamespace0xd4ec | creates configured domains / delegates actual library open to dlopen_ns |

The exact U13 policy source has the seven-name shared list. `native_loader.cpp`
161–190 and registry215–247,365–379 show the explicit chain. ANL source53 and
395–422 show its atomic counter starting at1: suffix `.2` is not an inode,
namespace owner identity, or proof selecting either mapped copy.

All direct **BL and tail B** open sites were enumerated for the host, archived
child plugin, nativeloader and ANL ELF. Host has one plain-dlopen site and seven
dlopen_ns sites. Archived child has one plain tail-dlopen site and four
RealOpenLocalNow dlopen_ns sites. Loader/ANL have no direct dlopen sites in these
ELFs: their callback/PLT edges remain essential. Counts do not cover resolved
indirect targets in other DSOs. Raw full disassemblies, exact argv, stderr and rc
are indexed privately; public excerpts and per-site PCs are included.

Archived `n10b-child.c:247–300` creates `westlake.sealed.child` with a search root
from the provider's directory, opens the provider there, and preloads bridge and
runtime in the same namespace. The exact archived plugin's callsites support
that path. Its pathname appears in attempt2 maps, but this new capture did not
hash that plugin through proc-root. Do not promote archive identity to a newly
measured child-plugin hash. Similarly the recorded route ART pathname and G05
file fingerprint do not reveal its live OpenNativeLibrary relocation winner.

## Why preserve both aliases

Original U13 `namespace_gates.py:14–16` assigns the *same candidate output* to
`payload/android/lib64/libnativeloader.so` and `payload/route/libnativeloader.so`.
`report.py:81–82` records paired rollback to the same previous bytes. Attempt2
now confirms both file identities really mapped concurrently. This supports
retaining the original paired publication invariant rather than selecting only
one alias based on a guessed winner. It is **not** a new deployment plan, and it
does not establish whether changing just one alias would affect this request.
No reason here to replace ANL, rewrite GLES, or batch the deferred errno gap.

The remaining entry/namespace winner is UNKNOWN. An already saved resolution
record of ART's OpenNativeLibrary target and loader-to-ANL bindings would close
it; no such record was provided. No dynamic hook/injection/new window is requested.
Current generation ownership is separate: this source analysis cannot invent an
owned state for a boot missing from local generation-state (G19 responsibility).

No device, environ, build, candidate, or prior accepted report changes.
