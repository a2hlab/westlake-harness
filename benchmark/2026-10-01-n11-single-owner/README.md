# N11: one resident bridge/runtime owner across ClassLoaders

The old smoke gate counted paths, so two loads of the same ELF path passed. N10b 5cd maps actually contain ART=1, JVM=1, bridge=2 and runtime=2. The N11 oracle counts load instances with master c2508ebdd and retains that failed historical evidence.

## Source identity correction

The donor double-load report inspected legacy `child_main.cpp`. Signed U8 provider 0509fe23 contains `child_main_after_stock.cpp`, lacks the INPUT-RT-CL-CHILD string, and its actual class-loader injection uses NOLOAD with no fresh fallback. Its big-stack source and build recipe are recorded in `westlake-harness-bms-deploy/benchmark/2026-09-30-child-stack-default/`, baseline 0509fe23. Actual U8 runtime 216b68fb likewise already contains the N2 compat-shim NOLOAD-only implementation. A stale dlerror saying runtime is not loaded does not prove a fresh runtime load occurred in that function. These facts correct the load-site attribution; the two-instance maps remain ground truth.

## Candidate

Use N10b's sealed owner preload and OH6.1 host callback permissions. Add direct ClassLoader app/bridge namespace inheritance for exactly `liboh_adapter_bridge.so:liboh_android_runtime.so`; intercept only these two canonical names/paths in the host open callback and return their **resident** sealed-owner handles. A missing owner returns null and never retries a fresh load. Ordinary app libraries keep their current namespace, flags and path. This makes the Java NativeLoader use the same owner as unchanged Route-A class-loader reinjection. The compat shim retains NOLOAD-only semantics and adds `[N11-WM-OWNER]`. Host callback success logs `[N11-CL-OWNER]`.

OH6.1 musl commit 02dd8d82887b040b85a4294e9a5039f016fd607a is preserved in the N10b evidence directory. `dynlink.c:2408-2448` examines direct inherited resident objects; `LOCAL_NS_PREFERED` can defer name reuse, but `:2572` checks inode reuse before a new map. Sharing both owners directly and opening the canonical resident handle avoids relying on recursive inheritance. This is ordinary loader API use, no ELF patches or signal changes.

The source donor is the U8 N4 host recipe (`westlake-harness-bms-deploy/benchmark/2026-09-30-n4-native`, local branch history), N2 compat shim and N10b native fixes. Source SHA and exact commands are recorded. Host baseline reproduces 1d3b0881 byte-identically; runtime baseline reproduces 216b68fb. Both candidates independently repeat. Provider/FZ-002 0509fe23, bridge 84695d62, ART, Java and images stay unchanged. Frozen AssetFd and VelocityTracker object hashes stay unchanged.

The candidate bundle has native manifest f6e5672c and requires **160 exact exceptions**: N10b's 154 retained plus 6 new bounded N1 findings (five standard logging/dl calls and one dynamic owner-path open). None is silently accepted; `exception-proposal.json` awaits outer approval. N2 has 103 unchanged findings. No device I/O has occurred.

## Authorized 61b window

After production approval and dry-run: master board_run `--detach`, after_lock apply, controls + fix smoke, instance count ART/JVM/bridge/runtime=1 each, then Wikipedia and fd-noice five runs each. Both target logs must have zero unknown sessionId; outer reads t20 against same-board baseline 3/6 each. Window <=30 minutes, before_unlock restores U8 312 identities and e953c0921536 / 4db882a81732. Any gate failure skips targets and rolls back. UI/owner results currently **unverified**. Passing native merges with N10b and J10b in one U9 package; no separate rollout version.
