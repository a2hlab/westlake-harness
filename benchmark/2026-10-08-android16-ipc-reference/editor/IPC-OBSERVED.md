# Binder IPC observed: `org.billthefarmer.editor`

Scenario: cold start to the editor screen, 15 s. Device: Husk LineageOS 23 (Android 16, BP4A.251205.006, arm64) under QEMU TCG in an OpenHarmony 6.1 emulator app.

79 Java binder calls, 50 distinct AIDL methods, 18 services (13 with an app frame on some call; the rest the framework called on the app's behalf).

| Service | OH analog | Calls | App frame | Methods |
|---|---|---:|---|---|
| `activity` | ability_runtime (AMS) | 13 | yes | IActivityManager.checkPermissionForDevice, IActivityManager.finishAttachApplication, IActivityManager.getContentProvider, IActivityManager.publishContentProviders, IActivityManager.reportOptimizationInfo, IActivityManager.reportStartInfoViewTimestamps, IActivityManager.setRenderThread |
| `window` | window_manager | 11 | yes | IWindowManager.getCurrentAnimatorScale, IWindowManager.hasNavigationBar, IWindowManager.openSession, IWindowSession.addToDisplayAsUser, IWindowSession.finishDrawing, IWindowSession.relayout, IWindowSession.setOnBackInvokedCallbackInfo |
| `servicemanager` |  | 9 | yes | IServiceManager.checkService2 |
| `package` | bundle_framework (BMS) | 8 | framework only | IPackageManager.getApplicationInfo, IPackageManager.getPackageInfo, IPackageManager.getPackagesForUid, IPackageManager.getSdkSandboxPackageName, IPackageManager.notifyDexLoad, IPackageManager.queryIntentActivities, IPackageManager.resolveContentProvider |
| `activity_task` | ability_runtime (AMS) | 7 | yes | IActivityClientController.activityIdle, IActivityClientController.activityResumed, IActivityClientController.getDisplayId, IActivityClientController.reportSizeConfigurations, IActivityClientController.setTaskDescription, IActivityTaskManager.getActivityClientController |
| `settings-provider` |  | 6 | yes | IContentProvider.call |
| `uimode` | display / theme | 5 | yes | IUiModeManager.addCallback, IUiModeManager.getContrast, IUiModeManager.getForceInvertState |
| `accessibility` |  | 4 | yes | IAccessibilityManager.addClient, IAccessibilityManager.getFocusColor, IAccessibilityManager.getFocusStrokeWidth, IAccessibilityManager.getRecommendedTimeoutMillis |
| `input` |  | 4 | framework only | IInputManager.getInputDevice, IInputManager.getInputDeviceIds, IInputManager.getVelocityTrackerStrategy, IInputManager.registerInputDevicesChangedListener |
| `display` | display_manager | 3 | yes | IDisplayManager.getDisplayIds, IDisplayManager.registerCallbackWithEventMask |
| `voiceinteraction` |  | 2 | framework only | IVoiceInteractionManagerService.notifyActivityEventChanged |
| `appops` |  | 1 | yes | IAppOpsService.checkOperationRawForDevice |
| `connectivity` | netmanager (NetConnManager) | 1 | framework only | IConnectivityManager.getProxyForNetwork |
| `graphicsstats` |  | 1 | yes | IGraphicsStats.requestBufferForProcess |
| `input_method` | inputmethod_framework | 1 | yes | IInputMethodManager.addClient |
| `mount` |  | 1 | yes | IStorageManager.getVolumeList |
| `protolog_configuration` |  | 1 | framework only | IProtoLogConfigurationService.registerClient |
| `user` | account/os_account | 1 | yes | IUserManager.isUserUnlockingOrUnlocked |
