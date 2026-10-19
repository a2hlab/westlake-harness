# Same-invocation window observation proposal

This is a design only. No runtime observer, binary change, build or device call was performed. Completed packet pins and a relay-ready ACK are in completed-packages-ACK.json; the canonical board is outside this lane's writable sandbox.

The smallest successful chain records libandroid765 ELF **0x3bd4** before `br x2`: x2 is the real bridge_symbol/dlsym result used immediately, and x30 is the restored original caller return address. Observe that dynamically captured return address in the same thread before the caller proceeds; x0 is the actual fromSurface result. A probe at 0x3be0 would capture the NULL failure path, not a successful return. No second dlsym call is needed. The earlier exact helper proof (r10-window-contract-review/provider-delegate.stdout.txt) establishes the data flow from dlsym 0x3814 through x0 to x2.

At shim85 ELF **0x5e48**, before its first instruction, capture x0 as the lock argument and the wrapper fields at that event. Read +0 as uint32; only after magic 0x5f776e64 matches, inspect +0xc8 (0x414e5731) and +0xc0 (OH pointer). Preserve failed reads as unknown. Do not interpret a mismatching object as raw OH or dereference +0xc0 speculatively. Snapshot both at fromSurface return and lock entry, not later using an address in a log.

fromSurface and lock can be on different threads and are separate calls. Use per-thread call sequence/return PC/SP for the former and a bounded object-generation association for the latter. Observe release at libandroid765 0x3c24 as a conservative invalidation marker. Pointer equality alone cannot exclude destruction/reuse; missed events, duplicate live generations or tracing gaps remain unknown. A release event alone does not prove destruction.

Actual caller selection uses the exact player SHA and executable PT_LOAD ranges, with fromSurface/lock/release import GOT ELF slots 0x472688/0x472490/0x4724b8. Recompute current load biases and mapped file identities; do not reuse r10 addresses. Resolve the captured winner against the actual mapped instance and exact ELF. The 0xd720 bridge handle and native_ready=1 are not function/object/geometry evidence.

Implementation prerequisite: the outer must select a supported execution-observation mechanism able to capture registers and readable memory at these boundaries without patching target bytes or invoking target functions. This proposal does not claim such a backend is already available. Debug-register changes or paused threads affect timing and must be explicit. No fallback instruction patching, global preload or new tracing framework is prescribed. A 30-second/32-record bound is sufficient for one useful chain; incomplete capture remains unknown.

These observations decide the object contract only. They do not establish buffer request/flush success, rendered video, audio or a safe global replacement for existing WebView consumers.
