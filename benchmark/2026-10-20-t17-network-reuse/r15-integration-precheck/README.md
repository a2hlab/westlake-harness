# R15 minimum production integration precheck

The accepted R15 is an offline typed adapter, not a loadable runtime. No source
or original build evidence was found missing in its existing scope. This review
ran no build and no device command. Existing `verify.py` rechecked original host
15-stage and OH 6-stage receipts, raw argv/stdout/stderr/rc, source/header/tool
hashes and artifacts: rc0. Current MAIN `check_frozen.py` also returned rc0,
8 entries / 30 checked / 0 violations. Public verify output is exact; the frozen
output contains local paths and is preserved privately with its hash index.

## Already available

Paths below are under `benchmark/2026-10-19-toutiao-video-playback/`.

| Input | Existing evidence and scope |
|---|---|
| R14 ABI/state machine | `candidate-r14-offline/window_module.{h,c}`. C SHA 1f42a393; header 28a88796. Header lines 11–29 define injected callbacks, borrowed conversion, fence ownership and one instance per ownership domain. C lines 10–12 assert Android buffer 48 bytes/bits@16/reserved@24 and Rect 16 bytes. |
| R15 typed adapter | `candidate-r15-provider-offline/provider_adapter.{h,c}`. C 5fc32ea5; header 3eae43c1. C lines 7–19 assert LP64, OH Rect/Region layout and seven SDK function signatures. Individual signed32 copies at +4/+8/+12/+16/+20 consume only a trusted stable 24-byte prefix. |
| Build recipe | `candidate-r15-provider-offline/build.py:25–64`: source locks, check_frozen first, consumed dependency hashes before/after, original command triplets. Host links R14+R15+test; OH compiles only R15 ET_REL. Existing missing-`stdbool.h` attempt is preserved; accepted header includes it. |
| Exact OH object | `evidence/oh-receipt.json`, `evidence/oh-readelf.txt`: 7648 bytes, SHA 5a3ed9e2b604b288f8fa88c218fea35b88649424a88011f8cf8b3df506e27528. It is not a DSO. R14 OH object is separately recorded in `candidate-r14-offline/oh-object-evidence/`. |
| Runtime link requirements | Both recorded objects have six undefined symbols: calloc, free, pthread_mutex_init/lock/unlock/destroy. OH provider functions are injected pointers, not unresolved direct imports. These object tables do not prove a future final DSO's dependencies or namespace winners. |
| Durable originals | R15 archive `HW248_ARTIFACT_ROOT/toutiao-window-r15-offline-20261020/window.tar.gz`, SHA f09e313f01757d6211c22ec68fccb7820848d2a1b0b850cf42c6a188bf39c676, 1,077,410 bytes / 1,280 members. `archive-evidence/outer-receipt.json` supersedes the preserved first failed upload; no new network access here. |

## Minimum remaining prerequisites, in order

1. **Observe the actual caller and provider instance.** Current 5cd wrapper type,
   owner, lifetime and trusted unwrap remain unknown. The exact prior surface
   ELF 8f1879f8 evidence is file evidence; check the actual 5cd provider SHA and
   selected namespace/object before reusing that implementation contract. No
   arbitrary pointer inspection or ambient dlsym fallback is supplied by R15.
2. **Add only a separate integration unit after that evidence.** It must provide
   seven correctly typed OH callbacks, trusted unwrap, monotonic clock, poll
   with saved errno, and owned-fd close; initialize one R15/R14 pair per ownership
   domain. Prevent calls during destroy and destroy R14 first. Keep raw provider
   rc separate from adapter refusal. Do not add a retry or reclaim failed slots.
3. **Supply a real production caller and link recipe.** Existing source has no
   factory/resolver, Android entrypoint/export route or OH shared-library recipe.
   The current OH recipe has neither `-shared` nor `-fPIC`; it is intentionally a
   compile-only check, not a broken production build. A new reviewed PIC/link
   recipe must pin source/toolchain/sysroot, record raw rc0 logs, declare exports
   and dependencies, and scan final ELF/open sites and namespace selection.
   Do not replace the large shim wholesale or assume natural preemption.
4. **Keep existing gates and ownership semantics.** Run frozen checking again
   before any new build/deploy; retain R14 exact source pins and SDK ABI asserts.
   The 44 fake-provider cases and current OH compile do not establish deployed
   ABI, safe wrapper lifetime or writable buffers. Preserve Map0/-1 suppression,
   uncertain Map cleanup refusal, Abort0 not proving lower release, bounded
   eight slots and no failed-slot reuse. Real fence/geometry/Map/Unmap/Flush
   observations and dynamic video/audio remain separate bounded acceptance.

No existing host build/interface defect requiring an immediate source fix was
found. The useful next increment is the narrow binding/entrypoint/link unit once
current object evidence exists, not another R14/R15 rewrite or repeated REA.
