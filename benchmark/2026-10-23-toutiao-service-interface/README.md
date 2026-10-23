# T53 — existing service interface remains unproven

**GAP, not implementation READY.** Two candidates were inspected locally; neither has
an exact-version, registered bridge endpoint with proven ordinary-host admission.
T52 naturally exercised gone/zombie recovery but candidate views stayed white. Its
restored feed is not close/reopen acceptance. The previously proven host callbacks
were not replayed. No device, remote, REA, service request, runtime change or runtime build ran.

## Exact host and caller evidence

The actual retained T32 signed HAP was read locally: `b18978b8…`. Its `module.json`
is `0dbaacbe6b17eadecda308d65e77483bf87fe2971695fecac1a5b55a5d137b51`, byte-equal
to the `df385638…` original HAP and the T32 main-tree member receipt. The complete
non-secret member is retained at `evidence/t32-signed-module.json`. It registers only
EntryAbility, no extensionAbilities, and requests INTERNET and GET_NETWORK_INFO.
The unbound VM-copy manifest (`d65c563b…`) was not used as the signed package identity.
EntryAbility's VM-copy bytes do equal the exact 9dc baseline; this says nothing about
manifest or whole-package equality.

The independent **2026-10-22 final restored** bm sample has SHA
`0f1f1e67e94be91a188652bb438e87232d40dfd0a936c16d58086880c5bc245b`:
`appPrivilegeLevel=normal`, `isSystemApp=false`, `accessTokenId=537137511`,
`uid=20011300`, `appProvisionType=release`, **`permissions=[]`**.
HAP requested permissions are not granted permissions. This historical sample is
current-known evidence, not today's fresh authorization and not evidence that any
particular public endpoint will admit the caller. Original bm output stays private;
results records its HOME-relative path, range, SHA and exact extracted fields.

## Two bounded candidates

| Candidate | Existing evidence | Remaining blocking gap |
| --- | --- | --- |
| UIAbilityContext service connection | SDK `UIAbilityContext.d.ts:1811-1839` declares `connectServiceExtensionAbility`, visibility/permission failures. | SDK metadata is 6.1.1.125/API24; same-board 6.1.0.31 client, server admission, registration and build implementations are absent from the inspected kit. No owned bridge handler/registered target is proven. A declaration cannot provide these. |
| Historical AppSpawnX transport | `native/host_spawn.c:1-52`; `spawn_server.cpp:419-457`; `main.cpp:300-328`; `BUILD.gn:29-107`; historical client recipe `stage_candidate.py:66-70`. | These historical native sources are not a supported normal-host API. Config `appspawn_x.cfg:27-60` declares a root service and root:appspawn/0660 socket. Current deployment/protocol/build binding and ordinary-host authorization are unverified. No root/internal call is recommended. |

Paths above are under `$WORKSPACES/vm-copies/westlake-current/` except the SDK file.
Every full locator, line range, SHA and computed blob is in `results.json.source_refs`.
Computed blobs do not imply committed or deployed provenance. Main inputs identify
fixed base `8bfba21cfb` and separately indicate whether bytes match that Git object.
Client and server permission evidence have separate status/ref fields.

The root condition/once recovery service and same-boot directory refusal remain
**harness controls**, not a third public service candidate. Their actual references
are `recovery.cfg:7-34` and `boot-entry.sh:11-27` in results. Nothing here changes
flags, clears attempts, grants permissions, or gives observer JSON authority.

## Exact source handoff gap

RUNBOOK:56 records `/opt/build-trees/oh610_lts_source` as OH **6.1.0.31** on hw248.
It was not accessed. The inspected local kit is
`$WORKSPACES/oh61-bms-kit-background-launcher/foundation/ability/ability_runtime/`.
These exact local paths are absent, and the checker rechecks their absence:

- `frameworks` — same-version JS/native client implementation and IPC chain.
- `services` — connection dispatch, caller token/UID checks and permission callees.
- `BUILD.gn` — implementation membership and target dependencies.
- `bundle.json` — component metadata; actual service registration/profile still needed.

The prior main report `2026-10-03-category-home-token/README.md:40-44` names
`ability_manager_service.cpp` and explicitly records unavailable AMS source. Its
nested source location and the permission-helper filenames are **unknown**, not
invented paths. The exact requested component is
`foundation/ability/ability_runtime` under the recorded same-version tree. Outer
source intake must supply the real client/dispatch/check/registration/build closure
and version identity; this report does not claim all missing code necessarily belongs
to the four local paths above. `missing_parts` distinguishes observed missing paths
from unverified endpoint/authorization bindings.

After those inputs arrive, the next decision is whether an **existing** owned handler
is registered and admits the ordinary host with its existing identity. If not, the
implementation prerequisite remains open. No new endpoint or permission workaround
is designed here, and no global claim that no service exists anywhere is made.

## Offline checks and delivery

```sh
python3 benchmark/2026-10-23-toutiao-service-interface/check.py --self-test
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_service_interface -- --nocapture
```

The verifier rehashes all local sources, exact signed HAP/module bindings and historical
caller facts, checks cited ranges and missing-state consistency. Ordinary and optimized
Python each accept the valid GAP report, reject a changed source SHA, reject READY
without server permission evidence, and reject `--require-ready` on the actual report.
Passing this checker validates evidence discipline, not interface availability.
`validation.json` binds actual receipts; original argv/start/end/stdout/stderr/rc remain
under `.private`. `landing-paths.txt` is the public handoff. No commit/push performed.
