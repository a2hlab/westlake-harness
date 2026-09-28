# Route A architecture decision: stock appspawn host + Android child plugin

## Decision

Route A is selected. WestLake will not reproduce OH's decoder, manager,
hook engine, fork coordinator, sandbox, token, SELinux, DAC, or result pipe in
a parallel daemon. It will run an AppSpawnX-named instance of the stock host
and install one OH module whose child processor starts Android only after the
stock child pipeline succeeds.

Route B—the separately built full-engine POD wrapper—remains a fallback only
if the stock host build boundary becomes unavailable. It is not the next step.

| Question | A: stock host + child plugin | B: full POD wrapper |
|---|---|---|
| Socket / request lifecycle | stock `StartSpawnService` on `AppSpawnX` | parallel adapter socket lifecycle |
| Decoder and message owner | stock `AppSpawnMsgNode` / `AppSpawningCtx` | copied decoder and wrapper-owned contexts |
| Fork / child result | stock `AppSpawnProcessMsg` and response pipe | wrapper must reconstruct the sequence |
| Security operations | stock common + sandbox modules | stock sources linked into another owner |
| Android-specific code | final child processor only | wrapper plus caller integration |
| Drift surface | one host main, one plugin, one fail-closed check | full engine/manager/msgmgr/common closure |
| HanBing result | preferred boundary plugin | valid fallback, larger duplicated owner |

## Startup path

`westlake_stock_host_main.c` keeps the stock preload helper and creates the
stock service with:

```text
mode        = MODE_FOR_APP_SPAWN
moduleType  = MODULE_DEFAULT
socketName  = AppSpawnX
serviceName = appspawn-x
```

Before `StartSpawnService`, it explicitly installs
`/system/lib64/appspawn/libwestlake_android_child.z.so`. Creating
`MODULE_DEFAULT` first is deliberate: the later stock
`AppSpawnLoadAutoRunModules(MODULE_DEFAULT)` does not scan
`appspawn/appspawn`, so the ACE child processor cannot race or overwrite the
WestLake child looper. `MODULE_COMMON` is still loaded unchanged, including
the stock security and sandbox modules.

The plugin is inert when stock ModuleMgr loads it. MAIN first checks the exact
real path, file SHA-256, ELF Build-ID, and `WlascContractV1`; it then obtains an
`RTLD_NOLOAD` handle for that exact DSO, proves both exported symbols originate
in that file, and installs one versioned table by value. The table carries the
five stock hook/message capabilities plus the MAIN-owned runtime callbacks.
Only a successful one-shot install registers hooks. Its server-preload hook
runs at priority 3001, after normal sandbox config preload at 3000. It requires
the service identity `appspawn-x`, rejects an existing child looper, and then
uses the provider identity to bind the callback table before ART preload.

## Per-request path

```text
stock socket receive
  -> DecodeAppSpawnMsg + CheckAppSpawnMsg
  -> stock AppSpawningCtx owns the decoded message
  -> stage 20, STOP_WHEN_ERROR
       stock parent hooks
       priority 6000: WLAR_ZygotePreFork + parent tail ledger
  -> stock fork
       parent stage 21: WLAR_ZygotePostForkParent
       child stage 30: AccessToken and child environment
       child stage 31, STOP_WHEN_ERROR:
         1000  stock cache/internet
         2999  WestLake rejects NO_SANDBOX / IGNORE_SANDBOX / missing TLVs
         3000  stock sandbox
         3500  stock sandbox mount marking
         4000  stock properties, DAC, capabilities, SELinux
         6000  WestLake child tail ledger
       stock pre-reply
       stock success result pipe
       stock post-reply
       WestLake child processor
         -> fixed C/POD request + pointer-free stock-stage receipt
         -> WLAR_EnterAndroidAfterStockSpecialization
```

The stage-31 tail is not a fabricated `sandbox_applied=true` flag. Stock
`AppSpawnExecuteSpawningHook` runs the hook list with
`HOOK_STOP_WHEN_ERROR`; therefore priority 6000 is reachable only when every
earlier hook in the frozen generation returned zero. The receipt says exactly
that both frozen tail positions were reached and the bypass guard passed.

The parent ledger is set before fork and inherited by copy-on-write. It binds
the exact `AppSpawnClient` address, message id, and runtime generation. The
address is used only inside the OH-owned module; it never crosses into the
Android runtime ABI. The exported runtime request contains fixed buffers and
integer values only.

## One necessary stock-host delta

OH v7 `ProcessSpawnReqMsg()` invokes stage 20 with flags zero and ignores its
return. That is incompatible with an ART parent: if `ZygoteHooks.preFork()`
fails, forking can inherit locks owned by live daemon threads.

The candidate therefore changes that one call to
`HOOK_STOP_WHEN_ERROR`, sends the stock error response, deletes the stock
spawning context, and returns before fork. The patch is
`patches/0001-parent-prefork-stop-on-error.patch`; its exact applied source is
under `stock_host_patched/`. The patched service compiles as a deterministic
AArch64 final-link object. No security hook or object ownership moves.

## Runtime provider and final host

The adapter-owned runtime provider now defines six typed symbols:

```c
int WLAR_GetRuntimeIdentity(WlascRuntimeIdentityV1 *);
int WLAR_ServerPreload(WlascRuntimePreloadReceiptV1 *);
int WLAR_InstallHostRuntimeServices(
    const WlascHostRuntimeServicesV1 *);
int WLAR_ZygotePreFork(uint64_t generation);
int WLAR_ZygotePostForkParent(uint64_t generation);
int WLAR_EnterAndroidAfterStockSpecialization(
    const WlascAndroidChildRequestV1 *,
    const WlascStockStageReceiptV1 *);
```

`WLAR_GetRuntimeIdentity` is side-effect free and makes it possible to bind
generation and provider SHA before any ART/native-loader work.
`WLAR_InstallHostRuntimeServices` copies the table by value and rejects wrong
ABI/size, null functions, cross-generation/SHA, duplicate installation, and
callback reentry. It creates no provider-to-MAIN undefined edge. The provider
then maps server preload to `AppSpawnXRuntime::startVm()`/`preload()` and the
parent functions to the existing zygote methods. The child function validates
the fixed request and stock receipt, verifies the already-applied uid/gid,
constructs `WlncProcessIdentityV1`, and calls MAIN-owned compatibility
admission exactly once. Only successful admission may translate the request and call
`ChildMain::runAfterStockSpecialization()`. That translation unit therefore
starts at zygote post-fork, followed by adapter initialization and
ActivityThread; it does not own a second guard preparation. Neither path
contains a mount, procattr, token, UID/GID mutation, capability, DAC, sandbox,
or SELinux operation; the legacy security-bearing `child_main.cpp` is not
compiled into the provider.

The deterministic final host now links the frozen stock sources, the patched
service, the provider DSO, the freestanding WLTG registry, and the main-ELF TLS
reservation. The ART side consumes the certified 23-member v12 provider base,
except that its old compatibility, app-loader, and host-fake Palette DSOs are
not used in the final set. Route A rebuilds the same seven-source compatibility
surface with the unsafe guard reset replaced by a terminating trap, rebuilds
the app loader with a WLTG READY callback before guest `dlopen_ns` and
`dlclose`/destructors, and builds
the real OH priority Palette boundary. The remaining 20 provider DSOs are
frozen byte-for-byte. Only the real recursive `DT_NEEDED` graph is initially
loaded; the rebuilt `libartpalette-system.so` stays outside the initial global
scope until its typed lazy edge is requested.
Every deployment DSO and the final host use
`-z defs --no-allow-shlib-undefined`. The plugin has a real `DT_NEEDED` edge
to the provider; the provider has no circular `appspawn-x` dependency; and
MAIN preparation/verification functions remain private behind the installed
tables. `ROUTE_A_INPUTS.json` binds every direct source, auxiliary header,
provider manifest, tool-generation manifest, and link library used by this
final link.

## Remaining activation blocker

Final link is not product activation. `startVm()` also has two dynamic roots
that must be built in this same generation: the ARM64 adapter runtime and
adapter bridge. Historical outputs are ineligible (mixed architecture, or
missing SONAME/Build-ID with RUNPATH), so neither may be copied into this
candidate. The bridge may be observed only through `RTLD_NOLOAD`, followed by
exact path/SHA/Build-ID verification; a side-effecting direct-load fallback is
forbidden.

The receipt-bound MAIN admission now
uses the WLTG registry, but the required Bionic invariant is broader: one
canonical per-process CSPRNG guard must be copied to slot 5 of every admitted
Android thread. The pre-guest loader READY gate is integrated; namespace-pthread
creation and JNI attach are not yet integrated in this generation. CardWords'
frozen native set has no Bionic `__stack_chk_guard` consumer, and Musl's global
guard is deliberately neither read nor written. Until the remaining admission
paths and true-cold evidence pass, `product_activation=false` is mandatory.

Three unused OH features are deliberately stubbed for this candidate: OH
prefork process caching, trace emission, and DFX stack dumping. The socket,
decoder, contexts, normal fork, stages 20/30/31, security modules, response
pipe, child watcher, ART, adapter, and ActivityThread paths are not stubbed.

## Frozen provenance

The complete 430-file OH v7 appspawn tree is now project-local. Its manifest is
`SOURCE_CLOSURE.json`; tree SHA-256 is
`1a113881bb525ea29b29ed6ffaea3948b8f64cea0a88ab978458894c503448d4`.
Target compilation uses only this closure plus the project-local frozen OH
clang/sysroot, pinned container image, and the direct link inputs frozen under
`stock_child_plugin/frozen/`.
