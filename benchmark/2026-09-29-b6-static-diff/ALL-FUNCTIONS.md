# All differing functions and supplemental linker blocks

Provider rows now compare sealed R155 80c9aee0 against NEW 8d109259 (task56); the former 977fb347 provider interpretation is superseded. Each row has a bounded static recommendation. `restore` means restore to reproduce R155, not a proven fix. `retain-*` differences are intentional or useful changes that are not proven harmless and should not be blindly reverted. `unchanged-code` records remain in each functions.json. Raw line references and a register-erased diff accompany every changed row.

## host

| Function | State | Disposition | Evidence |
|---|---|---|---|
| `AddAppSpawnHook` | modified | harmless-layout | [evidence/host/functions/4740c56a886385fc.diff](evidence/host/functions/4740c56a886385fc.diff) |
| `AddProcessMgrHook` | modified | harmless-layout | [evidence/host/functions/0d9e111c7f7d74bf.diff](evidence/host/functions/0d9e111c7f7d74bf.diff) |
| `AddServerStageHook` | modified | harmless-layout | [evidence/host/functions/e8a5088e8bfc9dc4.diff](evidence/host/functions/e8a5088e8bfc9dc4.diff) |
| `AddSpawnedProcess` | modified | harmless-layout | [evidence/host/functions/6531c8a48654548a.diff](evidence/host/functions/6531c8a48654548a.diff) |
| `AppSpawnClearEnv` | modified | harmless | [evidence/host/functions/64dd717e78a1b172.diff](evidence/host/functions/64dd717e78a1b172.diff) |
| `AppSpawnColdRun` | modified | retain-diagnostics | [evidence/host/functions/216483c7b98919f2.diff](evidence/host/functions/216483c7b98919f2.diff) |
| `AppSpawnColdStartApp` | modified | harmless-diagnostic | [evidence/host/functions/38f1213a2506ad6c.diff](evidence/host/functions/38f1213a2506ad6c.diff) |
| `AppSpawnCreateContent` | modified | harmless-diagnostic | [evidence/host/functions/4745ef850ac35369.diff](evidence/host/functions/4745ef850ac35369.diff) |
| `AppSpawnDump` | modified | restore | [evidence/host/functions/ee0109da9b6a51c2.diff](evidence/host/functions/ee0109da9b6a51c2.diff) |
| `AppSpawnHookExecute` | modified | harmless-layout | [evidence/host/functions/0c496f0ce3e49377.diff](evidence/host/functions/0c496f0ce3e49377.diff) |
| `AppSpawnRun` | modified | harmless-diagnostic | [evidence/host/functions/85cd0394eb3f8288.diff](evidence/host/functions/85cd0394eb3f8288.diff) |
| `AppSpawningCtxTraversal` | modified | harmless-layout | [evidence/host/functions/e4ed624e5f37330a.diff](evidence/host/functions/e4ed624e5f37330a.diff) |
| `CreateAppSpawnMgr` | modified | harmless-layout | [evidence/host/functions/33af5f93a337e592.diff](evidence/host/functions/33af5f93a337e592.diff) |
| `DeleteAppSpawnMgr` | modified | harmless-layout | [evidence/host/functions/89223f08c6cfa453.diff](evidence/host/functions/89223f08c6cfa453.diff) |
| `GetAppSpawnHookMgr` | modified | harmless-layout | [evidence/host/functions/da87379ff95f2512.diff](evidence/host/functions/da87379ff95f2512.diff) |
| `HandleRecvMessage` | modified | retain-hardening | [evidence/host/functions/fb357f014a24ef2c.diff](evidence/host/functions/fb357f014a24ef2c.diff) |
| `InitCommonEnv` | modified | harmless-layout | [evidence/host/functions/b6763c58b31c8aba.diff](evidence/host/functions/b6763c58b31c8aba.diff) |
| `InstallPluginHostServices` | modified | restore | [evidence/host/functions/db22d3adbf8515e5.diff](evidence/host/functions/db22d3adbf8515e5.diff) |
| `IsAllZeros` | removed | retain-hardening | [evidence/host/functions/1aa79c4f3f37bdaa.diff](evidence/host/functions/1aa79c4f3f37bdaa.diff) |
| `NotifyResToParent#2` | modified | harmless-diagnostic | [evidence/host/functions/2e5b5507b3c03058.diff](evidence/host/functions/2e5b5507b3c03058.diff) |
| `OnReceiveRequest` | modified | harmless-diagnostic | [evidence/host/functions/9c92b938ad1f5da7.diff](evidence/host/functions/9c92b938ad1f5da7.diff) |
| `OpenVerifiedFileHex` | added | retain-hardening | [evidence/host/functions/2af1956621866e45.diff](evidence/host/functions/2af1956621866e45.diff) |
| `ProcessAppSpawnDumpMsg` | modified | harmless-layout | [evidence/host/functions/d1b9a9a58cbfb43b.diff](evidence/host/functions/d1b9a9a58cbfb43b.diff) |
| `ProcessChildResponse` | modified | harmless-diagnostic | [evidence/host/functions/1e76b4749ad917a4.diff](evidence/host/functions/1e76b4749ad917a4.diff) |
| `ProcessMgrHookExecute` | modified | harmless-layout | [evidence/host/functions/72941c37b8bf620c.diff](evidence/host/functions/72941c37b8bf620c.diff) |
| `ProcessSignal` | modified | harmless-diagnostic | [evidence/host/functions/7c5c6f658bffb68f.diff](evidence/host/functions/7c5c6f658bffb68f.diff) |
| `ProcessSpawnReqMsg` | modified | retain-diagnostics | [evidence/host/functions/b24c0ccfdd75e68d.diff](evidence/host/functions/b24c0ccfdd75e68d.diff) |
| `ProcessTerminationStatusMsg` | modified | harmless-layout | [evidence/host/functions/ab268acfbbe712a4.diff](evidence/host/functions/ab268acfbbe712a4.diff) |
| `ServerStageHookExecute` | modified | harmless-layout | [evidence/host/functions/159a33890eb99e24.diff](evidence/host/functions/159a33890eb99e24.diff) |
| `StartSpawnService` | modified | harmless-diagnostic | [evidence/host/functions/b230debf7460d93c.diff](evidence/host/functions/b230debf7460d93c.diff) |
| `TerminateSpawnedProcess` | modified | harmless-layout | [evidence/host/functions/e3ba462b9ed77107.diff](evidence/host/functions/e3ba462b9ed77107.diff) |
| `TraversalSpawnedProcess` | modified | harmless-layout | [evidence/host/functions/aa10db5bfb5c50fc.diff](evidence/host/functions/aa10db5bfb5c50fc.diff) |
| `VerifyBuildId` | modified | retain-hardening | [evidence/host/functions/a8aec7a83b11727c.diff](evidence/host/functions/a8aec7a83b11727c.diff) |
| `WLEI_CloseVerifiedFile` | added | retain-hardening | [evidence/host/functions/0eadf1ac94205822.diff](evidence/host/functions/0eadf1ac94205822.diff) |
| `WLEI_OpenVerifiedFileHex` | added | retain-hardening | [evidence/host/functions/919966f6ad549db5.diff](evidence/host/functions/919966f6ad549db5.diff) |
| `WLEI_OpenVerifiedSystemFileHex` | added | retain-hardening | [evidence/host/functions/792e1cdd298a2381.diff](evidence/host/functions/792e1cdd298a2381.diff) |
| `WLEI_VerifyFileHex` | modified | retain-hardening | [evidence/host/functions/9d3ec6012099fd07.diff](evidence/host/functions/9d3ec6012099fd07.diff) |
| `WLEI_VerifyLoadedSymbolHex` | modified | retain-hardening | [evidence/host/functions/b2c895d136033ce3.diff](evidence/host/functions/b2c895d136033ce3.diff) |
| `WLSha256Final` | modified | harmless-constant-relocation | [evidence/host/functions/d28e042158734192.diff](evidence/host/functions/d28e042158734192.diff) |
| `WLSha256Init` | modified | harmless-constant-relocation | [evidence/host/functions/fa25d3ab361d4b84.diff](evidence/host/functions/fa25d3ab361d4b84.diff) |
| `WaitChildTimeout` | modified | harmless-diagnostic | [evidence/host/functions/b922e493c8603bdb.diff](evidence/host/functions/b922e493c8603bdb.diff) |
| `WlResolveHostStdio` | added | restore | [evidence/host/functions/ea23f80c08521c25.diff](evidence/host/functions/ea23f80c08521c25.diff) |
| `_ZN12_GLOBAL__N_126ResolveCurrentThreadRegionEPvPK20WltgProcessBindingV1PK18WltgThreadTicketV1P15WltgOwnedRegion` | modified | harmless-constant-relocation | [evidence/host/functions/34114dada1def864.diff](evidence/host/functions/34114dada1def864.diff) |
| `_ZN9appspawnx36WestLakeNativeCompatGetAuditSnapshotEP19WlncAuditSnapshotV1` | modified | harmless-constant-relocation | [evidence/host/functions/9fce1f02160bce32.diff](evidence/host/functions/9fce1f02160bce32.diff) |
| `_ZN9appspawnx37WestLakeNativeCompatPrepareMainThreadEPK21WlncProcessIdentityV1` | modified | harmless-constant-relocation | [evidence/host/functions/e67b7aa0eafb1f11.diff](evidence/host/functions/e67b7aa0eafb1f11.diff) |
| `_ZN9appspawnx40WestLakeNativeCompatPrepareParentRuntimeEPK20WlncParentIdentityV1` | modified | harmless-constant-relocation | [evidence/host/functions/58da921e6413e4f5.diff](evidence/host/functions/58da921e6413e4f5.diff) |
| `__emutls_unregister_key` | modified | restore-hardening | [evidence/host/functions/c6a96413af3f8e89.diff](evidence/host/functions/c6a96413af3f8e89.diff) |
| `block:.plt` | modified | harmless-layout | [evidence/host/functions/80a03770c27acce1.diff](evidence/host/functions/80a03770c27acce1.diff) |
| `block:DecodeUid@plt` | modified | harmless-layout | [evidence/host/functions/cc056114721aaf55.diff](evidence/host/functions/cc056114721aaf55.diff) |
| `block:FreeCfgFiles@plt` | modified | harmless-layout | [evidence/host/functions/41fbea7e38bcaa23.diff](evidence/host/functions/41fbea7e38bcaa23.diff) |
| `block:GetCfgFiles@plt` | modified | harmless-layout | [evidence/host/functions/d2d770f9a7312116.diff](evidence/host/functions/d2d770f9a7312116.diff) |
| `block:GetControlSocket@plt` | modified | harmless-layout | [evidence/host/functions/fe4bd74d02956f47.diff](evidence/host/functions/fe4bd74d02956f47.diff) |
| `block:GetOneCfgFile@plt` | modified | harmless-layout | [evidence/host/functions/54786c250b08dc10.diff](evidence/host/functions/54786c250b08dc10.diff) |
| `block:GetParameter@plt` | modified | harmless-layout | [evidence/host/functions/fe6f89f0ca3e66be.diff](evidence/host/functions/fe6f89f0ca3e66be.diff) |
| `block:HiLogPrint@plt` | modified | harmless-layout | [evidence/host/functions/ca85586b6af254a3.diff](evidence/host/functions/ca85586b6af254a3.diff) |
| `block:HookMgrAddEx@plt` | modified | harmless-layout | [evidence/host/functions/329e2646fb08bef5.diff](evidence/host/functions/329e2646fb08bef5.diff) |
| `block:HookMgrCreate@plt` | modified | harmless-layout | [evidence/host/functions/0aa4a0b9b8bdecc7.diff](evidence/host/functions/0aa4a0b9b8bdecc7.diff) |
| `block:HookMgrDestroy@plt` | modified | harmless-layout | [evidence/host/functions/872a82030b14f303.diff](evidence/host/functions/872a82030b14f303.diff) |
| `block:HookMgrExecute@plt` | modified | harmless-layout | [evidence/host/functions/8562ec7fb78280c0.diff](evidence/host/functions/8562ec7fb78280c0.diff) |
| `block:LE_AcceptStreamClient@plt` | modified | harmless-layout | [evidence/host/functions/53c79e7106ed7e7b.diff](evidence/host/functions/53c79e7106ed7e7b.diff) |
| `block:LE_AddSignal@plt` | modified | harmless-layout | [evidence/host/functions/c9f901ecf2ae8765.diff](evidence/host/functions/c9f901ecf2ae8765.diff) |
| `block:LE_CloseLoop@plt` | modified | harmless-layout | [evidence/host/functions/9d1517114f78d141.diff](evidence/host/functions/9d1517114f78d141.diff) |
| `block:LE_CloseSignalTask@plt` | modified | harmless-layout | [evidence/host/functions/8be9df6be92f736f.diff](evidence/host/functions/8be9df6be92f736f.diff) |
| `block:LE_CloseStreamTask@plt` | modified | harmless-layout | [evidence/host/functions/fd539f352c5213fa.diff](evidence/host/functions/fd539f352c5213fa.diff) |
| `block:LE_CloseTask@plt` | modified | harmless-layout | [evidence/host/functions/84bc5568c2ef529d.diff](evidence/host/functions/84bc5568c2ef529d.diff) |
| `block:LE_CreateBuffer@plt` | modified | harmless-layout | [evidence/host/functions/c821925d849dc344.diff](evidence/host/functions/c821925d849dc344.diff) |
| `block:LE_CreateSignalTask@plt` | modified | harmless-layout | [evidence/host/functions/597aa5ed247c0902.diff](evidence/host/functions/597aa5ed247c0902.diff) |
| `block:LE_CreateStreamServer@plt` | modified | harmless-layout | [evidence/host/functions/3fa0523dabec0eed.diff](evidence/host/functions/3fa0523dabec0eed.diff) |
| `block:LE_CreateTimer@plt` | modified | harmless-layout | [evidence/host/functions/8575ca8b9daa9814.diff](evidence/host/functions/8575ca8b9daa9814.diff) |
| `block:LE_FreeBuffer@plt` | modified | harmless-layout | [evidence/host/functions/8b4c9672e53d97f1.diff](evidence/host/functions/8b4c9672e53d97f1.diff) |
| `block:LE_GetBufferInfo@plt` | modified | harmless-layout | [evidence/host/functions/04260a4b5597bb45.diff](evidence/host/functions/04260a4b5597bb45.diff) |
| `block:LE_GetDefaultLoop@plt` | modified | harmless-layout | [evidence/host/functions/f46af0c73a68051c.diff](evidence/host/functions/f46af0c73a68051c.diff) |
| `block:LE_GetSendResult@plt` | modified | harmless-layout | [evidence/host/functions/bf21bc010a22f595.diff](evidence/host/functions/bf21bc010a22f595.diff) |
| `block:LE_GetSocketFd@plt` | modified | harmless-layout | [evidence/host/functions/c94f832ada52f6e8.diff](evidence/host/functions/c94f832ada52f6e8.diff) |
| `block:LE_GetUserData@plt` | modified | harmless-layout | [evidence/host/functions/27e7240b9e83e22f.diff](evidence/host/functions/27e7240b9e83e22f.diff) |
| `block:LE_RemoveWatcher@plt` | modified | harmless-layout | [evidence/host/functions/c92a10d4252d14d8.diff](evidence/host/functions/c92a10d4252d14d8.diff) |
| `block:LE_RunLoop@plt` | modified | harmless-layout | [evidence/host/functions/6aeede42edfb778b.diff](evidence/host/functions/6aeede42edfb778b.diff) |
| `block:LE_Send@plt` | modified | harmless-layout | [evidence/host/functions/a29665f5ec3ba471.diff](evidence/host/functions/a29665f5ec3ba471.diff) |
| `block:LE_StartTimer@plt` | modified | harmless-layout | [evidence/host/functions/c93a508c3221a3b0.diff](evidence/host/functions/c93a508c3221a3b0.diff) |
| `block:LE_StartWatcher@plt` | modified | harmless-layout | [evidence/host/functions/c37a6b773213fbdf.diff](evidence/host/functions/c37a6b773213fbdf.diff) |
| `block:LE_StopLoop@plt` | modified | harmless-layout | [evidence/host/functions/bf30d69a1bf72b28.diff](evidence/host/functions/bf30d69a1bf72b28.diff) |
| `block:LE_StopTimer@plt` | modified | harmless-layout | [evidence/host/functions/e699385f5fe51b30.diff](evidence/host/functions/e699385f5fe51b30.diff) |
| `block:ModuleMgrCreate@plt` | modified | harmless-layout | [evidence/host/functions/ebc364e21626eb91.diff](evidence/host/functions/ebc364e21626eb91.diff) |
| `block:ModuleMgrDestroy@plt` | modified | harmless-layout | [evidence/host/functions/60f28ad05d102876.diff](evidence/host/functions/60f28ad05d102876.diff) |
| `block:ModuleMgrInstall@plt` | modified | harmless-layout | [evidence/host/functions/fc01f63f7113d20f.diff](evidence/host/functions/fc01f63f7113d20f.diff) |
| `block:ModuleMgrScan@plt` | modified | harmless-layout | [evidence/host/functions/b91e7d56fb6d1c90.diff](evidence/host/functions/b91e7d56fb6d1c90.diff) |
| `block:OH_ListAddTail@plt` | modified | harmless-layout | [evidence/host/functions/a98bd9d15a680698.diff](evidence/host/functions/a98bd9d15a680698.diff) |
| `block:OH_ListAddWithOrder@plt` | modified | harmless-layout | [evidence/host/functions/7c4e7eae42eb6f7c.diff](evidence/host/functions/7c4e7eae42eb6f7c.diff) |
| `block:OH_ListFind@plt` | modified | harmless-layout | [evidence/host/functions/dc7f1a4f01b9d4f5.diff](evidence/host/functions/dc7f1a4f01b9d4f5.diff) |
| `block:OH_ListInit@plt` | modified | harmless-layout | [evidence/host/functions/d223721017473e63.diff](evidence/host/functions/d223721017473e63.diff) |
| `block:OH_ListRemove@plt` | modified | harmless-layout | [evidence/host/functions/517eef0e8f9eae77.diff](evidence/host/functions/517eef0e8f9eae77.diff) |
| `block:OH_ListRemoveAll@plt` | modified | harmless-layout | [evidence/host/functions/3abe5c966071cb6c.diff](evidence/host/functions/3abe5c966071cb6c.diff) |
| `block:OH_ListTraversal@plt` | modified | harmless-layout | [evidence/host/functions/7f8374ffe7ef8098.diff](evidence/host/functions/7f8374ffe7ef8098.diff) |
| `block:SetParameter@plt` | modified | harmless-layout | [evidence/host/functions/1bcf79e113ddeb36.diff](evidence/host/functions/1bcf79e113ddeb36.diff) |
| `block:WLTG_AfterForkChildReset@plt` | modified | harmless-layout | [evidence/host/functions/4200de254a112b9d.diff](evidence/host/functions/4200de254a112b9d.diff) |
| `block:WLTG_CancelThreadTicket@plt` | modified | harmless-layout | [evidence/host/functions/fa2a1d9261118b9f.diff](evidence/host/functions/fa2a1d9261118b9f.diff) |
| `block:WLTG_GetProcessSnapshot@plt` | modified | harmless-layout | [evidence/host/functions/be5e9ae6b867ac5e.diff](evidence/host/functions/be5e9ae6b867ac5e.diff) |
| `block:WLTG_IssueThreadTicket@plt` | modified | harmless-layout | [evidence/host/functions/b234d94d483b6173.diff](evidence/host/functions/b234d94d483b6173.diff) |
| `block:WLTG_PrepareCurrentThread@plt` | modified | harmless-layout | [evidence/host/functions/044565fa22ecefdf.diff](evidence/host/functions/044565fa22ecefdf.diff) |
| `block:WLTG_ProcessArm@plt` | modified | harmless-layout | [evidence/host/functions/3196c2b70bd2c7dd.diff](evidence/host/functions/3196c2b70bd2c7dd.diff) |
| `block:WLTG_RetireCurrentThread@plt` | modified | harmless-layout | [evidence/host/functions/61e2157d9b06587a.diff](evidence/host/functions/61e2157d9b06587a.diff) |
| `block:WLTG_Revoke@plt` | modified | harmless-layout | [evidence/host/functions/dbbb43d2c8948c92.diff](evidence/host/functions/dbbb43d2c8948c92.diff) |
| `block:WLTG_VerifyCurrentThreadReady@plt` | modified | harmless-layout | [evidence/host/functions/cd79c4bf1818a5de.diff](evidence/host/functions/cd79c4bf1818a5de.diff) |
| `block:_Unwind_Resume@plt` | modified | harmless-layout | [evidence/host/functions/e28eb13bb1b253ab.diff](evidence/host/functions/e28eb13bb1b253ab.diff) |
| `block:_ZN4OHOS6system16GetBoolParameterERKNSt3__h12basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEEb@plt` | modified | harmless-layout | [evidence/host/functions/c3cd5f16d3f1d4ed.diff](evidence/host/functions/c3cd5f16d3f1d4ed.diff) |
| `block:_ZNSt11logic_errorC2EPKc@plt` | modified | harmless-layout | [evidence/host/functions/bd40e5078d4311d6.diff](evidence/host/functions/bd40e5078d4311d6.diff) |
| `block:_ZNSt20bad_array_new_lengthC1Ev@plt` | modified | harmless-layout | [evidence/host/functions/310cbf9366df9e7b.diff](evidence/host/functions/310cbf9366df9e7b.diff) |
| `block:_ZNSt3__h12__next_primeEm@plt` | modified | harmless-layout | [evidence/host/functions/0238e522debf24af.diff](evidence/host/functions/0238e522debf24af.diff) |
| `block:_ZNSt3__h5mutex4lockEv@plt` | modified | harmless-layout | [evidence/host/functions/94dbecb5d1294d7c.diff](evidence/host/functions/94dbecb5d1294d7c.diff) |
| `block:_ZNSt3__h5mutex6unlockEv@plt` | modified | harmless-layout | [evidence/host/functions/4f9d700c4ab9941a.diff](evidence/host/functions/4f9d700c4ab9941a.diff) |
| `block:_ZNSt3__h5mutexD1Ev@plt` | modified | harmless-layout | [evidence/host/functions/70b203436c8699bf.diff](evidence/host/functions/70b203436c8699bf.diff) |
| `block:_ZSt9terminatev@plt` | modified | harmless-layout | [evidence/host/functions/d9d2e770e5e35522.diff](evidence/host/functions/d9d2e770e5e35522.diff) |
| `block:_ZdlPv@plt` | modified | harmless-layout | [evidence/host/functions/734446161d85a91d.diff](evidence/host/functions/734446161d85a91d.diff) |
| `block:_Znwm@plt` | modified | harmless-layout | [evidence/host/functions/c4f43e9ac3dabb97.diff](evidence/host/functions/c4f43e9ac3dabb97.diff) |
| `block:__at_fini@plt` | modified | harmless-layout | [evidence/host/functions/3b32f4e6ffef234b.diff](evidence/host/functions/3b32f4e6ffef234b.diff) |
| `block:__cxa_allocate_exception@plt` | modified | harmless-layout | [evidence/host/functions/b18883a0750e3c45.diff](evidence/host/functions/b18883a0750e3c45.diff) |
| `block:__cxa_atexit@plt` | modified | harmless-layout | [evidence/host/functions/261d144aca0fbbb8.diff](evidence/host/functions/261d144aca0fbbb8.diff) |
| `block:__cxa_begin_catch@plt` | modified | harmless-layout | [evidence/host/functions/4ad753a8682ce066.diff](evidence/host/functions/4ad753a8682ce066.diff) |
| `block:__cxa_finalize@plt` | modified | harmless-layout | [evidence/host/functions/5da62f5c9fd03af8.diff](evidence/host/functions/5da62f5c9fd03af8.diff) |
| `block:__cxa_free_exception@plt` | modified | harmless-layout | [evidence/host/functions/987966d587853e3c.diff](evidence/host/functions/987966d587853e3c.diff) |
| `block:__cxa_guard_abort@plt` | modified | harmless-layout | [evidence/host/functions/45eefd542fb922ac.diff](evidence/host/functions/45eefd542fb922ac.diff) |
| `block:__cxa_guard_acquire@plt` | modified | harmless-layout | [evidence/host/functions/5ff71a6e9c44548a.diff](evidence/host/functions/5ff71a6e9c44548a.diff) |
| `block:__cxa_guard_release@plt` | modified | harmless-layout | [evidence/host/functions/5eec6c15a1122554.diff](evidence/host/functions/5eec6c15a1122554.diff) |
| `block:__cxa_throw@plt` | modified | harmless-layout | [evidence/host/functions/7939b0ba6f2fb15d.diff](evidence/host/functions/7939b0ba6f2fb15d.diff) |
| `block:__deregister_frame_info@plt` | modified | harmless-layout | [evidence/host/functions/8dc5523a441b6224.diff](evidence/host/functions/8dc5523a441b6224.diff) |
| `block:__errno_location@plt` | modified | harmless-layout | [evidence/host/functions/927836485dd999ab.diff](evidence/host/functions/927836485dd999ab.diff) |
| `block:__libc_start_main@plt` | modified | harmless-layout | [evidence/host/functions/46db1100ebcfbf28.diff](evidence/host/functions/46db1100ebcfbf28.diff) |
| `block:__register_frame_info@plt` | modified | harmless-layout | [evidence/host/functions/133a1f168b60a5c2.diff](evidence/host/functions/133a1f168b60a5c2.diff) |
| `block:_exit@plt` | modified | harmless-layout | [evidence/host/functions/6c1b173043efcd10.diff](evidence/host/functions/6c1b173043efcd10.diff) |
| `block:atoi@plt` | modified | harmless-layout | [evidence/host/functions/c1911ef8e399adee.diff](evidence/host/functions/c1911ef8e399adee.diff) |
| `block:bcmp@plt` | modified | harmless-layout | [evidence/host/functions/581b279a8b2970c1.diff](evidence/host/functions/581b279a8b2970c1.diff) |
| `block:cJSON_AddNumberToObject@plt` | modified | harmless-layout | [evidence/host/functions/c6dec6bfde41aa80.diff](evidence/host/functions/c6dec6bfde41aa80.diff) |
| `block:cJSON_AddStringToObject@plt` | modified | harmless-layout | [evidence/host/functions/35aad70a63d47ea8.diff](evidence/host/functions/35aad70a63d47ea8.diff) |
| `block:cJSON_CreateObject@plt` | modified | harmless-layout | [evidence/host/functions/4fa6614a3fc9d506.diff](evidence/host/functions/4fa6614a3fc9d506.diff) |
| `block:cJSON_Delete@plt` | modified | harmless-layout | [evidence/host/functions/b4bc2a86a4b0203e.diff](evidence/host/functions/b4bc2a86a4b0203e.diff) |
| `block:cJSON_GetObjectItem@plt` | modified | harmless-layout | [evidence/host/functions/f2f653ce686ebce9.diff](evidence/host/functions/f2f653ce686ebce9.diff) |
| `block:cJSON_GetObjectItemCaseSensitive@plt` | modified | harmless-layout | [evidence/host/functions/5181508685c01eaf.diff](evidence/host/functions/5181508685c01eaf.diff) |
| `block:cJSON_GetStringValue@plt` | modified | harmless-layout | [evidence/host/functions/6b3527aa155f8164.diff](evidence/host/functions/6b3527aa155f8164.diff) |
| `block:cJSON_IsArray@plt` | modified | harmless-layout | [evidence/host/functions/8418285edbfdc5eb.diff](evidence/host/functions/8418285edbfdc5eb.diff) |
| `block:cJSON_IsNumber@plt` | modified | harmless-layout | [evidence/host/functions/28e6e5b18c8a8e46.diff](evidence/host/functions/28e6e5b18c8a8e46.diff) |
| `block:cJSON_IsObject@plt` | modified | harmless-layout | [evidence/host/functions/ff2392c259d5731e.diff](evidence/host/functions/ff2392c259d5731e.diff) |
| `block:cJSON_IsString@plt` | modified | harmless-layout | [evidence/host/functions/d00adb028f1fcf96.diff](evidence/host/functions/d00adb028f1fcf96.diff) |
| `block:cJSON_Parse@plt` | modified | harmless-layout | [evidence/host/functions/eefcd8d833662fcc.diff](evidence/host/functions/eefcd8d833662fcc.diff) |
| `block:cJSON_Print@plt` | modified | harmless-layout | [evidence/host/functions/50d27e090870c4cf.diff](evidence/host/functions/50d27e090870c4cf.diff) |
| `block:calloc@plt` | modified | harmless-layout | [evidence/host/functions/a9e8f11f43e2676f.diff](evidence/host/functions/a9e8f11f43e2676f.diff) |
| `block:clock_gettime@plt` | modified | harmless-layout | [evidence/host/functions/97f23e6c27919fa1.diff](evidence/host/functions/97f23e6c27919fa1.diff) |
| `block:clone@plt` | modified | harmless-layout | [evidence/host/functions/1f8facfbb9895890.diff](evidence/host/functions/1f8facfbb9895890.diff) |
| `block:close@plt` | modified | harmless-layout | [evidence/host/functions/7c043866062c01ed.diff](evidence/host/functions/7c043866062c01ed.diff) |
| `block:closedir@plt` | modified | harmless-layout | [evidence/host/functions/a9f2c379d3297909.diff](evidence/host/functions/a9f2c379d3297909.diff) |
| `block:dl_iterate_phdr@plt` | modified | harmless-layout | [evidence/host/functions/79cd94b1c8eba22d.diff](evidence/host/functions/79cd94b1c8eba22d.diff) |
| `block:dladdr@plt` | modified | harmless-layout | [evidence/host/functions/d01a977040932b95.diff](evidence/host/functions/d01a977040932b95.diff) |
| `block:dlclose@plt` | modified | harmless-layout | [evidence/host/functions/8741a3a1471dbaba.diff](evidence/host/functions/8741a3a1471dbaba.diff) |
| `block:dlerror@plt` | modified | harmless-layout | [evidence/host/functions/b7a5ccb01422a4be.diff](evidence/host/functions/b7a5ccb01422a4be.diff) |
| `block:dlns_create2@plt` | modified | harmless-layout | [evidence/host/functions/b476cf2ace2bf3ec.diff](evidence/host/functions/b476cf2ace2bf3ec.diff) |
| `block:dlns_inherit@plt` | modified | harmless-layout | [evidence/host/functions/e9086a7a40fd8e3a.diff](evidence/host/functions/e9086a7a40fd8e3a.diff) |
| `block:dlns_init@plt` | modified | harmless-layout | [evidence/host/functions/05bc1bf8e05f8d4d.diff](evidence/host/functions/05bc1bf8e05f8d4d.diff) |
| `block:dlns_set_namespace_allowed_libs@plt` | modified | harmless-layout | [evidence/host/functions/feb564f0ec225a02.diff](evidence/host/functions/feb564f0ec225a02.diff) |
| `block:dlns_set_namespace_permitted_paths@plt` | modified | harmless-layout | [evidence/host/functions/bcb677c90d92eaec.diff](evidence/host/functions/bcb677c90d92eaec.diff) |
| `block:dlns_set_namespace_separated@plt` | modified | harmless-layout | [evidence/host/functions/d1ca33de0c32be45.diff](evidence/host/functions/d1ca33de0c32be45.diff) |
| `block:dlopen@plt` | modified | harmless-layout | [evidence/host/functions/3ff36795fedc06aa.diff](evidence/host/functions/3ff36795fedc06aa.diff) |
| `block:dlopen_ns@plt` | modified | harmless-layout | [evidence/host/functions/f34f70a3849561b8.diff](evidence/host/functions/f34f70a3849561b8.diff) |
| `block:dlsym@plt` | modified | harmless-layout | [evidence/host/functions/74dc8db09c3e3dbd.diff](evidence/host/functions/74dc8db09c3e3dbd.diff) |
| `block:execv@plt` | modified | harmless-layout | [evidence/host/functions/a827b9e8d5f70bad.diff](evidence/host/functions/a827b9e8d5f70bad.diff) |
| `block:fallocate@plt` | modified | harmless-layout | [evidence/host/functions/346b3531b6b4bce6.diff](evidence/host/functions/346b3531b6b4bce6.diff) |
| `block:fclose@plt` | modified | harmless-layout | [evidence/host/functions/992fe58255b0a1fe.diff](evidence/host/functions/992fe58255b0a1fe.diff) |
| `block:fcntl@plt` | modified | harmless-layout | [evidence/host/functions/1759425b8f2924f0.diff](evidence/host/functions/1759425b8f2924f0.diff) |
| `block:fdsan_get_error_level@plt` | modified | harmless-layout | [evidence/host/functions/c6f230ecacc39433.diff](evidence/host/functions/c6f230ecacc39433.diff) |
| `block:fdsan_set_error_level@plt` | modified | harmless-layout | [evidence/host/functions/fb1180ea04b6367a.diff](evidence/host/functions/fb1180ea04b6367a.diff) |
| `block:fflush@plt` | removed | restore-with-caller | [evidence/host/functions/df06fb6c24523b8b.diff](evidence/host/functions/df06fb6c24523b8b.diff) |
| `block:ffrt_child_init@plt` | modified | harmless-layout | [evidence/host/functions/dcb836fb1df6af17.diff](evidence/host/functions/dcb836fb1df6af17.diff) |
| `block:fopen@plt` | modified | harmless-layout | [evidence/host/functions/f39d29002639dcfa.diff](evidence/host/functions/f39d29002639dcfa.diff) |
| `block:fork@plt` | modified | harmless-layout | [evidence/host/functions/8f343b1e520afedd.diff](evidence/host/functions/8f343b1e520afedd.diff) |
| `block:fread@plt` | modified | harmless-layout | [evidence/host/functions/6c548bd48eb5ad9a.diff](evidence/host/functions/6c548bd48eb5ad9a.diff) |
| `block:free@plt` | modified | harmless-layout | [evidence/host/functions/ed9127767958e20c.diff](evidence/host/functions/ed9127767958e20c.diff) |
| `block:fstat@plt` | modified | harmless-layout | [evidence/host/functions/1c048c0d7c4a2c0b.diff](evidence/host/functions/1c048c0d7c4a2c0b.diff) |
| `block:getauxval@plt` | modified | harmless-layout | [evidence/host/functions/527e8835a5d75d98.diff](evidence/host/functions/527e8835a5d75d98.diff) |
| `block:getenv@plt` | modified | harmless-layout | [evidence/host/functions/7c75bf9dbb26dfbb.diff](evidence/host/functions/7c75bf9dbb26dfbb.diff) |
| `block:getgid@plt` | modified | harmless-layout | [evidence/host/functions/6473f54805c1228e.diff](evidence/host/functions/6473f54805c1228e.diff) |
| `block:getpid@plt` | modified | harmless-layout | [evidence/host/functions/7b44857ed6d3dc22.diff](evidence/host/functions/7b44857ed6d3dc22.diff) |
| `block:getrandom@plt` | modified | harmless-layout | [evidence/host/functions/2a8079bcaf687820.diff](evidence/host/functions/2a8079bcaf687820.diff) |
| `block:getsockopt@plt` | modified | harmless-layout | [evidence/host/functions/3d0ecdb62b33c820.diff](evidence/host/functions/3d0ecdb62b33c820.diff) |
| `block:gettid@plt` | modified | harmless-layout | [evidence/host/functions/15cccca93e22195d.diff](evidence/host/functions/15cccca93e22195d.diff) |
| `block:getuid@plt` | modified | harmless-layout | [evidence/host/functions/e91f2d2ed49a0d15.diff](evidence/host/functions/e91f2d2ed49a0d15.diff) |
| `block:kill@plt` | modified | harmless-layout | [evidence/host/functions/74de120e80a0c7b6.diff](evidence/host/functions/74de120e80a0c7b6.diff) |
| `block:malloc@plt` | modified | harmless-layout | [evidence/host/functions/329fe710d164f551.diff](evidence/host/functions/329fe710d164f551.diff) |
| `block:memcpy@plt` | modified | harmless-layout | [evidence/host/functions/100657bf3a1dd88c.diff](evidence/host/functions/100657bf3a1dd88c.diff) |
| `block:memcpy_s@plt` | modified | harmless-layout | [evidence/host/functions/e79102139f17c081.diff](evidence/host/functions/e79102139f17c081.diff) |
| `block:memmove@plt` | modified | harmless-layout | [evidence/host/functions/2c09048d2b79e68b.diff](evidence/host/functions/2c09048d2b79e68b.diff) |
| `block:memset@plt` | modified | harmless-layout | [evidence/host/functions/8be105e928130577.diff](evidence/host/functions/8be105e928130577.diff) |
| `block:memset_s@plt` | modified | harmless-layout | [evidence/host/functions/796297c423a4af1b.diff](evidence/host/functions/796297c423a4af1b.diff) |
| `block:mkdir@plt` | modified | harmless-layout | [evidence/host/functions/295eb427a8106a6c.diff](evidence/host/functions/295eb427a8106a6c.diff) |
| `block:mmap@plt` | modified | harmless-layout | [evidence/host/functions/8fe73f44d81cf51e.diff](evidence/host/functions/8fe73f44d81cf51e.diff) |
| `block:mprotect@plt` | modified | harmless-layout | [evidence/host/functions/438562f738c873cd.diff](evidence/host/functions/438562f738c873cd.diff) |
| `block:munmap@plt` | modified | harmless-layout | [evidence/host/functions/cdad1cd725840fad.diff](evidence/host/functions/cdad1cd725840fad.diff) |
| `block:open@plt` | modified | harmless-layout | [evidence/host/functions/2464f032fca0d429.diff](evidence/host/functions/2464f032fca0d429.diff) |
| `block:opendir@plt` | modified | harmless-layout | [evidence/host/functions/90d45b5a0c36e53a.diff](evidence/host/functions/90d45b5a0c36e53a.diff) |
| `block:pipe@plt` | modified | harmless-layout | [evidence/host/functions/dd49168ba1c1598f.diff](evidence/host/functions/dd49168ba1c1598f.diff) |
| `block:pread@plt` | modified | harmless-layout | [evidence/host/functions/5723c6060986ee9c.diff](evidence/host/functions/5723c6060986ee9c.diff) |
| `block:pthread_attr_destroy@plt` | modified | harmless-layout | [evidence/host/functions/161da6bc6fc0e25a.diff](evidence/host/functions/161da6bc6fc0e25a.diff) |
| `block:pthread_attr_getstack@plt` | modified | harmless-layout | [evidence/host/functions/376e0207da83a676.diff](evidence/host/functions/376e0207da83a676.diff) |
| `block:pthread_attr_init@plt` | modified | harmless-layout | [evidence/host/functions/66abace28b4c27c7.diff](evidence/host/functions/66abace28b4c27c7.diff) |
| `block:pthread_attr_setdetachstate@plt` | modified | harmless-layout | [evidence/host/functions/54a7ed67bcb38afd.diff](evidence/host/functions/54a7ed67bcb38afd.diff) |
| `block:pthread_attr_setstacksize@plt` | modified | harmless-layout | [evidence/host/functions/8098e1c0da364262.diff](evidence/host/functions/8098e1c0da364262.diff) |
| `block:pthread_create@plt` | modified | harmless-layout | [evidence/host/functions/d76cd557a7f19616.diff](evidence/host/functions/d76cd557a7f19616.diff) |
| `block:pthread_exit@plt` | modified | harmless-layout | [evidence/host/functions/f291646c8c130016.diff](evidence/host/functions/f291646c8c130016.diff) |
| `block:pthread_getattr_np@plt` | modified | harmless-layout | [evidence/host/functions/def3d6292fcc717a.diff](evidence/host/functions/def3d6292fcc717a.diff) |
| `block:pthread_once@plt` | added | restore-with-caller | [evidence/host/functions/40852937925a1117.diff](evidence/host/functions/40852937925a1117.diff) |
| `block:pthread_self@plt` | modified | harmless-layout | [evidence/host/functions/1b56762a0b217baa.diff](evidence/host/functions/1b56762a0b217baa.diff) |
| `block:quick_exit@plt` | modified | harmless-layout | [evidence/host/functions/49e61f967cdfc428.diff](evidence/host/functions/49e61f967cdfc428.diff) |
| `block:read@plt` | modified | harmless-layout | [evidence/host/functions/e51ceecb4ff0d918.diff](evidence/host/functions/e51ceecb4ff0d918.diff) |
| `block:readdir@plt` | modified | harmless-layout | [evidence/host/functions/6de08a60471088bc.diff](evidence/host/functions/6de08a60471088bc.diff) |
| `block:readlink@plt` | modified | harmless-layout | [evidence/host/functions/bf014d9e71974216.diff](evidence/host/functions/bf014d9e71974216.diff) |
| `block:realpath@plt` | modified | harmless-layout | [evidence/host/functions/5e57d1a72adef07e.diff](evidence/host/functions/5e57d1a72adef07e.diff) |
| `block:recvmsg@plt` | modified | harmless-layout | [evidence/host/functions/1e5e6554ba8b87e9.diff](evidence/host/functions/1e5e6554ba8b87e9.diff) |
| `block:sched_setscheduler@plt` | modified | harmless-layout | [evidence/host/functions/7a7db0f6b48c22ec.diff](evidence/host/functions/7a7db0f6b48c22ec.diff) |
| `block:setenv@plt` | modified | harmless-layout | [evidence/host/functions/aff64424129be87e.diff](evidence/host/functions/aff64424129be87e.diff) |
| `block:signal@plt` | modified | harmless-layout | [evidence/host/functions/817bb38412a49c8e.diff](evidence/host/functions/817bb38412a49c8e.diff) |
| `block:snprintf@plt` | modified | harmless-layout | [evidence/host/functions/46e2fcfb713e7f7b.diff](evidence/host/functions/46e2fcfb713e7f7b.diff) |
| `block:snprintf_s@plt` | modified | harmless-layout | [evidence/host/functions/195a9dae6921dec6.diff](evidence/host/functions/195a9dae6921dec6.diff) |
| `block:sprintf_s@plt` | modified | harmless-layout | [evidence/host/functions/f05c9bf4de9ac0ac.diff](evidence/host/functions/f05c9bf4de9ac0ac.diff) |
| `block:stat@plt` | modified | harmless-layout | [evidence/host/functions/c6f31a4c9e672f8c.diff](evidence/host/functions/c6f31a4c9e672f8c.diff) |
| `block:strcat_s@plt` | modified | harmless-layout | [evidence/host/functions/fc4764f21dc0f396.diff](evidence/host/functions/fc4764f21dc0f396.diff) |
| `block:strchr@plt` | modified | harmless-layout | [evidence/host/functions/d725baceedc3df64.diff](evidence/host/functions/d725baceedc3df64.diff) |
| `block:strcmp@plt` | modified | harmless-layout | [evidence/host/functions/da20ffa12cded264.diff](evidence/host/functions/da20ffa12cded264.diff) |
| `block:strcpy_s@plt` | modified | harmless-layout | [evidence/host/functions/0189fd2992fcb06d.diff](evidence/host/functions/0189fd2992fcb06d.diff) |
| `block:strdup@plt` | modified | harmless-layout | [evidence/host/functions/8ba0243913bd7458.diff](evidence/host/functions/8ba0243913bd7458.diff) |
| `block:strlen@plt` | modified | harmless-layout | [evidence/host/functions/c83f5045be37ed80.diff](evidence/host/functions/c83f5045be37ed80.diff) |
| `block:strncmp@plt` | modified | harmless-layout | [evidence/host/functions/0e2f274f7bc1d019.diff](evidence/host/functions/0e2f274f7bc1d019.diff) |
| `block:strncpy_s@plt` | modified | harmless-layout | [evidence/host/functions/4db7b5d46cea70b9.diff](evidence/host/functions/4db7b5d46cea70b9.diff) |
| `block:strstr@plt` | modified | harmless-layout | [evidence/host/functions/499ea097f93e5a83.diff](evidence/host/functions/499ea097f93e5a83.diff) |
| `block:strtok_r@plt` | modified | harmless-layout | [evidence/host/functions/6404fca95704b8d0.diff](evidence/host/functions/6404fca95704b8d0.diff) |
| `block:syscall@plt` | modified | harmless-layout | [evidence/host/functions/bd1b068efc6392f8.diff](evidence/host/functions/bd1b068efc6392f8.diff) |
| `block:sysconf@plt` | modified | harmless-layout | [evidence/host/functions/888951b10a3a3b36.diff](evidence/host/functions/888951b10a3a3b36.diff) |
| `block:uname@plt` | modified | harmless-layout | [evidence/host/functions/9d46b259c8b23caa.diff](evidence/host/functions/9d46b259c8b23caa.diff) |
| `block:unlink@plt` | modified | harmless-layout | [evidence/host/functions/8ee5cdab7ad8fae8.diff](evidence/host/functions/8ee5cdab7ad8fae8.diff) |
| `block:unsetenv@plt` | modified | harmless-layout | [evidence/host/functions/496cc53c4687dffb.diff](evidence/host/functions/496cc53c4687dffb.diff) |
| `block:usleep@plt` | modified | harmless-layout | [evidence/host/functions/65232e2ef2e93e3c.diff](evidence/host/functions/65232e2ef2e93e3c.diff) |
| `block:vfprintf@plt` | removed | restore-with-caller | [evidence/host/functions/37fe140d8d26e695.diff](evidence/host/functions/37fe140d8d26e695.diff) |
| `block:waitpid@plt` | modified | harmless-layout | [evidence/host/functions/4cf20455e4d387c5.diff](evidence/host/functions/4cf20455e4d387c5.diff) |
| `block:write@plt` | modified | harmless-layout | [evidence/host/functions/255ea088f4f7e67c.diff](evidence/host/functions/255ea088f4f7e67c.diff) |
| `fflush` | added | restore | [evidence/host/functions/994ad13f9341d810.diff](evidence/host/functions/994ad13f9341d810.diff) |
| `fprintf` | added | restore | [evidence/host/functions/1be4491e83fe9767.diff](evidence/host/functions/1be4491e83fe9767.diff) |
| `fputc` | added | restore | [evidence/host/functions/14133142b1774f62.diff](evidence/host/functions/14133142b1774f62.diff) |
| `fputs` | added | restore | [evidence/host/functions/d8cde7532b4d78c3.diff](evidence/host/functions/d8cde7532b4d78c3.diff) |
| `fwrite` | added | restore | [evidence/host/functions/37abd85243d6f655.diff](evidence/host/functions/37abd85243d6f655.diff) |
| `main` | modified | harmless-diagnostic | [evidence/host/functions/0d6e4079e36703eb.diff](evidence/host/functions/0d6e4079e36703eb.diff) |
| `vfprintf` | added | restore | [evidence/host/functions/2047ed1ad4f4f2b2.diff](evidence/host/functions/2047ed1ad4f4f2b2.diff) |

## child

| Function | State | Disposition | Evidence |
|---|---|---|---|
| `AbsoluteCanonicalForm` | removed | restore-with-protocol | [evidence/child/functions/442ea670220ac46b.diff](evidence/child/functions/442ea670220ac46b.diff) |
| `AllocatorDomainRejected` | removed | harmless-rename | [evidence/child/functions/90f47f85c5506ae7.diff](evidence/child/functions/90f47f85c5506ae7.diff) |
| `BuildIdentity` | added | restore-with-protocol | [evidence/child/functions/44ee021408568623.diff](evidence/child/functions/44ee021408568623.diff) |
| `BuildRequestKey` | added | restore-with-protocol | [evidence/child/functions/17ebbe651b4fe600.diff](evidence/child/functions/17ebbe651b4fe600.diff) |
| `BytesNonzero` | added | restore-with-protocol | [evidence/child/functions/693ee81a27f9dce5.diff](evidence/child/functions/693ee81a27f9dce5.diff) |
| `CandidateValid` | modified | restore-with-protocol | [evidence/child/functions/de7e2d7316dba1ba.diff](evidence/child/functions/de7e2d7316dba1ba.diff) |
| `CompleteStockChildReply` | modified | retain-diagnostics | [evidence/child/functions/c1516371bd70ea89.diff](evidence/child/functions/c1516371bd70ea89.diff) |
| `CppRuntimeDomainRejected` | removed | harmless-rename | [evidence/child/functions/5585c0ab994ba760.diff](evidence/child/functions/5585c0ab994ba760.diff) |
| `CurrentChildThreadId` | added | restore-with-protocol | [evidence/child/functions/5e4b7c990e0f7a3a.diff](evidence/child/functions/5e4b7c990e0f7a3a.diff) |
| `DigestEqual` | added | restore-with-protocol | [evidence/child/functions/784a8929ef037d80.diff](evidence/child/functions/784a8929ef037d80.diff) |
| `DrainHookOwner` | added | restore-with-protocol | [evidence/child/functions/6f92dd8263dc7ce1.diff](evidence/child/functions/6f92dd8263dc7ce1.diff) |
| `InvalidateHookOwner` | added | restore-with-protocol | [evidence/child/functions/eb599538addcafa0.diff](evidence/child/functions/eb599538addcafa0.diff) |
| `InvokeProviderA06ThenA02` | added | restore | [evidence/child/functions/8af5553d9b67cab4.diff](evidence/child/functions/8af5553d9b67cab4.diff) |
| `InvokeProviderChildEntryWithResolver` | removed | restore-with-protocol | [evidence/child/functions/e42a067cfbdce593.diff](evidence/child/functions/e42a067cfbdce593.diff) |
| `IsAllZeros` | removed | retain-hardening | [evidence/child/functions/1aa79c4f3f37bdaa.diff](evidence/child/functions/1aa79c4f3f37bdaa.diff) |
| `IsInheritedPreloadedProvider` | added | restore-with-protocol | [evidence/child/functions/56e6a83daff6edaf.diff](evidence/child/functions/56e6a83daff6edaf.diff) |
| `LoadSealedProviderAfterHooks` | modified | restore | [evidence/child/functions/7293af0ca174140d.diff](evidence/child/functions/7293af0ca174140d.diff) |
| `MapsState` | added | restore-with-protocol | [evidence/child/functions/d561a04c62267d15.diff](evidence/child/functions/d561a04c62267d15.diff) |
| `OpenVerifiedFileHex` | added | retain-hardening | [evidence/child/functions/2af1956621866e45.diff](evidence/child/functions/2af1956621866e45.diff) |
| `P0AllocatorDomainRejected` | added | harmless-rename | [evidence/child/functions/191d8709aeebab8f.diff](evidence/child/functions/191d8709aeebab8f.diff) |
| `P0CppRuntimeDomainRejected` | added | harmless-rename | [evidence/child/functions/b599e055bf821d8f.diff](evidence/child/functions/b599e055bf821d8f.diff) |
| `P0SignalRouteRejected` | added | harmless-rename | [evidence/child/functions/5d4a33fa11a53525.diff](evidence/child/functions/5d4a33fa11a53525.diff) |
| `P0ThreadCreateRejected` | added | harmless-rename | [evidence/child/functions/5cd1c6d13e08febc.diff](evidence/child/functions/5cd1c6d13e08febc.diff) |
| `P0ThreadDetachRejected` | added | harmless-rename | [evidence/child/functions/dc6a27dd13a195e6.diff](evidence/child/functions/dc6a27dd13a195e6.diff) |
| `P0ThreadJoinRejected` | added | harmless-rename | [evidence/child/functions/21688b9cdb1686af.diff](evidence/child/functions/21688b9cdb1686af.diff) |
| `P0ThreadSelfRejected` | added | harmless-rename | [evidence/child/functions/3fcf3590aa46a5ac.diff](evidence/child/functions/3fcf3590aa46a5ac.diff) |
| `P0TlsGetSetRejected` | added | harmless-rename | [evidence/child/functions/5b3312ddae4cce1b.diff](evidence/child/functions/5b3312ddae4cce1b.diff) |
| `P0TlsKeyCreateRejected` | added | harmless-rename | [evidence/child/functions/4ab8e1712539b785.diff](evidence/child/functions/4ab8e1712539b785.diff) |
| `P0UnwindDomainRejected` | added | harmless-rename | [evidence/child/functions/01684113e17f8f76.diff](evidence/child/functions/01684113e17f8f76.diff) |
| `PublishChildHookTable` | modified | restore-with-protocol | [evidence/child/functions/b6486cdfadf8bd40.diff](evidence/child/functions/b6486cdfadf8bd40.diff) |
| `RealIsMapped` | removed | restore-with-protocol | [evidence/child/functions/475cbc2495cf8f7e.diff](evidence/child/functions/475cbc2495cf8f7e.diff) |
| `RealOpenLocalNow` | removed | restore-with-protocol | [evidence/child/functions/d3e398a468661716.diff](evidence/child/functions/d3e398a468661716.diff) |
| `RequestKey` | added | restore-with-protocol | [evidence/child/functions/db2d4442b90b7706.diff](evidence/child/functions/db2d4442b90b7706.diff) |
| `RevokeChildHookTable` | modified | restore-with-protocol | [evidence/child/functions/31662bb9c0f5736f.diff](evidence/child/functions/31662bb9c0f5736f.diff) |
| `RevokeHookOwner` | added | restore-with-protocol | [evidence/child/functions/c0070373929578f3.diff](evidence/child/functions/c0070373929578f3.diff) |
| `SignalRouteRejected` | removed | harmless-rename | [evidence/child/functions/8a8736c6518f3531.diff](evidence/child/functions/8a8736c6518f3531.diff) |
| `SourceFactsValid` | added | restore-with-protocol | [evidence/child/functions/4e7d9ac9621f6ab0.diff](evidence/child/functions/4e7d9ac9621f6ab0.diff) |
| `ThreadCreateRejected` | removed | harmless-rename | [evidence/child/functions/256103c8f2a2d006.diff](evidence/child/functions/256103c8f2a2d006.diff) |
| `ThreadDetachRejected` | removed | harmless-rename | [evidence/child/functions/a2e68593f498a39a.diff](evidence/child/functions/a2e68593f498a39a.diff) |
| `ThreadJoinRejected` | removed | harmless-rename | [evidence/child/functions/0782c82a7fb29cd9.diff](evidence/child/functions/0782c82a7fb29cd9.diff) |
| `ThreadSelfRejected` | removed | harmless-rename | [evidence/child/functions/8589226396cb1b91.diff](evidence/child/functions/8589226396cb1b91.diff) |
| `TlsGetSetRejected` | removed | harmless-rename | [evidence/child/functions/2c91904d627de959.diff](evidence/child/functions/2c91904d627de959.diff) |
| `TlsKeyCreateRejected` | removed | harmless-rename | [evidence/child/functions/b59c37251b844217.diff](evidence/child/functions/b59c37251b844217.diff) |
| `UnwindDomainRejected` | removed | harmless-rename | [evidence/child/functions/ba1166a1616ab60a.diff](evidence/child/functions/ba1166a1616ab60a.diff) |
| `VerifyBuildId` | modified | retain-hardening | [evidence/child/functions/a8aec7a83b11727c.diff](evidence/child/functions/a8aec7a83b11727c.diff) |
| `VisitClosure` | modified | restore-with-protocol | [evidence/child/functions/d7bb6b36ccbac6bb.diff](evidence/child/functions/d7bb6b36ccbac6bb.diff) |
| `WLASC_InstallStockHostServicesV1` | modified | restore-with-protocol | [evidence/child/functions/73b6c7afb2f3cd44.diff](evidence/child/functions/73b6c7afb2f3cd44.diff) |
| `WLASC_ReceiptChildTail` | modified | harmless-constant-relocation | [evidence/child/functions/ad47e7293e47dca3.diff](evidence/child/functions/ad47e7293e47dca3.diff) |
| `WLASC_ReceiptConsume` | modified | harmless-constant-relocation | [evidence/child/functions/d91f3fe397d3242e.diff](evidence/child/functions/d91f3fe397d3242e.diff) |
| `WLASC_ReceiptParentTail` | modified | harmless-constant-relocation | [evidence/child/functions/a71e2d7b7329adc2.diff](evidence/child/functions/a71e2d7b7329adc2.diff) |
| `WLEI_CloseVerifiedFile` | added | retain-hardening | [evidence/child/functions/0eadf1ac94205822.diff](evidence/child/functions/0eadf1ac94205822.diff) |
| `WLEI_OpenVerifiedFileHex` | added | retain-hardening | [evidence/child/functions/919966f6ad549db5.diff](evidence/child/functions/919966f6ad549db5.diff) |
| `WLEI_OpenVerifiedSystemFileHex` | added | retain-hardening | [evidence/child/functions/792e1cdd298a2381.diff](evidence/child/functions/792e1cdd298a2381.diff) |
| `WLEI_VerifyFileHex` | modified | retain-hardening | [evidence/child/functions/9d3ec6012099fd07.diff](evidence/child/functions/9d3ec6012099fd07.diff) |
| `WLEI_VerifyLoadedSymbolHex` | modified | retain-hardening | [evidence/child/functions/b2c895d136033ce3.diff](evidence/child/functions/b2c895d136033ce3.diff) |
| `WLSCPL_GetLastArtifactIdentityDetail` | added | restore-with-protocol | [evidence/child/functions/64a3ef39f0de07ee.diff](evidence/child/functions/64a3ef39f0de07ee.diff) |
| `WLSCPL_InheritAndroidRuntimeV1` | added | restore | [evidence/child/functions/916349540820e557.diff](evidence/child/functions/916349540820e557.diff) |
| `WLSCPL_LoadSealedProvider` | modified | restore-with-protocol | [evidence/child/functions/b7a2cd9200bc95c9.diff](evidence/child/functions/b7a2cd9200bc95c9.diff) |
| `WLSCPL_OpenPreparedNamespace` | modified | restore | [evidence/child/functions/a7972c88802d846c.diff](evidence/child/functions/a7972c88802d846c.diff) |
| `WLSha256Final` | modified | harmless-constant-relocation | [evidence/child/functions/d28e042158734192.diff](evidence/child/functions/d28e042158734192.diff) |
| `WLSha256Init` | modified | harmless-constant-relocation | [evidence/child/functions/fa25d3ab361d4b84.diff](evidence/child/functions/fa25d3ab361d4b84.diff) |
| `WestlakeChildBypassGuard` | modified | harmless-layout | [evidence/child/functions/d65ed1ef64aed619.diff](evidence/child/functions/d65ed1ef64aed619.diff) |
| `WestlakeRunAndroidChild` | modified | restore-with-protocol | [evidence/child/functions/656d041b018b60aa.diff](evidence/child/functions/656d041b018b60aa.diff) |
| `WlascGateMarker` | modified | retain-diagnostics | [evidence/child/functions/34967055c31bd750.diff](evidence/child/functions/34967055c31bd750.diff) |
| `WlascGateMarkerValue` | modified | retain-diagnostics | [evidence/child/functions/fd31d70f54ed718f.diff](evidence/child/functions/fd31d70f54ed718f.diff) |
| `WlgrIfAcquire` | added | restore-with-protocol | [evidence/child/functions/15954198db5a3db0.diff](evidence/child/functions/15954198db5a3db0.diff) |
| `WlgrIfChildReadSeal` | added | restore-with-protocol | [evidence/child/functions/8b956c69d4620439.diff](evidence/child/functions/8b956c69d4620439.diff) |
| `WlgrIfDigestMetadata` | added | restore-with-protocol | [evidence/child/functions/f8ad6a8caea0e450.diff](evidence/child/functions/f8ad6a8caea0e450.diff) |
| `WlgrIfDigestStockReceipt` | added | restore-with-protocol | [evidence/child/functions/d846689d1c5408ef.diff](evidence/child/functions/d846689d1c5408ef.diff) |
| `WlgrIfGetBuildGeneratedMetadata` | added | restore-with-protocol | [evidence/child/functions/0f44443091d54214.diff](evidence/child/functions/0f44443091d54214.diff) |
| `WlgrIfParentSeal` | added | restore-with-protocol | [evidence/child/functions/dc962b7e64312f4e.diff](evidence/child/functions/dc962b7e64312f4e.diff) |
| `WlgrIfParseBootId` | added | restore-with-protocol | [evidence/child/functions/3733bc2086e25e49.diff](evidence/child/functions/3733bc2086e25e49.diff) |
| `WlgrIfProduceHookSchemaDigest` | added | restore-with-protocol | [evidence/child/functions/d11f9ec6a12f43c0.diff](evidence/child/functions/d11f9ec6a12f43c0.diff) |
| `WlgrIfProductionContextInit` | added | restore-with-protocol | [evidence/child/functions/61235cd6a5e45da9.diff](evidence/child/functions/61235cd6a5e45da9.diff) |
| `WlgrIfProductionOps` | added | restore-with-protocol | [evidence/child/functions/3ad66189df8b0e1d.diff](evidence/child/functions/3ad66189df8b0e1d.diff) |
| `WlgrIfProductionRandom` | added | restore-with-protocol | [evidence/child/functions/339450db99d79cde.diff](evidence/child/functions/339450db99d79cde.diff) |
| `WlgrIfProductionReadBootId` | added | restore-with-protocol | [evidence/child/functions/0b102c60ad799133.diff](evidence/child/functions/0b102c60ad799133.diff) |
| `WlgrIfProductionReadHook` | added | restore-with-protocol | [evidence/child/functions/0dc6410f2c90f67a.diff](evidence/child/functions/0dc6410f2c90f67a.diff) |
| `WlgrIfProductionReadManifest` | added | restore-with-protocol | [evidence/child/functions/c9a5793506a4925e.diff](evidence/child/functions/c9a5793506a4925e.diff) |
| `WlgrIfProductionReadMetadata` | added | restore-with-protocol | [evidence/child/functions/f39a488ab79bed8f.diff](evidence/child/functions/f39a488ab79bed8f.diff) |
| `WlgrIfProductionReadProcess` | added | restore-with-protocol | [evidence/child/functions/f3fd7957a67e89d1.diff](evidence/child/functions/f3fd7957a67e89d1.diff) |
| `WlgrIfProductionReadReceipt` | added | restore-with-protocol | [evidence/child/functions/f6c1558c1f834e18.diff](evidence/child/functions/f6c1558c1f834e18.diff) |
| `WlgrIfSerializeStockReceipt` | added | restore-with-protocol | [evidence/child/functions/8ebee2a6cb6269bf.diff](evidence/child/functions/8ebee2a6cb6269bf.diff) |
| `WlgrIfValidateHook` | added | restore-with-protocol | [evidence/child/functions/f800e17e85367760.diff](evidence/child/functions/f800e17e85367760.diff) |
| `WlgrIfValidateMetadata` | added | restore-with-protocol | [evidence/child/functions/a3665575e2dae171.diff](evidence/child/functions/a3665575e2dae171.diff) |
| `WlgrIpBuild` | added | restore-with-protocol | [evidence/child/functions/3dbe2dc06d0ab270.diff](evidence/child/functions/3dbe2dc06d0ab270.diff) |
| `WlgrIpGetIdentity` | added | restore-with-protocol | [evidence/child/functions/1189e5395edc1fa3.diff](evidence/child/functions/1189e5395edc1fa3.diff) |
| `WlgrIpValidate` | added | restore-with-protocol | [evidence/child/functions/2fa544e03d14a662.diff](evidence/child/functions/2fa544e03d14a662.diff) |
| `block:.plt` | modified | harmless-layout | [evidence/child/functions/80a03770c27acce1.diff](evidence/child/functions/80a03770c27acce1.diff) |
| `block:__errno_location@plt` | modified | harmless-layout | [evidence/child/functions/927836485dd999ab.diff](evidence/child/functions/927836485dd999ab.diff) |
| `block:_exit@plt` | modified | harmless-layout | [evidence/child/functions/6c1b173043efcd10.diff](evidence/child/functions/6c1b173043efcd10.diff) |
| `block:clock_gettime@plt` | added | restore-with-caller | [evidence/child/functions/97f23e6c27919fa1.diff](evidence/child/functions/97f23e6c27919fa1.diff) |
| `block:close@plt` | modified | harmless-layout | [evidence/child/functions/7c043866062c01ed.diff](evidence/child/functions/7c043866062c01ed.diff) |
| `block:dladdr@plt` | modified | harmless-layout | [evidence/child/functions/d01a977040932b95.diff](evidence/child/functions/d01a977040932b95.diff) |
| `block:dlclose@plt` | removed | restore-with-caller | [evidence/child/functions/8741a3a1471dbaba.diff](evidence/child/functions/8741a3a1471dbaba.diff) |
| `block:dlerror@plt` | modified | harmless-layout | [evidence/child/functions/b7a5ccb01422a4be.diff](evidence/child/functions/b7a5ccb01422a4be.diff) |
| `block:dlns_create2@plt` | modified | harmless-layout | [evidence/child/functions/b476cf2ace2bf3ec.diff](evidence/child/functions/b476cf2ace2bf3ec.diff) |
| `block:dlns_inherit@plt` | added | restore-with-caller | [evidence/child/functions/e9086a7a40fd8e3a.diff](evidence/child/functions/e9086a7a40fd8e3a.diff) |
| `block:dlns_init@plt` | modified | harmless-layout | [evidence/child/functions/05bc1bf8e05f8d4d.diff](evidence/child/functions/05bc1bf8e05f8d4d.diff) |
| `block:dlopen@plt` | removed | restore-with-caller | [evidence/child/functions/3ff36795fedc06aa.diff](evidence/child/functions/3ff36795fedc06aa.diff) |
| `block:dlopen_ns@plt` | modified | harmless-layout | [evidence/child/functions/f34f70a3849561b8.diff](evidence/child/functions/f34f70a3849561b8.diff) |
| `block:dlsym@plt` | modified | harmless-layout | [evidence/child/functions/74dc8db09c3e3dbd.diff](evidence/child/functions/74dc8db09c3e3dbd.diff) |
| `block:fclose@plt` | modified | harmless-layout | [evidence/child/functions/992fe58255b0a1fe.diff](evidence/child/functions/992fe58255b0a1fe.diff) |
| `block:fgets@plt` | modified | harmless-layout | [evidence/child/functions/5dada9f75d82571e.diff](evidence/child/functions/5dada9f75d82571e.diff) |
| `block:fopen@plt` | modified | harmless-layout | [evidence/child/functions/f39d29002639dcfa.diff](evidence/child/functions/f39d29002639dcfa.diff) |
| `block:free@plt` | modified | harmless-layout | [evidence/child/functions/ed9127767958e20c.diff](evidence/child/functions/ed9127767958e20c.diff) |
| `block:fstat@plt` | modified | harmless-layout | [evidence/child/functions/1c048c0d7c4a2c0b.diff](evidence/child/functions/1c048c0d7c4a2c0b.diff) |
| `block:getpid@plt` | modified | harmless-layout | [evidence/child/functions/7b44857ed6d3dc22.diff](evidence/child/functions/7b44857ed6d3dc22.diff) |
| `block:getppid@plt` | modified | harmless-layout | [evidence/child/functions/606c42813a307ddc.diff](evidence/child/functions/606c42813a307ddc.diff) |
| `block:getrandom@plt` | added | restore-with-caller | [evidence/child/functions/2a8079bcaf687820.diff](evidence/child/functions/2a8079bcaf687820.diff) |
| `block:malloc@plt` | modified | harmless-layout | [evidence/child/functions/329fe710d164f551.diff](evidence/child/functions/329fe710d164f551.diff) |
| `block:memcmp@plt` | modified | harmless-layout | [evidence/child/functions/1e7f22f44fa3dad5.diff](evidence/child/functions/1e7f22f44fa3dad5.diff) |
| `block:memcpy@plt` | modified | harmless-layout | [evidence/child/functions/100657bf3a1dd88c.diff](evidence/child/functions/100657bf3a1dd88c.diff) |
| `block:memset@plt` | modified | harmless-layout | [evidence/child/functions/8be105e928130577.diff](evidence/child/functions/8be105e928130577.diff) |
| `block:open@plt` | modified | harmless-layout | [evidence/child/functions/2464f032fca0d429.diff](evidence/child/functions/2464f032fca0d429.diff) |
| `block:pread@plt` | modified | harmless-layout | [evidence/child/functions/5723c6060986ee9c.diff](evidence/child/functions/5723c6060986ee9c.diff) |
| `block:read@plt` | modified | harmless-layout | [evidence/child/functions/e51ceecb4ff0d918.diff](evidence/child/functions/e51ceecb4ff0d918.diff) |
| `block:realpath@plt` | modified | harmless-layout | [evidence/child/functions/5e57d1a72adef07e.diff](evidence/child/functions/5e57d1a72adef07e.diff) |
| `block:sched_yield@plt` | added | restore-with-caller | [evidence/child/functions/02d9f38630b97c01.diff](evidence/child/functions/02d9f38630b97c01.diff) |
| `block:snprintf@plt` | added | restore-with-caller | [evidence/child/functions/46e2fcfb713e7f7b.diff](evidence/child/functions/46e2fcfb713e7f7b.diff) |
| `block:sscanf@plt` | added | restore-with-caller | [evidence/child/functions/06a9ec2c9e6b7c70.diff](evidence/child/functions/06a9ec2c9e6b7c70.diff) |
| `block:strchr@plt` | modified | harmless-layout | [evidence/child/functions/d725baceedc3df64.diff](evidence/child/functions/d725baceedc3df64.diff) |
| `block:strcmp@plt` | modified | harmless-layout | [evidence/child/functions/da20ffa12cded264.diff](evidence/child/functions/da20ffa12cded264.diff) |
| `block:strlen@plt` | modified | harmless-layout | [evidence/child/functions/c83f5045be37ed80.diff](evidence/child/functions/c83f5045be37ed80.diff) |
| `block:strncmp@plt` | removed | restore-with-caller | [evidence/child/functions/0e2f274f7bc1d019.diff](evidence/child/functions/0e2f274f7bc1d019.diff) |
| `block:strrchr@plt` | modified | harmless-layout | [evidence/child/functions/0f459b9a0a94835d.diff](evidence/child/functions/0f459b9a0a94835d.diff) |
| `block:strtoull@plt` | added | restore-with-caller | [evidence/child/functions/e406afe7a80f27d6.diff](evidence/child/functions/e406afe7a80f27d6.diff) |
| `block:write@plt` | modified | harmless-layout | [evidence/child/functions/255ea088f4f7e67c.diff](evidence/child/functions/255ea088f4f7e67c.diff) |
| `westlake_child_hook_table_v1_drain` | modified | restore-with-protocol | [evidence/child/functions/a0e4b9e3d9c33b7e.diff](evidence/child/functions/a0e4b9e3d9c33b7e.diff) |
| `westlake_child_hook_table_v1_invalidate` | modified | restore-with-protocol | [evidence/child/functions/9815358b11a99aac.diff](evidence/child/functions/9815358b11a99aac.diff) |
| `westlake_child_hook_table_v1_prepare_candidate` | modified | restore | [evidence/child/functions/4048961ccf1ee582.diff](evidence/child/functions/4048961ccf1ee582.diff) |
| `westlake_child_hook_table_v1_prepare_candidate_with_callbacks` | added | restore-with-protocol | [evidence/child/functions/6b2732188922b485.diff](evidence/child/functions/6b2732188922b485.diff) |
| `westlake_child_hook_table_v1_revoke` | modified | restore-with-protocol | [evidence/child/functions/a65bdf03bc983ee7.diff](evidence/child/functions/a65bdf03bc983ee7.diff) |
| `wlgr_v2_a02_bundle_valid` | added | restore-with-protocol | [evidence/child/functions/e4ee0eda0b4fe01a.diff](evidence/child/functions/e4ee0eda0b4fe01a.diff) |
| `wlgr_v2_bytes_zero` | added | restore-with-protocol | [evidence/child/functions/37383ed807954fe3.diff](evidence/child/functions/37383ed807954fe3.diff) |
| `wlgr_v2_expected_owner` | added | restore-with-protocol | [evidence/child/functions/1108c31309dec127.diff](evidence/child/functions/1108c31309dec127.diff) |
| `wlgr_v2_identity_equal` | added | restore-with-protocol | [evidence/child/functions/c139c3aac5b13186.diff](evidence/child/functions/c139c3aac5b13186.diff) |
| `wlgr_v2_identity_equal#2` | added | restore-with-protocol | [evidence/child/functions/42ec7823ec1d4300.diff](evidence/child/functions/42ec7823ec1d4300.diff) |
| `wlgr_v2_identity_valid` | added | restore-with-protocol | [evidence/child/functions/a7f42c03cd4fd5eb.diff](evidence/child/functions/a7f42c03cd4fd5eb.diff) |
| `wlgr_v2_identity_valid#2` | added | restore-with-protocol | [evidence/child/functions/f8adb2b8c7887dbe.diff](evidence/child/functions/f8adb2b8c7887dbe.diff) |
| `wlgr_v2_receipt_valid` | added | restore-with-protocol | [evidence/child/functions/f5d4b6d62511d411.diff](evidence/child/functions/f5d4b6d62511d411.diff) |
| `wlgr_v2_runtime_key_equal` | added | restore-with-protocol | [evidence/child/functions/fc0fb81bbec42401.diff](evidence/child/functions/fc0fb81bbec42401.diff) |
| `wlgr_v2_runtime_key_valid` | added | restore-with-protocol | [evidence/child/functions/ce3f8ee37d0819bf.diff](evidence/child/functions/ce3f8ee37d0819bf.diff) |
| `wlgr_v2_runtime_key_valid#2` | added | restore-with-protocol | [evidence/child/functions/74f2716aed642036.diff](evidence/child/functions/74f2716aed642036.diff) |

## runtime-provider

| Function | State | Disposition | Evidence |
|---|---|---|---|
| `IsAllZeros` | removed | retain-hardening | [evidence/runtime-provider/functions/1aa79c4f3f37bdaa.diff](evidence/runtime-provider/functions/1aa79c4f3f37bdaa.diff) |
| `OpenVerifiedFileHex` | added | retain-hardening | [evidence/runtime-provider/functions/2af1956621866e45.diff](evidence/runtime-provider/functions/2af1956621866e45.diff) |
| `VerifyBuildId` | modified | retain-hardening | [evidence/runtime-provider/functions/a8aec7a83b11727c.diff](evidence/runtime-provider/functions/a8aec7a83b11727c.diff) |
| `WLAR_EnterAndroidAfterStockSpecialization` | modified | restore | [evidence/runtime-provider/functions/3228fee5dd0320f9.diff](evidence/runtime-provider/functions/3228fee5dd0320f9.diff) |
| `WLAR_GetRuntimeIdentity` | modified | retain-generation | [evidence/runtime-provider/functions/13e1e8ffa5fa3a79.diff](evidence/runtime-provider/functions/13e1e8ffa5fa3a79.diff) |
| `WLAR_HostServicesGetNamespaceCallbacks` | modified | restore-with-protocol | [evidence/runtime-provider/functions/ade19426b5548e16.diff](evidence/runtime-provider/functions/ade19426b5548e16.diff) |
| `WLAR_HostServicesIsInstalled` | removed | restore-with-protocol | [evidence/runtime-provider/functions/4846f53075b28962.diff](evidence/runtime-provider/functions/4846f53075b28962.diff) |
| `WLAR_InstallHostRuntimeServices` | modified | restore-with-protocol | [evidence/runtime-provider/functions/3e1af20b69614705.diff](evidence/runtime-provider/functions/3e1af20b69614705.diff) |
| `WLAR_LoaderPhaseFail` | removed | restore-with-protocol | [evidence/runtime-provider/functions/54cd42f867e35941.diff](evidence/runtime-provider/functions/54cd42f867e35941.diff) |
| `WLAR_PrepareA02PrerequisiteBundleV2` | added | restore | [evidence/runtime-provider/functions/9772286fc273ebf2.diff](evidence/runtime-provider/functions/9772286fc273ebf2.diff) |
| `WLEI_VerifyFileHex` | modified | retain-hardening | [evidence/runtime-provider/functions/9d3ec6012099fd07.diff](evidence/runtime-provider/functions/9d3ec6012099fd07.diff) |
| `WLEI_VerifyLoadedSymbolHex` | modified | retain-hardening | [evidence/runtime-provider/functions/b2c895d136033ce3.diff](evidence/runtime-provider/functions/b2c895d136033ce3.diff) |
| `WLSha256Final` | modified | harmless-constant-relocation | [evidence/runtime-provider/functions/d28e042158734192.diff](evidence/runtime-provider/functions/d28e042158734192.diff) |
| `WLSha256Init` | modified | harmless-constant-relocation | [evidence/runtime-provider/functions/fa25d3ab361d4b84.diff](evidence/runtime-provider/functions/fa25d3ab361d4b84.diff) |
| `_GLOBAL__sub_I_westlake_android_runtime_provider.cpp` | added | restore-with-protocol | [evidence/runtime-provider/functions/b781eb8d00eb13f1.diff](evidence/runtime-provider/functions/b781eb8d00eb13f1.diff) |
| `_ZL21wlgr_v2_receipt_validPK33westlake_runtime_stage_receipt_v2` | added | restore-with-protocol | [evidence/runtime-provider/functions/34e7b9536c6071f5.diff](evidence/runtime-provider/functions/34e7b9536c6071f5.diff) |
| `_ZL22wlgr_v2_expected_ownerj` | added | restore-with-protocol | [evidence/runtime-provider/functions/ad54abdb8bed6b2c.diff](evidence/runtime-provider/functions/ad54abdb8bed6b2c.diff) |
| `_ZL22wlgr_v2_identity_equalPK31westlake_generation_identity_v2S1_` | added | restore-with-protocol | [evidence/runtime-provider/functions/e7e288d2317c8785.diff](evidence/runtime-provider/functions/e7e288d2317c8785.diff) |
| `_ZL22wlgr_v2_identity_validPK31westlake_generation_identity_v2` | added | restore-with-protocol | [evidence/runtime-provider/functions/e3541073abbd9097.diff](evidence/runtime-provider/functions/e3541073abbd9097.diff) |
| `_ZL24wlgr_v2_a02_bundle_validPK35westlake_a02_prerequisite_bundle_v2` | added | restore-with-protocol | [evidence/runtime-provider/functions/fd828f913dc7652f.diff](evidence/runtime-provider/functions/fd828f913dc7652f.diff) |
| `_ZL25wlgr_v2_runtime_key_validPK32westlake_runtime_instance_key_v2` | added | restore-with-protocol | [evidence/runtime-provider/functions/15e88f98faeee769.diff](evidence/runtime-provider/functions/15e88f98faeee769.diff) |
| `_ZN12_GLOBAL__N_110InvalidateEPv` | added | restore-with-protocol | [evidence/runtime-provider/functions/97129647c4fa87bc.diff](evidence/runtime-provider/functions/97129647c4fa87bc.diff) |
| `_ZN12_GLOBAL__N_111VerifyReadyEPv` | added | restore-with-protocol | [evidence/runtime-provider/functions/89562de02d9d875e.diff](evidence/runtime-provider/functions/89562de02d9d875e.diff) |
| `_ZN12_GLOBAL__N_112ConstructorsEPv` | added | restore-with-protocol | [evidence/runtime-provider/functions/fc7370b5c8fafe96.diff](evidence/runtime-provider/functions/fc7370b5c8fafe96.diff) |
| `_ZN12_GLOBAL__N_112RequestValidEPK26WlascAndroidChildRequestV1PK24WlascStockStageReceiptV1` | added | restore-with-protocol | [evidence/runtime-provider/functions/6ae197821eff7624.diff](evidence/runtime-provider/functions/6ae197821eff7624.diff) |
| `_ZN12_GLOBAL__N_113CreateChildVmEPv` | removed | restore-with-protocol | [evidence/runtime-provider/functions/453251049f79cde1.diff](evidence/runtime-provider/functions/453251049f79cde1.diff) |
| `_ZN12_GLOBAL__N_114EnterChildMainEPv` | removed | restore-with-protocol | [evidence/runtime-provider/functions/cea3243c1de97639.diff](evidence/runtime-provider/functions/cea3243c1de97639.diff) |
| `_ZN12_GLOBAL__N_115DrainChildCallsEPv` | removed | restore-with-protocol | [evidence/runtime-provider/functions/8d6a35281eec11a9.diff](evidence/runtime-provider/functions/8d6a35281eec11a9.diff) |
| `_ZN12_GLOBAL__N_116CompleteChildJniEPv` | removed | restore-with-protocol | [evidence/runtime-provider/functions/53b538707b52a3e0.diff](evidence/runtime-provider/functions/53b538707b52a3e0.diff) |
| `_ZN12_GLOBAL__N_116TranslateRequestERK26WlascAndroidChildRequestV1` | removed | restore-with-protocol | [evidence/runtime-provider/functions/9df4b884b58f516a.diff](evidence/runtime-provider/functions/9df4b884b58f516a.diff) |
| `_ZN12_GLOBAL__N_117FillGenerationShaEPh` | removed | restore-with-protocol | [evidence/runtime-provider/functions/6dc6e42c0999f2da.diff](evidence/runtime-provider/functions/6dc6e42c0999f2da.diff) |
| `_ZN12_GLOBAL__N_118AuditSnapshotValidERK19WlncAuditSnapshotV1m` | removed | restore-with-protocol | [evidence/runtime-provider/functions/89f5dd0f360bac1b.diff](evidence/runtime-provider/functions/89f5dd0f360bac1b.diff) |
| `_ZN12_GLOBAL__N_119CommitAuditSnapshotEPv` | added | restore-with-protocol | [evidence/runtime-provider/functions/9bafddb7613c9398.diff](evidence/runtime-provider/functions/9bafddb7613c9398.diff) |
| `_ZN12_GLOBAL__N_120CaptureAuditSnapshotEPvPN19wlar_child_sequence21LosslessAuditSnapshotE` | added | restore-with-protocol | [evidence/runtime-provider/functions/63ed6b9aaadc5842.diff](evidence/runtime-provider/functions/63ed6b9aaadc5842.diff) |
| `_ZN12_GLOBAL__N_120LoaderAdmissionValidEPK16WlscplManifestV2PK18WlscplLoadResultV2` | added | restore-with-protocol | [evidence/runtime-provider/functions/f9400d4d2b8706ac.diff](evidence/runtime-provider/functions/f9400d4d2b8706ac.diff) |
| `_ZN12_GLOBAL__N_120RevokeChildAdmissionEPv` | removed | restore-with-protocol | [evidence/runtime-provider/functions/58c82053b963941e.diff](evidence/runtime-provider/functions/58c82053b963941e.diff) |
| `_ZN12_GLOBAL__N_121ConstructChildRuntimeEPv` | removed | restore | [evidence/runtime-provider/functions/393b8f6894fd9fae.diff](evidence/runtime-provider/functions/393b8f6894fd9fae.diff) |
| `_ZN12_GLOBAL__N_122OpenNamespaceFromStockEP12Dl_namespacePKci` | removed | restore-with-protocol | [evidence/runtime-provider/functions/f5889a63798e63ad.diff](evidence/runtime-provider/functions/f5889a63798e63ad.diff) |
| `_ZN12_GLOBAL__N_123VerifyLoaderThreadReadyEPv` | removed | restore-with-protocol | [evidence/runtime-provider/functions/9971afcbd73b8c22.diff](evidence/runtime-provider/functions/9971afcbd73b8c22.diff) |
| `_ZN12_GLOBAL__N_124InvalidateChildAdmissionEPv` | removed | restore-with-protocol | [evidence/runtime-provider/functions/6b4b636d7da23943.diff](evidence/runtime-provider/functions/6b4b636d7da23943.diff) |
| `_ZN12_GLOBAL__N_12VmEPv` | added | restore-with-protocol | [evidence/runtime-provider/functions/35af11dc6fb75994.diff](evidence/runtime-provider/functions/35af11dc6fb75994.diff) |
| `_ZN12_GLOBAL__N_135CreateConfiguredNamespacesFromStockEP12Dl_namespacePKcS3_S3_S3_S3_PK13WlpbHostOpsV1PPvS1_S3_S3_S3_` | removed | restore-with-protocol | [evidence/runtime-provider/functions/321c56dab4437bec.diff](evidence/runtime-provider/functions/321c56dab4437bec.diff) |
| `_ZN12_GLOBAL__N_13JniEPv` | added | restore-with-protocol | [evidence/runtime-provider/functions/c3ea0174d82cf0f6.diff](evidence/runtime-provider/functions/c3ea0174d82cf0f6.diff) |
| `_ZN12_GLOBAL__N_13NowEPv` | added | restore-with-protocol | [evidence/runtime-provider/functions/8f7efd3bbaaa2153.diff](evidence/runtime-provider/functions/8f7efd3bbaaa2153.diff) |
| `_ZN12_GLOBAL__N_13TidEPv` | added | restore-with-protocol | [evidence/runtime-provider/functions/0fa7e7a8caac1bd5.diff](evidence/runtime-provider/functions/0fa7e7a8caac1bd5.diff) |
| `_ZN12_GLOBAL__N_15DrainEPv` | added | restore-with-protocol | [evidence/runtime-provider/functions/e0c3e22626fe3592.diff](evidence/runtime-provider/functions/e0c3e22626fe3592.diff) |
| `_ZN12_GLOBAL__N_16DigestEPvPKvmPh` | added | restore-with-protocol | [evidence/runtime-provider/functions/0e10d4cf5ec57fec.diff](evidence/runtime-provider/functions/0e10d4cf5ec57fec.diff) |
| `_ZN12_GLOBAL__N_16RevokeEPvi` | added | restore-with-protocol | [evidence/runtime-provider/functions/ecf21b368bb88725.diff](evidence/runtime-provider/functions/ecf21b368bb88725.diff) |
| `_ZN12_GLOBAL__N_17ContextD2Ev` | added | restore-with-protocol | [evidence/runtime-provider/functions/41c986e894c7361f.diff](evidence/runtime-provider/functions/41c986e894c7361f.diff) |
| `_ZN12_GLOBAL__N_19TranslateERK26WlascAndroidChildRequestV1` | added | restore-with-protocol | [evidence/runtime-provider/functions/1c127e84865bd153.diff](evidence/runtime-provider/functions/1c127e84865bd153.diff) |
| `_ZN19wlar_child_sequence16CommitA02HandoffEPNS_6LedgerERKNS_10OperationsEP33westlake_runtime_stage_receipt_v2` | added | restore-with-protocol | [evidence/runtime-provider/functions/b500eb113ea5dd43.diff](evidence/runtime-provider/functions/b500eb113ea5dd43.diff) |
| `_ZN19wlar_child_sequence3RunEPNS_6LedgerERK31westlake_generation_identity_v2PK33westlake_runtime_stage_receipt_v2jRKNS_10OperationsEP35westlake_a02_prerequisite_bundle_v2PS5_` | added | restore-with-protocol | [evidence/runtime-provider/functions/e881e5ed34ca94bf.diff](evidence/runtime-provider/functions/e881e5ed34ca94bf.diff) |
| `_ZN19wlar_child_sequence3RunEPNS_6LedgerERKNS_9AdmissionEmRKNS_10OperationsE` | removed | restore-with-protocol | [evidence/runtime-provider/functions/85d9bc048f38246d.diff](evidence/runtime-provider/functions/85d9bc048f38246d.diff) |
| `_ZN19wlar_child_sequence4FailEPNS_6LedgerERKNS_10OperationsEi` | removed | restore-with-protocol | [evidence/runtime-provider/functions/3f2b5ce232a2307b.diff](evidence/runtime-provider/functions/3f2b5ce232a2307b.diff) |
| `_ZN19wlar_child_sequenceL18AuditSnapshotValidERKNS_21LosslessAuditSnapshotEm` | added | restore-with-protocol | [evidence/runtime-provider/functions/51d00f09bd67a7c3.diff](evidence/runtime-provider/functions/51d00f09bd67a7c3.diff) |
| `_ZN19wlar_child_sequenceL18FillSuccessReceiptERKNS_10OperationsERK31westlake_generation_identity_v2jmmPKvmP33westlake_runtime_stage_receipt_v2` | added | restore-with-protocol | [evidence/runtime-provider/functions/588602ff35a0b26e.diff](evidence/runtime-provider/functions/588602ff35a0b26e.diff) |
| `_ZN19wlar_child_sequenceL4FailEPNS_6LedgerERKNS_10OperationsEjiiPKhP33westlake_runtime_stage_receipt_v2` | added | restore-with-protocol | [evidence/runtime-provider/functions/88e0bea3b82efcd1.diff](evidence/runtime-provider/functions/88e0bea3b82efcd1.diff) |
| `_ZN19wlar_child_sequenceL4HashERKNS_10OperationsEPKvmPh` | added | restore-with-protocol | [evidence/runtime-provider/functions/923cf466e6181bba.diff](evidence/runtime-provider/functions/923cf466e6181bba.diff) |
| `_ZN8westlake3jni18AttachStatusStringENS0_12AttachStatusE` | modified | harmless-layout | [evidence/runtime-provider/functions/91d3a1467349fdf4.diff](evidence/runtime-provider/functions/91d3a1467349fdf4.diff) |
| `_ZN9appspawnx16AppSpawnXRuntime7preloadEv` | modified | restore | [evidence/runtime-provider/functions/6d5a1aaa444cdd18.diff](evidence/runtime-provider/functions/6d5a1aaa444cdd18.diff) |
| `_ZN9appspawnx16AppSpawnXRuntime7startVmEb` | modified | restore | [evidence/runtime-provider/functions/5377bb33fa19d9f6.diff](evidence/runtime-provider/functions/5377bb33fa19d9f6.diff) |
| `_ZN9appspawnx9ChildMain27runAfterStockSpecializationERKNS_8SpawnMsgEPNS_16AppSpawnXRuntimeE` | modified | harmless-constant-relocation | [evidence/runtime-provider/functions/f8463b3e55a8975d.diff](evidence/runtime-provider/functions/f8463b3e55a8975d.diff) |
| `_ZN9appspawnxL23logArtAbortAndTerminateEv` | added | restore-with-protocol | [evidence/runtime-provider/functions/badba79270d8828f.diff](evidence/runtime-provider/functions/badba79270d8828f.diff) |
| `_ZNKSt3__h6vectorIiNS_9allocatorIiEEE20__throw_length_errorB6v15004Ev` | removed | harmless-codegen | [evidence/runtime-provider/functions/3db580e26ae8d07b.diff](evidence/runtime-provider/functions/3db580e26ae8d07b.diff) |
| `__emutls_unregister_key` | modified | restore-hardening | [evidence/runtime-provider/functions/c6a96413af3f8e89.diff](evidence/runtime-provider/functions/c6a96413af3f8e89.diff) |
| `block:.plt` | modified | harmless-layout | [evidence/runtime-provider/functions/80a03770c27acce1.diff](evidence/runtime-provider/functions/80a03770c27acce1.diff) |
| `block:ANL_InstallRuntimeGate@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/4a3ebc6b5219464a.diff](evidence/runtime-provider/functions/4a3ebc6b5219464a.diff) |
| `block:HiLogPrint@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/ca85586b6af254a3.diff](evidence/runtime-provider/functions/ca85586b6af254a3.diff) |
| `block:InitializeNativeLoader@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/fff9823019266c13.diff](evidence/runtime-provider/functions/fff9823019266c13.diff) |
| `block:WLNL_InstallSealedOpenV1@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/0d5bca2b3cb026da.diff](evidence/runtime-provider/functions/0d5bca2b3cb026da.diff) |
| `block:WLTG_CancelThreadTicket@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/fa2a1d9261118b9f.diff](evidence/runtime-provider/functions/fa2a1d9261118b9f.diff) |
| `block:WLTG_IssueThreadTicket@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/b234d94d483b6173.diff](evidence/runtime-provider/functions/b234d94d483b6173.diff) |
| `block:WLTG_PrepareCurrentThread@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/044565fa22ecefdf.diff](evidence/runtime-provider/functions/044565fa22ecefdf.diff) |
| `block:WLTG_ReasonString@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/2a44810e95c4715f.diff](evidence/runtime-provider/functions/2a44810e95c4715f.diff) |
| `block:WLTG_RetireCurrentThread@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/61e2157d9b06587a.diff](evidence/runtime-provider/functions/61e2157d9b06587a.diff) |
| `block:WLTG_VerifyCurrentThreadReady@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/cd79c4bf1818a5de.diff](evidence/runtime-provider/functions/cd79c4bf1818a5de.diff) |
| `block:_Unwind_Resume@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/e28eb13bb1b253ab.diff](evidence/runtime-provider/functions/e28eb13bb1b253ab.diff) |
| `block:_ZNSt11logic_errorC2EPKc@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/bd40e5078d4311d6.diff](evidence/runtime-provider/functions/bd40e5078d4311d6.diff) |
| `block:_ZNSt20bad_array_new_lengthC1Ev@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/310cbf9366df9e7b.diff](evidence/runtime-provider/functions/310cbf9366df9e7b.diff) |
| `block:_ZNSt3__h12basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6appendEPKc@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/fe61a000d33aeb71.diff](evidence/runtime-provider/functions/fe61a000d33aeb71.diff) |
| `block:_ZNSt3__h12basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6assignEPKc@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/46d8fd3346c90c49.diff](evidence/runtime-provider/functions/46d8fd3346c90c49.diff) |
| `block:_ZNSt3__h12basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEEC1ERKS5_@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/8466731e1c4dad00.diff](evidence/runtime-provider/functions/8466731e1c4dad00.diff) |
| `block:_ZSt9terminatev@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/d9d2e770e5e35522.diff](evidence/runtime-provider/functions/d9d2e770e5e35522.diff) |
| `block:_ZdlPv@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/734446161d85a91d.diff](evidence/runtime-provider/functions/734446161d85a91d.diff) |
| `block:_Znwm@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/c4f43e9ac3dabb97.diff](evidence/runtime-provider/functions/c4f43e9ac3dabb97.diff) |
| `block:__at_fini@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/3b32f4e6ffef234b.diff](evidence/runtime-provider/functions/3b32f4e6ffef234b.diff) |
| `block:__cxa_allocate_exception@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/b18883a0750e3c45.diff](evidence/runtime-provider/functions/b18883a0750e3c45.diff) |
| `block:__cxa_atexit@plt` | added | restore-with-caller | [evidence/runtime-provider/functions/261d144aca0fbbb8.diff](evidence/runtime-provider/functions/261d144aca0fbbb8.diff) |
| `block:__cxa_begin_catch@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/4ad753a8682ce066.diff](evidence/runtime-provider/functions/4ad753a8682ce066.diff) |
| `block:__cxa_finalize@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/5da62f5c9fd03af8.diff](evidence/runtime-provider/functions/5da62f5c9fd03af8.diff) |
| `block:__cxa_free_exception@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/987966d587853e3c.diff](evidence/runtime-provider/functions/987966d587853e3c.diff) |
| `block:__cxa_throw@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/7939b0ba6f2fb15d.diff](evidence/runtime-provider/functions/7939b0ba6f2fb15d.diff) |
| `block:__deregister_frame_info@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/8dc5523a441b6224.diff](evidence/runtime-provider/functions/8dc5523a441b6224.diff) |
| `block:__errno_location@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/927836485dd999ab.diff](evidence/runtime-provider/functions/927836485dd999ab.diff) |
| `block:__register_frame_info@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/133a1f168b60a5c2.diff](evidence/runtime-provider/functions/133a1f168b60a5c2.diff) |
| `block:_exit@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/6c1b173043efcd10.diff](evidence/runtime-provider/functions/6c1b173043efcd10.diff) |
| `block:abort@plt` | added | restore-with-caller | [evidence/runtime-provider/functions/27a63d6e6f598a19.diff](evidence/runtime-provider/functions/27a63d6e6f598a19.diff) |
| `block:access@plt` | removed | restore-with-caller | [evidence/runtime-provider/functions/eb245be41d37b413.diff](evidence/runtime-provider/functions/eb245be41d37b413.diff) |
| `block:bcmp@plt` | added | restore-with-caller | [evidence/runtime-provider/functions/581b279a8b2970c1.diff](evidence/runtime-provider/functions/581b279a8b2970c1.diff) |
| `block:clock_gettime@plt` | added | restore-with-caller | [evidence/runtime-provider/functions/97f23e6c27919fa1.diff](evidence/runtime-provider/functions/97f23e6c27919fa1.diff) |
| `block:close@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/7c043866062c01ed.diff](evidence/runtime-provider/functions/7c043866062c01ed.diff) |
| `block:dladdr@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/d01a977040932b95.diff](evidence/runtime-provider/functions/d01a977040932b95.diff) |
| `block:dlclose@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/8741a3a1471dbaba.diff](evidence/runtime-provider/functions/8741a3a1471dbaba.diff) |
| `block:dlerror@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/b7a5ccb01422a4be.diff](evidence/runtime-provider/functions/b7a5ccb01422a4be.diff) |
| `block:dlopen@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/3ff36795fedc06aa.diff](evidence/runtime-provider/functions/3ff36795fedc06aa.diff) |
| `block:dlsym@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/74dc8db09c3e3dbd.diff](evidence/runtime-provider/functions/74dc8db09c3e3dbd.diff) |
| `block:dup2@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/c2c4b6d2f68e686e.diff](evidence/runtime-provider/functions/c2c4b6d2f68e686e.diff) |
| `block:fflush@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/df06fb6c24523b8b.diff](evidence/runtime-provider/functions/df06fb6c24523b8b.diff) |
| `block:fprintf@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/3a5faa32b7fdbf6d.diff](evidence/runtime-provider/functions/3a5faa32b7fdbf6d.diff) |
| `block:free@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/ed9127767958e20c.diff](evidence/runtime-provider/functions/ed9127767958e20c.diff) |
| `block:fstat@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/1c048c0d7c4a2c0b.diff](evidence/runtime-provider/functions/1c048c0d7c4a2c0b.diff) |
| `block:fwrite@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/f0ff60818162d91f.diff](evidence/runtime-provider/functions/f0ff60818162d91f.diff) |
| `block:getenv@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/7c75bf9dbb26dfbb.diff](evidence/runtime-provider/functions/7c75bf9dbb26dfbb.diff) |
| `block:getgid@plt` | removed | restore-with-caller | [evidence/runtime-provider/functions/6473f54805c1228e.diff](evidence/runtime-provider/functions/6473f54805c1228e.diff) |
| `block:getpid@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/7b44857ed6d3dc22.diff](evidence/runtime-provider/functions/7b44857ed6d3dc22.diff) |
| `block:getppid@plt` | removed | restore-with-caller | [evidence/runtime-provider/functions/606c42813a307ddc.diff](evidence/runtime-provider/functions/606c42813a307ddc.diff) |
| `block:getrlimit@plt` | removed | restore-with-caller | [evidence/runtime-provider/functions/f0cba47b40b8eee5.diff](evidence/runtime-provider/functions/f0cba47b40b8eee5.diff) |
| `block:getuid@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/e91f2d2ed49a0d15.diff](evidence/runtime-provider/functions/e91f2d2ed49a0d15.diff) |
| `block:malloc@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/329fe710d164f551.diff](evidence/runtime-provider/functions/329fe710d164f551.diff) |
| `block:memchr@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/d0ead308b8d5904e.diff](evidence/runtime-provider/functions/d0ead308b8d5904e.diff) |
| `block:memcmp@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/1e7f22f44fa3dad5.diff](evidence/runtime-provider/functions/1e7f22f44fa3dad5.diff) |
| `block:memcpy@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/100657bf3a1dd88c.diff](evidence/runtime-provider/functions/100657bf3a1dd88c.diff) |
| `block:memmove@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/2c09048d2b79e68b.diff](evidence/runtime-provider/functions/2c09048d2b79e68b.diff) |
| `block:memset@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/8be105e928130577.diff](evidence/runtime-provider/functions/8be105e928130577.diff) |
| `block:open@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/2464f032fca0d429.diff](evidence/runtime-provider/functions/2464f032fca0d429.diff) |
| `block:prctl@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/3ca200d31475e905.diff](evidence/runtime-provider/functions/3ca200d31475e905.diff) |
| `block:pread@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/5723c6060986ee9c.diff](evidence/runtime-provider/functions/5723c6060986ee9c.diff) |
| `block:read@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/e51ceecb4ff0d918.diff](evidence/runtime-provider/functions/e51ceecb4ff0d918.diff) |
| `block:realpath@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/5e57d1a72adef07e.diff](evidence/runtime-provider/functions/5e57d1a72adef07e.diff) |
| `block:setenv@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/aff64424129be87e.diff](evidence/runtime-provider/functions/aff64424129be87e.diff) |
| `block:setrlimit@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/4f6bf33f1f6c39c8.diff](evidence/runtime-provider/functions/4f6bf33f1f6c39c8.diff) |
| `block:setvbuf@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/69176a173dc68bc9.diff](evidence/runtime-provider/functions/69176a173dc68bc9.diff) |
| `block:snprintf@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/46e2fcfb713e7f7b.diff](evidence/runtime-provider/functions/46e2fcfb713e7f7b.diff) |
| `block:stat@plt` | removed | restore-with-caller | [evidence/runtime-provider/functions/c6f31a4c9e672f8c.diff](evidence/runtime-provider/functions/c6f31a4c9e672f8c.diff) |
| `block:strcmp@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/da20ffa12cded264.diff](evidence/runtime-provider/functions/da20ffa12cded264.diff) |
| `block:strerror@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/55913a35c5772d82.diff](evidence/runtime-provider/functions/55913a35c5772d82.diff) |
| `block:strlen@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/c83f5045be37ed80.diff](evidence/runtime-provider/functions/c83f5045be37ed80.diff) |
| `block:vsnprintf@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/10074f70a5788fec.diff](evidence/runtime-provider/functions/10074f70a5788fec.diff) |
| `block:westlake_art_copy_fault_message_for_abort_logging@plt` | added | restore-with-caller | [evidence/runtime-provider/functions/bc584ddb6f442e59.diff](evidence/runtime-provider/functions/bc584ddb6f442e59.diff) |
| `block:write@plt` | modified | harmless-layout | [evidence/runtime-provider/functions/255ea088f4f7e67c.diff](evidence/runtime-provider/functions/255ea088f4f7e67c.diff) |

### host `AddAppSpawnHook`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:2127`, `evidence/host/new/disassembly.txt:2154`.

### host `AddProcessMgrHook`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:2269`, `evidence/host/new/disassembly.txt:2296`.

### host `AddServerStageHook`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:1838`, `evidence/host/new/disassembly.txt:1865`.

### host `AddSpawnedProcess`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:2511`, `evidence/host/new/disassembly.txt:2538`.

### host `AppSpawnClearEnv`

The resolved diff only changes w6 source-line literals passed to HiLogPrint (1437→1442, 1433→1438). Calls, control flow and cleanup operations are unchanged after address resolution. Keep; no behavioral restoration needed beyond diagnostic text.

Evidence: `evidence/host/r155/disassembly.txt:6527`, `evidence/host/new/disassembly.txt:6567`.

### host `AppSpawnColdRun`

Added WLCGATE HiLog calls preserve the prior result and gate branches. Keep for diagnosis; logging has timing/reentrancy side effects, so not strict runtime equivalence, but no mandatory functional rollback identified.

Evidence: `evidence/host/r155/disassembly.txt:5522`, `evidence/host/new/disassembly.txt:5549`.

### host `AppSpawnColdStartApp`

Error log line numbers and source layout move; the flags/msgSize/clientId formatting failure branches remain. Relative read-only lookup table moved with its targets. No changed cold-exec argument or error return identified.

Evidence: `evidence/host/r155/disassembly.txt:5967`, `evidence/host/new/disassembly.txt:6007`.

### host `AppSpawnCreateContent`

Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.

Evidence: `evidence/host/r155/disassembly.txt:5175`, `evidence/host/new/disassembly.txt:5202`.

### host `AppSpawnDump`

Belongs to the new stdio broker: either defines a remapping wrapper or changes a call from imported vfprintf/fflush to the local wrapper. Restore with __sF and the rest of the broker.

Evidence: `evidence/host/r155/disassembly.txt:10981`, `evidence/host/new/disassembly.txt:11064`.

### host `AppSpawnHookExecute`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:1918`, `evidence/host/new/disassembly.txt:1945`.

### host `AppSpawnRun`

Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.

Evidence: `evidence/host/r155/disassembly.txt:5859`, `evidence/host/new/disassembly.txt:5899`.

### host `AppSpawningCtxTraversal`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:2995`, `evidence/host/new/disassembly.txt:3022`.

### host `CreateAppSpawnMgr`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:2353`, `evidence/host/new/disassembly.txt:2380`.

### host `DeleteAppSpawnMgr`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:2420`, `evidence/host/new/disassembly.txt:2447`.

### host `GetAppSpawnHookMgr`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:1616`, `evidence/host/new/disassembly.txt:1643`.

### host `HandleRecvMessage`

Ancillary-message bound comparison changes absolute-pointer sum to offset-versus-remaining-length arithmetic. Equivalent for valid non-wrapping ranges; malformed/overflow behavior need not match. Do not undo a bounds-check hardening change to pursue loader parity.

Evidence: `evidence/host/r155/disassembly.txt:8858`, `evidence/host/new/disassembly.txt:8898`.

### host `InitCommonEnv`

Pointer-table relocations move to the same environment-name strings; no getenv/setenv/selection instruction changes. Underlying relocation addends are resolved separately.

Evidence: `evidence/host/r155/disassembly.txt:10163`, `evidence/host/new/disassembly.txt:10246`.

### host `InstallPluginHostServices`

NEW requires lookup of WLSCPL_InheritAndroidRuntimeV1, records parent PID and callback identity, and introduces additional rejection branches. R155 never requires that symbol. Restore host/child contract as a coherent pair; retaining a candidate child while deleting required services is not parity.

Evidence: `evidence/host/r155/disassembly.txt:449`, `evidence/host/new/disassembly.txt:449`.

### host `IsAllZeros`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/host/r155/disassembly.txt:15662`.

### host `NotifyResToParent#2`

Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.

Evidence: `evidence/host/r155/disassembly.txt:5466`, `evidence/host/new/disassembly.txt:5493`.

### host `OnReceiveRequest`

Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.

Evidence: `evidence/host/r155/disassembly.txt:7814`, `evidence/host/new/disassembly.txt:7854`.

### host `OpenVerifiedFileHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/host/new/disassembly.txt:15234`.

### host `ProcessAppSpawnDumpMsg`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:3023`, `evidence/host/new/disassembly.txt:3050`.

### host `ProcessChildResponse`

Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.

Evidence: `evidence/host/r155/disassembly.txt:9471`, `evidence/host/new/disassembly.txt:9554`.

### host `ProcessMgrHookExecute`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:2207`, `evidence/host/new/disassembly.txt:2234`.

### host `ProcessSignal`

Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.

Evidence: `evidence/host/r155/disassembly.txt:6748`, `evidence/host/new/disassembly.txt:6788`.

### host `ProcessSpawnReqMsg`

Added WLCGATE HiLog calls preserve the prior result and gate branches. Keep for diagnosis; logging has timing/reentrancy side effects, so not strict runtime equivalence, but no mandatory functional rollback identified.

Evidence: `evidence/host/r155/disassembly.txt:9059`, `evidence/host/new/disassembly.txt:9100`.

### host `ProcessTerminationStatusMsg`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:3284`, `evidence/host/new/disassembly.txt:3311`.

### host `ServerStageHookExecute`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:1643`, `evidence/host/new/disassembly.txt:1670`.

### host `StartSpawnService`

Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.

Evidence: `evidence/host/r155/disassembly.txt:6319`, `evidence/host/new/disassembly.txt:6359`.

### host `TerminateSpawnedProcess`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:2648`, `evidence/host/new/disassembly.txt:2675`.

### host `TraversalSpawnedProcess`

Residual page-relative access is the same local global (g_appSpawnMgr or hook-manager storage) at a relocated address: 0x1e280→0x1ef18 or neighboring slot 0x1e278→0x1ef10. These are not changed structure-member offsets; raw ADRP and symbol tables identify the target.

Evidence: `evidence/host/r155/disassembly.txt:2483`, `evidence/host/new/disassembly.txt:2510`.

### host `VerifyBuildId`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/host/r155/disassembly.txt:15344`, `evidence/host/new/disassembly.txt:15631`.

### host `WLEI_CloseVerifiedFile`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/host/new/disassembly.txt:15495`.

### host `WLEI_OpenVerifiedFileHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/host/new/disassembly.txt:15231`.

### host `WLEI_OpenVerifiedSystemFileHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/host/new/disassembly.txt:15492`.

### host `WLEI_VerifyFileHex`

Verification delegates to a verified-open helper and closes the verified descriptor instead of the old separate checks. Do not blindly remove identity verification to emulate R155. Inspect OpenVerifiedFileHex and VerifyBuildId deltas; failed candidate identity may be a generation mismatch, not a defect in verification. Functional equivalence is not yet proven.

Evidence: `evidence/host/r155/disassembly.txt:15148`, `evidence/host/new/disassembly.txt:15512`.

### host `WLEI_VerifyLoadedSymbolHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/host/r155/disassembly.txt:15568`, `evidence/host/new/disassembly.txt:15551`.

### host `WLSha256Final`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/host/r155/disassembly.txt:15900`, `evidence/host/new/disassembly.txt:16169`.

### host `WLSha256Init`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/host/r155/disassembly.txt:15694`, `evidence/host/new/disassembly.txt:15963`.

### host `WaitChildTimeout`

Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.

Evidence: `evidence/host/r155/disassembly.txt:9782`, `evidence/host/new/disassembly.txt:9865`.

### host `WlResolveHostStdio`

Resolves host stdio through dlsym(-1, ...) and terminates with _exit(127) on lookup failure. Entire broker is absent in R155; new failure path and dependency on lookup scope. Remove as one stdio-interposition unit when reproducing R155.

Evidence: `evidence/host/new/disassembly.txt:16373`.

### host `_ZN12_GLOBAL__N_126ResolveCurrentThreadRegionEPvPK20WltgProcessBindingV1PK18WltgThreadTicketV1P15WltgOwnedRegion`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/host/r155/disassembly.txt:14509`, `evidence/host/new/disassembly.txt:14592`.

### host `_ZN9appspawnx36WestLakeNativeCompatGetAuditSnapshotEP19WlncAuditSnapshotV1`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/host/r155/disassembly.txt:13868`, `evidence/host/new/disassembly.txt:13951`.

### host `_ZN9appspawnx37WestLakeNativeCompatPrepareMainThreadEPK21WlncProcessIdentityV1`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/host/r155/disassembly.txt:13500`, `evidence/host/new/disassembly.txt:13583`.

### host `_ZN9appspawnx40WestLakeNativeCompatPrepareParentRuntimeEPK20WlncParentIdentityV1`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/host/r155/disassembly.txt:13168`, `evidence/host/new/disassembly.txt:13251`.

### host `__emutls_unregister_key`

R155 starts with bti c; NEW omits it. Remaining instructions match. Preserve the landing-pad hardening in rebuild flags; no GNU_PROPERTY BTI requirement was observed, so device fault causality is unverified.

Evidence: `evidence/host/r155/disassembly.txt:16057`, `evidence/host/new/disassembly.txt:16665`.

### host `fflush`

New wrapper remaps Bionic stream slots, handles NULL, and branches through g_host_fflush. R155 uses an imported PLT entry. Restore together with __sF and the other five wrappers, not just this export.

Evidence: `evidence/host/new/disassembly.txt:16626`.

### host `fprintf`

New variadic adapter invokes the local vfprintf broker. Changes symbol resolution and logging path for dependencies; remove with broker for an exact R155 host control.

Evidence: `evidence/host/new/disassembly.txt:16443`.

### host `fputc`

Belongs to the new stdio broker: either defines a remapping wrapper or changes a call from imported vfprintf/fflush to the local wrapper. Restore with __sF and the rest of the broker.

Evidence: `evidence/host/new/disassembly.txt:16588`.

### host `fputs`

Belongs to the new stdio broker: either defines a remapping wrapper or changes a call from imported vfprintf/fflush to the local wrapper. Restore with __sF and the rest of the broker.

Evidence: `evidence/host/new/disassembly.txt:16550`.

### host `fwrite`

New wrapper rewrites the stream argument before indirect dispatch. R155 has no such definition. ABI-visible behavior differs even if many non-Bionic calls still pass through.

Evidence: `evidence/host/new/disassembly.txt:16506`.

### host `main`

Only HiLogPrint source-line arguments differ; surrounding calls and control flow match.

Evidence: `evidence/host/r155/disassembly.txt:126`, `evidence/host/new/disassembly.txt:126`.

### host `vfprintf`

New globally exported wrapper calls pthread_once, recognizes __sF slots at strides 152/304, remaps FILE pointers and indirectly calls the resolved libc function. R155 imports this symbol. This changes binding and FILE ownership behavior, not a harmless rename.

Evidence: `evidence/host/new/disassembly.txt:16326`.

### child `AbsoluteCanonicalForm`

Part of changed sealed provider, namespace admission and caller sequence. V1 direct resolver is replaced by V2 verified artifact acquisition and A06→A02; restore the complete R155 loader/caller contract. Error diagnostics and identity hashes must match that chosen generation.

Evidence: `evidence/child/r155/disassembly.txt:178`.

### child `AllocatorDomainRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1252`.

### child `BuildIdentity`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:5241`.

### child `BuildRequestKey`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:3512`.

### child `BytesNonzero`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4781`.

### child `CandidateValid`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/r155/disassembly.txt:1335`, `evidence/child/new/disassembly.txt:6300`.

### child `CompleteStockChildReply`

NEW keeps stderr write markers but removes the optional dlsym(HiLogPrint) mirror. Reply write/close/error handling remains; logging visibility and loader re-entry change. No reason to reintroduce the optional mirror for functional parity.

Evidence: `evidence/child/r155/disassembly.txt:3329`, `evidence/child/new/disassembly.txt:8213`.

### child `CppRuntimeDomainRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1262`.

### child `CurrentChildThreadId`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:9955`.

### child `DigestEqual`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:5486`.

### child `DrainHookOwner`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/new/disassembly.txt:9944`.

### child `InvalidateHookOwner`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/new/disassembly.txt:9949`.

### child `InvokeProviderA06ThenA02`

New staged receipt-generation and provider prerequisite/handoff path replaces InvokeProviderChildEntryWithResolver. Calls, transition validation, deadlines/identity inputs and failure returns are new runtime behavior.

Evidence: `evidence/child/new/disassembly.txt:9480`.

### child `InvokeProviderChildEntryWithResolver`

Part of changed sealed provider, namespace admission and caller sequence. V1 direct resolver is replaced by V2 verified artifact acquisition and A06→A02; restore the complete R155 loader/caller contract. Error diagnostics and identity hashes must match that chosen generation.

Evidence: `evidence/child/r155/disassembly.txt:3782`.

### child `IsAllZeros`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/child/r155/disassembly.txt:4420`.

### child `IsInheritedPreloadedProvider`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:1997`.

### child `LoadSealedProviderAfterHooks`

Manifest version comparison changes 1 to 2, extra production identity callback checks appear, and the load path grows from 208 to 588 instructions. Boot-bound identity, receipt and A06/A02 admission are runtime gating changes. Revert the whole loader/provider protocol only as a generation-consistent control.

Evidence: `evidence/child/r155/disassembly.txt:3405`, `evidence/child/new/disassembly.txt:8265`.

### child `MapsState`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:2048`.

### child `OpenVerifiedFileHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/child/new/disassembly.txt:10353`.

### child `P0AllocatorDomainRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6217`.

### child `P0CppRuntimeDomainRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6227`.

### child `P0SignalRouteRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6212`.

### child `P0ThreadCreateRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6182`.

### child `P0ThreadDetachRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6192`.

### child `P0ThreadJoinRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6187`.

### child `P0ThreadSelfRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6197`.

### child `P0TlsGetSetRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6207`.

### child `P0TlsKeyCreateRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6202`.

### child `P0UnwindDomainRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/new/disassembly.txt:6222`.

### child `PublishChildHookTable`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/r155/disassembly.txt:3196`, `evidence/child/new/disassembly.txt:8076`.

### child `RealIsMapped`

Part of changed sealed provider, namespace admission and caller sequence. V1 direct resolver is replaced by V2 verified artifact acquisition and A06→A02; restore the complete R155 loader/caller contract. Error diagnostics and identity hashes must match that chosen generation.

Evidence: `evidence/child/r155/disassembly.txt:918`.

### child `RealOpenLocalNow`

Part of changed sealed provider, namespace admission and caller sequence. V1 direct resolver is replaced by V2 verified artifact acquisition and A06→A02; restore the complete R155 loader/caller contract. Error diagnostics and identity hashes must match that chosen generation.

Evidence: `evidence/child/r155/disassembly.txt:986`.

### child `RequestKey`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4409`.

### child `RevokeChildHookTable`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/r155/disassembly.txt:3302`, `evidence/child/new/disassembly.txt:8193`.

### child `RevokeHookOwner`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/new/disassembly.txt:9938`.

### child `SignalRouteRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1247`.

### child `SourceFactsValid`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:5098`.

### child `ThreadCreateRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1217`.

### child `ThreadDetachRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1227`.

### child `ThreadJoinRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1222`.

### child `ThreadSelfRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1232`.

### child `TlsGetSetRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1242`.

### child `TlsKeyCreateRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1237`.

### child `UnwindDomainRejected`

Old rejector and P0-prefixed replacement have identical full instruction bodies and return values. Callback publication policy is reviewed separately.

Evidence: `evidence/child/r155/disassembly.txt:1257`.

### child `VerifyBuildId`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/child/r155/disassembly.txt:4092`, `evidence/child/new/disassembly.txt:10750`.

### child `VisitClosure`

Graph DFS remains structurally similar, but artifact stride changes 376→400, manifest array slot 32→64 and edge slots 244/248→248/252. This consumes a different V2 schema; restore matching producer/consumer layouts together, not numeric offsets alone.

Evidence: `evidence/child/r155/disassembly.txt:1044`, `evidence/child/new/disassembly.txt:2147`.

### child `WLASC_InstallStockHostServicesV1`

Part of changed sealed provider, namespace admission and caller sequence. V1 direct resolver is replaced by V2 verified artifact acquisition and A06→A02; restore the complete R155 loader/caller contract. Error diagnostics and identity hashes must match that chosen generation.

Evidence: `evidence/child/r155/disassembly.txt:2289`, `evidence/child/new/disassembly.txt:7242`.

### child `WLASC_ReceiptChildTail`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/child/r155/disassembly.txt:69`, `evidence/child/new/disassembly.txt:69`.

### child `WLASC_ReceiptConsume`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/child/r155/disassembly.txt:98`, `evidence/child/new/disassembly.txt:98`.

### child `WLASC_ReceiptParentTail`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/child/r155/disassembly.txt:7`, `evidence/child/new/disassembly.txt:7`.

### child `WLEI_CloseVerifiedFile`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/child/new/disassembly.txt:10614`.

### child `WLEI_OpenVerifiedFileHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/child/new/disassembly.txt:10350`.

### child `WLEI_OpenVerifiedSystemFileHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/child/new/disassembly.txt:10611`.

### child `WLEI_VerifyFileHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/child/r155/disassembly.txt:3896`, `evidence/child/new/disassembly.txt:10631`.

### child `WLEI_VerifyLoadedSymbolHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/child/r155/disassembly.txt:4326`, `evidence/child/new/disassembly.txt:10670`.

### child `WLSCPL_GetLastArtifactIdentityDetail`

Part of changed sealed provider, namespace admission and caller sequence. V1 direct resolver is replaced by V2 verified artifact acquisition and A06→A02; restore the complete R155 loader/caller contract. Error diagnostics and identity hashes must match that chosen generation.

Evidence: `evidence/child/new/disassembly.txt:205`.

### child `WLSCPL_InheritAndroidRuntimeV1`

NEW calls dlns_inherit, then dlopen_ns(flags 258) and caches the Android runtime handle; absent in R155. This affects namespace visibility and load lifetime. Restore with the host installer and namespace callbacks, not by deleting a symbol alone.

Evidence: `evidence/child/new/disassembly.txt:168`.

### child `WLSCPL_LoadSealedProvider`

Part of changed sealed provider, namespace admission and caller sequence. V1 direct resolver is replaced by V2 verified artifact acquisition and A06→A02; restore the complete R155 loader/caller contract. Error diagnostics and identity hashes must match that chosen generation.

Evidence: `evidence/child/r155/disassembly.txt:240`, `evidence/child/new/disassembly.txt:210`.

### child `WLSCPL_OpenPreparedNamespace`

R155 validates absolute canonical /system/android/lib64/ path and flags then uses dlopen. NEW tests nonempty input and prepared state then calls dlopen_ns in g_sealed_namespace. Search scope, admission conditions and load grouping change.

Evidence: `evidence/child/r155/disassembly.txt:144`, `evidence/child/new/disassembly.txt:144`.

### child `WLSha256Final`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/child/r155/disassembly.txt:4661`, `evidence/child/new/disassembly.txt:11304`.

### child `WLSha256Init`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/child/r155/disassembly.txt:4452`, `evidence/child/new/disassembly.txt:11095`.

### child `WestlakeChildBypassGuard`

Only residual page-relative access changes; old 0x1a000+1544 and new 0x24000+464 address g_stock_host_services+0x98 in both. Guard tests and callback slots match, unlike the separate install/protocol changes.

Evidence: `evidence/child/r155/disassembly.txt:2603`, `evidence/child/new/disassembly.txt:7556`.

### child `WestlakeRunAndroidChild`

Part of changed sealed provider, namespace admission and caller sequence. V1 direct resolver is replaced by V2 verified artifact acquisition and A06→A02; restore the complete R155 loader/caller contract. Error diagnostics and identity hashes must match that chosen generation.

Evidence: `evidence/child/r155/disassembly.txt:2800`, `evidence/child/new/disassembly.txt:7753`.

### child `WlascGateMarker`

NEW keeps stderr write markers but removes the optional dlsym(HiLogPrint) mirror. Reply write/close/error handling remains; logging visibility and loader re-entry change. No reason to reintroduce the optional mirror for functional parity.

Evidence: `evidence/child/r155/disassembly.txt:3153`, `evidence/child/new/disassembly.txt:8062`.

### child `WlascGateMarkerValue`

NEW keeps stderr write markers but removes the optional dlsym(HiLogPrint) mirror. Reply write/close/error handling remains; logging visibility and loader re-entry change. No reason to reintroduce the optional mirror for functional parity.

Evidence: `evidence/child/r155/disassembly.txt:3746`, `evidence/child/new/disassembly.txt:8895`.

### child `WlgrIfAcquire`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:3038`.

### child `WlgrIfChildReadSeal`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4137`.

### child `WlgrIfDigestMetadata`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:2326`.

### child `WlgrIfDigestStockReceipt`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4259`.

### child `WlgrIfGetBuildGeneratedMetadata`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:11460`.

### child `WlgrIfParentSeal`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4599`.

### child `WlgrIfParseBootId`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:2207`.

### child `WlgrIfProduceHookSchemaDigest`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4561`.

### child `WlgrIfProductionContextInit`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4619`.

### child `WlgrIfProductionOps`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4911`.

### child `WlgrIfProductionRandom`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4064`.

### child `WlgrIfProductionReadBootId`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:3916`.

### child `WlgrIfProductionReadHook`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4533`.

### child `WlgrIfProductionReadManifest`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4099`.

### child `WlgrIfProductionReadMetadata`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4112`.

### child `WlgrIfProductionReadProcess`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:3965`.

### child `WlgrIfProductionReadReceipt`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4286`.

### child `WlgrIfSerializeStockReceipt`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4157`.

### child `WlgrIfValidateHook`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:2934`.

### child `WlgrIfValidateMetadata`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:2447`.

### child `WlgrIpBuild`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:4959`.

### child `WlgrIpGetIdentity`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:5930`.

### child `WlgrIpValidate`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:5848`.

### child `westlake_child_hook_table_v1_drain`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/r155/disassembly.txt:1733`, `evidence/child/new/disassembly.txt:6676`.

### child `westlake_child_hook_table_v1_invalidate`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/r155/disassembly.txt:1815`, `evidence/child/new/disassembly.txt:6769`.

### child `westlake_child_hook_table_v1_prepare_candidate`

Candidate preparation now participates in callback-owner lifetime management and a new prepare_candidate_with_callbacks entry. Receipt publication/revocation semantics changed. Keep the R155 lifecycle unless the new owner protocol is intentionally adopted and tested as a complete set.

Evidence: `evidence/child/r155/disassembly.txt:1105`, `evidence/child/new/disassembly.txt:6177`.

### child `westlake_child_hook_table_v1_prepare_candidate_with_callbacks`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/new/disassembly.txt:6054`.

### child `westlake_child_hook_table_v1_revoke`

Hook table now carries callback-owner validation and drain/revoke/invalidate behavior. Same-size/similar signatures do not prove lifecycle equivalence. Keep an internally consistent ownership scheme; restore R155 lifecycle as a unit for parity.

Evidence: `evidence/child/r155/disassembly.txt:1647`, `evidence/child/new/disassembly.txt:6601`.

### child `wlgr_v2_a02_bundle_valid`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:9962`.

### child `wlgr_v2_bytes_zero`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:2909`.

### child `wlgr_v2_expected_owner`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:10127`.

### child `wlgr_v2_identity_equal`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:5517`.

### child `wlgr_v2_identity_equal#2`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:9149`.

### child `wlgr_v2_identity_valid`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:5299`.

### child `wlgr_v2_identity_valid#2`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:8962`.

### child `wlgr_v2_receipt_valid`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:10138`.

### child `wlgr_v2_runtime_key_equal`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:3633`.

### child `wlgr_v2_runtime_key_valid`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:5970`.

### child `wlgr_v2_runtime_key_valid#2`

New V2 identity/admission helper: contributes boot/process identity, digest/receipt validation, or loaded-file state to the new gate. Required by the changed acquisition protocol; absent in R155. Revert only with its owning V2 protocol, not to bypass a single check.

Evidence: `evidence/child/new/disassembly.txt:9854`.

### runtime-provider `IsAllZeros`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:8790`.

### runtime-provider `OpenVerifiedFileHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/runtime-provider/new/disassembly.txt:10177`.

### runtime-provider `VerifyBuildId`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:8472`, `evidence/runtime-provider/new/disassembly.txt:10554`.

### runtime-provider `WLAR_EnterAndroidAfterStockSpecialization`

R155 drives constructor/VM/JNI/main sequence directly. NEW validates a previously prepared request and A02 bundle, compares persisted identity/receipt data, then commits A02 handoff. Same exported name now has different preconditions and sequencing.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:5890`, `evidence/runtime-provider/new/disassembly.txt:7545`.

### runtime-provider `WLAR_GetRuntimeIdentity`

Same output layout and null check; NEW vector-copies the 32-byte digest and emits a different generation token. Preserve identity values matching the deployed generation; do not paste R155 digest constants into NEW code.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:5699`, `evidence/runtime-provider/new/disassembly.txt:7464`.

### runtime-provider `WLAR_HostServicesGetNamespaceCallbacks`

R155 getter has two outputs (create namespaces, open namespace); NEW adds open_sealed_exact as the first of three outputs. Restore declarations and callers together with installer-time sealed-open registration; public service fields +112/+120 remain mandatory nonzero in both artifacts.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7952`, `evidence/runtime-provider/new/disassembly.txt:9854`.

### runtime-provider `WLAR_HostServicesIsInstalled`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7530`.

### runtime-provider `WLAR_InstallHostRuntimeServices`

R155 calls WLNL_InstallSealedOpenV1(services->open_sealed_exact at +104) before publishing ADMISSION_READY. NEW moves the call into Constructors. Restore installer-time binding and fail-closed state publication, not a duplicate call.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:5850`, `evidence/runtime-provider/new/disassembly.txt:7485`.

### runtime-provider `WLAR_LoaderPhaseFail`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:8147`.

### runtime-provider `WLAR_PrepareA02PrerequisiteBundleV2`

New public entry validates V2 manifest/load result, process identity and prerequisite transitions before preparation. It is part of the new A06/A02 protocol; not an ABI-neutral helper.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8310`.

### runtime-provider `WLEI_VerifyFileHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:8276`, `evidence/runtime-provider/new/disassembly.txt:10435`.

### runtime-provider `WLEI_VerifyLoadedSymbolHex`

Verified-open/ELF identity family: NEW accepts 16/20-byte build IDs, retains an open descriptor, checks final device/inode/size, and removes the old fixed-length zero helper. Runtime admission changes, but not a justified R155 rollback target. Keep full expected-hash verification; test any compatibility failure separately.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:8696`, `evidence/runtime-provider/new/disassembly.txt:10474`.

### runtime-provider `WLSha256Final`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:9028`, `evidence/runtime-provider/new/disassembly.txt:11092`.

### runtime-provider `WLSha256Init`

Only .rodata load offsets differ; the exact 1/4/8/16 bytes loaded at every differing operand were compared and match. Numeric structure offsets were not erased.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:8822`, `evidence/runtime-provider/new/disassembly.txt:10886`.

### runtime-provider `_GLOBAL__sub_I_westlake_android_runtime_provider.cpp`

New constructor zeroes/initializes global Context and registers its destructor through __cxa_atexit. It is not an empty compiler stub. It supports the new protocol; remove only if reverting that stateful protocol, not as an isolated constructor deletion.

Evidence: `evidence/runtime-provider/new/disassembly.txt:9307`.

### runtime-provider `_ZL21wlgr_v2_receipt_validPK33westlake_runtime_stage_receipt_v2`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:7248`.

### runtime-provider `_ZL22wlgr_v2_expected_ownerj`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:9181`.

### runtime-provider `_ZL22wlgr_v2_identity_equalPK31westlake_generation_identity_v2S1_`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:6917`.

### runtime-provider `_ZL22wlgr_v2_identity_validPK31westlake_generation_identity_v2`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8742`.

### runtime-provider `_ZL24wlgr_v2_a02_bundle_validPK35westlake_a02_prerequisite_bundle_v2`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:6640`.

### runtime-provider `_ZL25wlgr_v2_runtime_key_validPK32westlake_runtime_instance_key_v2`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:9192`.

### runtime-provider `_ZN12_GLOBAL__N_110InvalidateEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8249`.

### runtime-provider `_ZN12_GLOBAL__N_111VerifyReadyEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:9276`.

### runtime-provider `_ZN12_GLOBAL__N_112ConstructorsEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8084`.

### runtime-provider `_ZN12_GLOBAL__N_112RequestValidEPK26WlascAndroidChildRequestV1PK24WlascStockStageReceiptV1`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:7813`.

### runtime-provider `_ZN12_GLOBAL__N_113CreateChildVmEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7332`.

### runtime-provider `_ZN12_GLOBAL__N_114EnterChildMainEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7358`.

### runtime-provider `_ZN12_GLOBAL__N_115DrainChildCallsEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7375`.

### runtime-provider `_ZN12_GLOBAL__N_116CompleteChildJniEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7341`.

### runtime-provider `_ZN12_GLOBAL__N_116TranslateRequestERK26WlascAndroidChildRequestV1`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:6574`.

### runtime-provider `_ZN12_GLOBAL__N_117FillGenerationShaEPh`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:5781`.

### runtime-provider `_ZN12_GLOBAL__N_118AuditSnapshotValidERK19WlncAuditSnapshotV1m`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:6477`.

### runtime-provider `_ZN12_GLOBAL__N_119CommitAuditSnapshotEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8040`.

### runtime-provider `_ZN12_GLOBAL__N_120CaptureAuditSnapshotEPvPN19wlar_child_sequence21LosslessAuditSnapshotE`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:7889`.

### runtime-provider `_ZN12_GLOBAL__N_120LoaderAdmissionValidEPK16WlscplManifestV2PK18WlscplLoadResultV2`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8645`.

### runtime-provider `_ZN12_GLOBAL__N_120RevokeChildAdmissionEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7370`.

### runtime-provider `_ZN12_GLOBAL__N_121ConstructChildRuntimeEPv`

Removed R155 callback contains setenv calls, stack-limit setup and runtime construction. Deleted environment literals include ICU/TZDATA/I18N/DEX2OAT settings. NEW Constructors callback must be assessed with its callers; three-file evidence does not prove equivalent setup occurs elsewhere.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:6918`.

### runtime-provider `_ZN12_GLOBAL__N_122OpenNamespaceFromStockEP12Dl_namespacePKci`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7427`.

### runtime-provider `_ZN12_GLOBAL__N_123VerifyLoaderThreadReadyEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7388`.

### runtime-provider `_ZN12_GLOBAL__N_124InvalidateChildAdmissionEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7378`.

### runtime-provider `_ZN12_GLOBAL__N_12VmEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8213`.

### runtime-provider `_ZN12_GLOBAL__N_135CreateConfiguredNamespacesFromStockEP12Dl_namespacePKcS3_S3_S3_S3_PK13WlpbHostOpsV1PPvS1_S3_S3_S3_`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7415`.

### runtime-provider `_ZN12_GLOBAL__N_13JniEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8221`.

### runtime-provider `_ZN12_GLOBAL__N_13NowEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8259`.

### runtime-provider `_ZN12_GLOBAL__N_13TidEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:7880`.

### runtime-provider `_ZN12_GLOBAL__N_15DrainEPv`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8240`.

### runtime-provider `_ZN12_GLOBAL__N_16DigestEPvPKvmPh`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8278`.

### runtime-provider `_ZN12_GLOBAL__N_16RevokeEPvi`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8230`.

### runtime-provider `_ZN12_GLOBAL__N_17ContextD2Ev`

New abort logging/termination or global Context destructor participates in changed VM options and lifecycle. Not an inert name change; restore with the owning VM/global-state change.

Evidence: `evidence/runtime-provider/new/disassembly.txt:7460`.

### runtime-provider `_ZN12_GLOBAL__N_19TranslateERK26WlascAndroidChildRequestV1`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:8929`.

### runtime-provider `_ZN19wlar_child_sequence16CommitA02HandoffEPNS_6LedgerERKNS_10OperationsEP33westlake_runtime_stage_receipt_v2`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:6805`.

### runtime-provider `_ZN19wlar_child_sequence3RunEPNS_6LedgerERK31westlake_generation_identity_v2PK33westlake_runtime_stage_receipt_v2jRKNS_10OperationsEP35westlake_a02_prerequisite_bundle_v2PS5_`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:5811`.

### runtime-provider `_ZN19wlar_child_sequence3RunEPNS_6LedgerERKNS_9AdmissionEmRKNS_10OperationsE`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:5575`.

### runtime-provider `_ZN19wlar_child_sequence4FailEPNS_6LedgerERKNS_10OperationsEi`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:5545`.

### runtime-provider `_ZN19wlar_child_sequenceL18AuditSnapshotValidERKNS_21LosslessAuditSnapshotEm`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:6393`.

### runtime-provider `_ZN19wlar_child_sequenceL18FillSuccessReceiptERKNS_10OperationsERK31westlake_generation_identity_v2jmmPKvmP33westlake_runtime_stage_receipt_v2`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:6501`.

### runtime-provider `_ZN19wlar_child_sequenceL4FailEPNS_6LedgerERKNS_10OperationsEjiiPKhP33westlake_runtime_stage_receipt_v2`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:6269`.

### runtime-provider `_ZN19wlar_child_sequenceL4HashERKNS_10OperationsEPKvmPh`

Provider callback/sequence implementation belongs to the changed constructor→VM→JNI→main versus V2 prepare/commit lifecycle. Added/removed callbacks are not independent harmless renames: context fields, identity/receipt state and call ordering differ. Restore its R155 counterpart as part of the provider protocol, preserving verification.

Evidence: `evidence/runtime-provider/new/disassembly.txt:6230`.

### runtime-provider `_ZN8westlake3jni18AttachStatusStringENS0_12AttachStatusE`

Only the address of the read-only relative string lookup table changes. Return-string choices and bounds logic remain the same; no ABI change.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:3695`, `evidence/runtime-provider/new/disassembly.txt:3961`.

### runtime-provider `_ZN9appspawnx16AppSpawnXRuntime7preloadEv`

NEW moves registerNativeMethods and cacheJavaReferences from startVm into preload, preceded by VerifyLoadedAdapterBridge. Restore the R155 phase boundary together with startVm; retain exact adapter-bridge verification. Typeface behavior already exists in R155 and needs no restoration.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:2620`, `evidence/runtime-provider/new/disassembly.txt:2835`.

### runtime-provider `_ZN9appspawnx16AppSpawnXRuntime7startVmEb`

Both artifacts already implement startVm(bool) and non-zygote mode. NEW adds the abort VM option and Java System.loadLibrary(javacore), and moves registerNativeMethods/cacheJavaReferences out to preload. Restore R155 ordering and dependencies as a unit; retain startVm(false) for the specialized child. R155 calls are at disassembly lines 1261/1264/1267.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:232`, `evidence/runtime-provider/new/disassembly.txt:232`.

### runtime-provider `_ZN9appspawnx9ChildMain27runAfterStockSpecializationERKNS_8SpawnMsgEPNS_16AppSpawnXRuntimeE`

Correct R155 80c9aee0 already has the Typeface nativeWarmUpCache no-op, omits zygote post-fork calls and defers adapter initialization. Only one unresolved rodata displacement differs; both resolve to nativeWarmUpCache (provider-focused-evidence.json). Withdraw the earlier behavioral rollback recommendation.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:4078`, `evidence/runtime-provider/new/disassembly.txt:4344`.

### runtime-provider `_ZN9appspawnxL23logArtAbortAndTerminateEv`

New abort logging/termination or global Context destructor participates in changed VM options and lifecycle. Not an inert name change; restore with the owning VM/global-state change.

Evidence: `evidence/runtime-provider/new/disassembly.txt:1593`.

### runtime-provider `_ZNKSt3__h6vectorIiNS_9allocatorIiEEE20__throw_length_errorB6v15004Ev`

Removed local vector throw helper reflects changed template instantiation; no exported ABI entry removed. Runtime allocation/error paths are assessed with startVm/provider sequence.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:7381`.

### runtime-provider `__emutls_unregister_key`

R155 starts with bti c; NEW omits it. Remaining instructions match. Preserve the landing-pad hardening in rebuild flags; no GNU_PROPERTY BTI requirement was observed, so device fault causality is unverified.

Evidence: `evidence/runtime-provider/r155/disassembly.txt:9185`, `evidence/runtime-provider/new/disassembly.txt:11249`.

