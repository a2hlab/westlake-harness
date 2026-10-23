# T54: ordinary host service connection, source admission

The missing T53 server source must not be replaced by a guess that every service connection requires a system app. In the supplied ability_runtime implementation, a normal foreground UIAbility connecting to an installed, local, same-user SERVICE is **not directly rejected by a blanket system-app gate**. This is a conditional source path, not proof that this host can register a SERVICE or rebuild its bridge runtime. The overall result remains **GAP**.

The second and final path, `connectServiceExtensionAbilityWithAccount`, explicitly throws **202** for a non-system caller once the argument-count check passes. Analysis stops at that rejection. No permissions, identities, service requests, builds, devices or T38 operations were changed or executed.

## Evidence and version boundary

`results.json` gives full SHA-256, computed Git blob IDs, exact line ranges and range hashes for 34 exact-byte public source/build files (2,745,686 bytes; 26 ability_runtime and 8 BMS). Copies under `sources/ability_runtime/` retain their original license headers; `LICENSE` is included. The default checker reads these copies, not a home-directory source cache. Computed blob IDs identify the supplied bytes; they are not a claim of an independently fetched upstream Git object.

The persistent intake is `$HOME/.local/share/westlake/t54-oh-source-intake-20261023/`. Its manifest SHA is `f471153f4144f82dc35dd3cb1fe0a842937e4301733b6563e3df8f30c07d0e48`, ability_runtime HEAD/revision is `101781d2eb1097eac5ff57d636af9d7127e5c6e8`, branch label `OpenHarmony-6.1-LTS`. The recorded local patch SHA is `33cc405794a06da8137f3b1cecff6d9bbd0020c5a6b7086389fc9946ffeb0461`: five appmgr files are modified; none of the 26 ability_runtime copies is in that patch/status list. Each ability_runtime copy matched the supplied source-index size/SHA, and source bytes stayed unchanged across copying. Only this selected subset was checked, not all 8,687 source entries.

Manifest, metadata and patch are copied under `provenance/`; tar and complete source-index remain in the persistent intake, with their hashes in `results.json`. This is source provenance, **not a binding to deployed libraries, build flags or active access-token policy**. Board-byte binding remains unknown.

T53 (`0a52f405ec`) supplies the exact signed `module.json` copy: EntryAbility, no extensionAbilities. Its historical 2026-10-22 caller observation is normal/non-system with `permissions=[]`; it is not fresh authorization. Manifest requestPermissions are not permission grants. T53 was not modified or rerun.

## Production call chain

Paths below are relative to `sources/ability_runtime/`. See the named source-ref in results for its full SHA and exact span.

| Link | Actual source and lines | Consequence |
|---|---|---|
| JS binding and ordinary entry | `frameworks/native/ability/native/ability_runtime/js_ability_context.cpp:2382`, `1847-1913` | SERVICE request. The system-app test at 1865 only changes displayId filtering. JS returns a connection ID immediately; mapped failures call `onFailed`. |
| Native context | `frameworks/native/ability/ability_runtime/ability_context_impl.cpp:1596-1604` | Uses the context token and ConnectionManager. |
| Connection management | `frameworks/native/ability/ability_runtime/connection_manager.cpp:56-110`, `147-177` | Default account; validates caller/callback, reuses matching connection or sends new request. |
| IPC client | `services/abilitymgr/src/ability_manager_client.cpp:609-620` | Calls proxy `ConnectAbilityCommon`. |
| IPC serialization | `services/abilitymgr/src/ability_manager_proxy.cpp:1395-1440` | `CONNECT_ABILITY_WITH_TYPE`, returns reply integer. |
| IPC dispatch | `services/abilitymgr/src/ability_manager_stub.cpp:220-229`, `1086-1097`, `1819-1843` | Checks descriptor, reads arguments, dispatches to AMS, writes actual result. |
| Server common entry | `services/abilitymgr/src/ability_manager_service.cpp:5244-5395` | SERVICE cross-user calls hit the system-app guard at 5268; same-user does not. Local branch reaches ConnectLocalAbility. |
| Resolve and admission | same file `5575-5725` | Resolves target, checks type/static permissions/interceptors/call-service permissions, then dispatches to connect manager. |
| Target connection | `services/abilitymgr/src/ability_connect_manager.cpp:325-423` | Existing connection, load or active-service dispatch; native ERR_OK is not completed connection or rendered UI. |
| Target implementation boundary | `frameworks/native/ability/native/js_service_extension.cpp:386-425`, `622-658` | Calls target's `onConnect` and extracts its RemoteObject. Does not supply a project-specific bridge operation. |
| Rejected account path | `js_ability_context.cpp:1915-1929` | Non-system -> `ERROR_CODE_NOT_SYSTEM_APP` (202); no alternate entry proposed. |

Build references are included for native context, JS bindings/service extension, IPC client/proxy, AMS/stub and permission verification. `services/sa_profile/180.json` registers framework library `libabilityms.z.so` in `foundation`. This **framework service registration** is distinct from eligibility to install/register a target HAP ServiceExtension and from an owned bridge endpoint.

## Conditions that remain real

AMS `IsCrossUserCall:16211-16222` and `GetValidUserId:10501-10505` distinguish user scope. Ordinary same-user connection still requires a resolvable target of the correct type: resolution failure maps to 16000001; wrong type to 16000002. `start_ability_utils.cpp:250-303` asks BMS for ExtensionAbilityInfo when normal ability resolution has no target.

AMS `CheckStaticCfgPermission:10898-10981` and `CheckStaticCfgPermissionForAbility:10839-10857` use the real calling access token. For the ordinary cross-token case, an empty target permission list or all required grants pass (the source also contains existing same-token and privileged exceptions; no new grant is proposed). Failure becomes `ERR_STATIC_CFG_PERMISSION` -> **16000005**. In `permission_verification.cpp:352-372,407-430`, an invisible cross-token target without the required permission fails -> **16000004**. The symbolic-to-JS mapping and numeric enum are copied.

Ordinary SERVICE sets `isBackgroundCall=false` at AMS 11791. This does not mean background access is unconditional: config-controlled `ShouldPreventStartAbility:14594-14649` can reject API>=12 cross-app UI-only background callers; a foreground caller passes that particular check. The before/after interceptors, DLP build branch, user constraints and other errors remain in force. `StartOtherAppInterceptor` returns early for this `isWithUI=false` request; `ExtensionControlInterceptor` does not apply the other-extension caller restriction to a normal UIAbility. This review does not claim every installed policy permits a chosen target.

## Remaining implementation prerequisites

1. **Target registration/runtime eligibility: still unknown; its SERVICE type rule is now source-bound.** The BMS dependency is `bundle_mgr_helper.h:21` (`bundle_mgr_interface.h`) and helper.cpp:599 (`IBundleMgr::QueryExtensionAbilityInfos`). The supplied BMS source and cx-env subreview establish the conditional privilege rule below. Actual build arguments, target signed capability/preinstall match and concrete installed registration remain unbound. Normal/non-system caller identity alone proves neither admission nor rejection of target registration.
2. **Owned bridge endpoint: not found/bound in this evidence.** Need a concrete target bundle/module/ability, registration, service-side RemoteObject/transaction implementation, authorization and bridge-operation/build provenance. Generic AMS transport cannot substitute for this. Absence of an owned endpoint in these inputs is not a claim that the entire device has no services.
3. **Token/backend and deployed binding:** `permission_verification.cpp:19,45,63` calls `accesstoken_kit.h`/VerifyAccessToken; the manifest identifies `base/security/access_token` revision `9e819c8933db91055b2962c3f244b17dfa6f6085`. That component is outside this intake review. Concrete target permissions and deployed component/configuration identity remain unproved.

Opening an application UI again and reconstructing the bridge runtime are different capabilities. This source review proves no bridge reconstruction endpoint and no white-screen fix.

## BMS registration finding integrated from cx-env

Eight referenced BMS files were independently hashed, read at the cited lines and copied verbatim under `sources/bundle_framework/`. The peer JSON is retained at `provenance/bms-admission.json` (SHA `fae9099aa5e34b5cdec4812a8bde677678839c2d2fd02ce38f387ada879247c3`). This integration does not retrace BMS beyond its cited evidence.

- `services/bundlemgr/include/privilege_extension_ability_type.h:25-32` includes SERVICE in the privilege set and leaves the system-only set empty. `bundle_install_checker.cpp:1552-1564` rejects a privileged type without effective `allowUsePrivilegeExtension`, returning **ERR_APPEXECFWK_PARSE_PROFILE_PROP_CHECK_ERROR**. This is not a direct system-only rule.
- `app_privilege_capability.h:28` defaults the capability false. Checker lines 100-103 and 1270-1286 read signed provision `appPrivilegeCapabilities` / `AllowAppUsePrivilegeExtension`. Lines 1364-1405 give explicitly present, signature-matched preinstall capability `allowAppUsePrivilegeExtension` precedence, including an explicit false value. This is not an ordinary requestPermission.
- Without `USE_PRE_BUNDLE_PROFILE`, checker lines 1282-1285 enable privilege extensions. `appexecfwk.gni:51` defaults the GN argument true and `services/bundlemgr/BUILD.gn:212-214,493-495` controls the macro. **The deployed argument and target's effective capability remain unknown; no change is proposed.**
- `base_bundle_installer.cpp:2213-2229,5333-5337` passes signature-verified inputs to parsing and propagates failure; checker lines 495-510 derive the capability and apply the gate.
- `extension_ability_info.cpp:39,48` maps SERVICE and APP_SERVICE. APP_SERVICE is in neither reviewed set; this proves only that these two type predicates do not reject it. It is **not a third connection candidate or proof of successful install/start/connect**. `module_profile.cpp:138` uses the separate `BundleType::APP_SERVICE_FWK` enum. Lines 2544-2573 copy target type, visibility, permissions and identifier allow-list; the system+preinstall condition only copies read/write permission fields.

BMS revision is `ef924ea4198befa65a088863d9812b7f872e4bbc`, attributed to exact manifest and metadata, not a local extracted-tree Git HEAD. Metadata/patch record 14 modified files. **Two copied files (`base_bundle_installer.cpp` and `services/bundlemgr/BUILD.gn`) are locally modified**: their actual bytes/line numbers and patch SHA `74dc41a5ad00c03fe2c8b4cccf7730acb00e3328bd624d212cf1c8e64074bc75` are retained, not represented as pristine upstream blobs. The other six are outside the recorded patch list.

The peer originally used the ability_runtime-only source-index, so its null BMS matches were accurate. This card independently matched these eight files against the new separate `bms-source-index.json` (10,814 entries); it did not claim to verify all entries. Index and BMS tar pins are in results; persistent originals remain at the intake. The checker verifies the public copies and patch attribution without needing that private root.

## Offline reproduction

From the repository root:

```sh
python3 benchmark/2026-10-23-service-source-chain/check.py --self-test --out benchmark/2026-10-23-service-source-chain/.private/review-new
cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test service_source_chain -- --nocapture
```

The checker tests real subprocess exits for valid GAP, changed source pin, false board-version binding and unsupported READY, under normal Python and `-O`. It uses explicit checks rather than assertions. It validates report/source evidence, not production C++ behavior. Existing output directories are refused. Raw argv/start/end/stdout/stderr/rc are retained privately; public receipts index their SHA/size. Rust uses a unique persistent card-private directory; it is not a temporary evidence mode. No raw stderr is in the landing list.
