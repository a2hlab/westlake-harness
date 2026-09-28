# OH-owned security specialization closure

## Verdict

The selected production direction is **Route A: stock OH appspawn host plus
one WestLake Android child plugin**. Its implementation and decision record
are under `stock_child_plugin/`. The stock host remains the sole owner of the
socket, raw decoder, request contexts, hook engine, fork, security operations,
result pipe, and child lifecycle. WestLake enters ART only through the stock
`RegChildLooper` seam after the stock child pipeline succeeds.

The raw-message/POD control plane in this directory remains a tested,
fail-closed **Route B fallback**. It does **not** implement SELinux, mounts,
namespace setup, DAC, or AccessToken operations itself. It is not the current
activation path and `product_activation=false` remains mandatory.

## Stock call order recovered from frozen OH sources

The exact stage values are `STAGE_PARENT_PRE_FORK=20` and
`STAGE_CHILD_EXECUTE=31`; common and sandbox priorities are 2000 and 3000.
They are frozen in `appspawn_hook.h:71-91`.

For the device's normal sandbox route, the sandbox constructor registers:

1. server preload / priority 3000:
   `LoadAppSandboxConfigCJson`;
2. parent pre-fork / priority 2000: `SpawnMountDirToShared`;
3. parent pre-fork / priority 3000: `InstallDebugSandbox`;
4. child execute / priority 3000: `SetAppSandboxProperty`.

The registrations are in the frozen
`normal/appspawn_sandbox_manager.cpp:90-101`. The stock service validates the
decoded message, creates `AppSpawningCtx`, attaches the decoded
`AppSpawnMsgNode`, runs parent stage 20 from priority 0, forks through the
normal spawn path, waits for the child's result, and only then reports success
(`standard/appspawn_service.c:1014-1057`).

The complete 430-file OH v7 appspawn source tree is now frozen project-locally
under `adapter/frozen/references/oh-appspawn-security-v7`. It proves the child
hook runner, decoder/context ownership, result pipe, and `RegChildLooper` seam.
Its tree identity and auxiliary inputs are recorded by
`stock_child_plugin/SOURCE_CLOSURE.json`.

## Route B fallback boundary

```text
raw OH message + SHA/config/DSO generation identities
    -> WLSS_ParentPrepare (envelope validation, no OH side effects)
    -> same-generation OH wrapper owns decoder + opaque contexts
    -> WLSS_ParentPreFork
         -> wrapper executes stock stage 20 from priority 0
         -> typed receipt must prove every parent hook completed
    -> fork
    -> WLSS_ChildExecute
         -> revalidate raw bytes and the complete stock generation
         -> wrapper executes stock stage 31 from priority 0
         -> typed receipt must prove result=0 and sandbox applied
    -> child may continue
```

The four callbacks in `WlssStockOps` are the only allowed bridge to the
production OH owner. Callback success is exactly `1`; a stock hook result is
successful only when exactly `0`. Every other value is terminal.

`WlssStockOps.context` must be request-local. The future OH wrapper places its
stock-decoded `AppSpawnMsgNode`, `AppSpawningCtx`, and manager references there
before fork; the child inherits those exact objects. No pointer layout crosses
the public POD ABI.

## Typed raw-OH-TLV record

`WlssSecurityRecordV1` retains the original immutable message pointer, size,
SHA-256 identity, complete two-word v7 flags bitmap, generation identities,
and one `WlssTlvSpan` for every standard or extended TLV. Extended TLVs retain
their raw offset/length, 32-byte name, data type, data length, and payload
offset. Owner, permission, internet, and arbitrary extension data are never
collapsed into the existing `SpawnMsg` projection.

This matters because the current product parser keeps only the first flag word
and explicitly skips owner, permission, and internet TLVs, while unknown
extension TLVs are also skipped (`spawn_server.cpp:566-630`). The new record is
an envelope and preservation layer; the stock decoder remains the semantic
authority.

For `MSG_APP_SPAWN`, preparation rejects:

- missing or malformed bundle, complete two-word flags, DAC, APL/domain,
  AccessToken, owner, permission, or internet TLVs;
- zero AccessToken, empty APL, malformed DAC/GID count, or malformed ext TLVs;
- `APP_FLAGS_NO_SANDBOX` and `APP_FLAGS_IGNORE_SANDBOX`;
- missing config, empty config identity, missing full module engine, empty DSO
  identities, generation zero, raw-message drift, or identity callback failure.

The explicit bypass rejection is necessary because stock normal sandbox code
returns success for `NO_SANDBOX` and converts any sandbox failure to success for
`IGNORE_SANDBOX` (`appspawn_sandbox_manager.cpp:31-62`).

Before both parent and child callbacks, the adapter rechecks raw identity,
stock/config identities, reparses the immutable envelope, and compares its
complete shape. Any failure publishes `WLSS_RECORD_FAILED`; failed records
cannot resume.

## Why direct DSO invocation is rejected

The frozen OH GN file builds `libappspawn_module_engine` as a native stub and
installs an empty stub under the runtime symlink name
(`modules/module_engine/BUILD.gn:34-64`). Device evidence confirms that exact
shape: the sandbox DSO is real, but the runtime module-engine alias has only
two exports and SONAME `libappspawn_stub_empty.so`.

The real sandbox DSO's exported C++ function is insufficient:

- `AppSpawnMgr` and `AppSpawningCtx` are only forward declarations in the
  public hook header;
- the function dereferences generation-private fields, queries decoded flags,
  config, mode, and namespace state;
- its constructor expects `AddServerStageHook` and `AddAppSpawnHook` to resolve
  from the owning appspawn executable;
- calling only the child function would omit server preload and parent hooks.

Consequently, `dlopen`/`dlsym`, fabricated structs, a handwritten mount path,
direct procattr, `NO_SANDBOX`, and fake receipts are all architecture failures.
The ELF gate rejects such primitives in this control-plane artifact.

## Selected Route A production build path

1. Build an `AppSpawnX`-named instance of the frozen stock OH host. Keep stock
   `ProcessSpawnReqMsg`, `AppSpawnChild`, stages 20/30/31, sandbox/common
   modules, response pipe, and all opaque object ownership unchanged.
2. Apply the one fail-closed parent delta recorded under
   `stock_child_plugin/patches`: stage 20 uses `HOOK_STOP_WHEN_ERROR`, and a
   failed ART pre-fork hook returns the stock error before fork.
3. Install the WestLake module explicitly under `MODULE_DEFAULT`. It rejects
   security-bypass flags before sandbox, records the successful stock hook
   tails, and registers the sole Android child processor via
   `RegChildLooper`. Do not load the competing ACE child processor.
4. Implement the four `WLAR_*` runtime-provider symbols and a security-free
   Android child entry beginning after specialization. It must not repeat
   AccessToken, DAC, sandbox, UID/GID, mount, or SELinux work.
5. Final-link the stock host from the frozen OH dependency closure. Only after
   a true-cold device run proves module load, stage-20 success, stage-31 tail,
   stock response success, and one Android child entry may product activation
   change to true.

Route B is retained only if the stock host build boundary becomes unavailable;
it is not an excuse to duplicate OH process or security owners.
