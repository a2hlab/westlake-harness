# Binder IPC observed: `com.keylesspalace.tusky`

Scenario: cold start to the login screen, 45 s. Device: Husk LineageOS 23 (Android 16, BP4A.251205.006, arm64) under QEMU TCG in an OpenHarmony 6.1 emulator app.

100 Java binder calls, 64 distinct AIDL methods, 18 services (11 with an app frame on some call; the rest the framework called on the app's behalf).

| Service | OH analog | Calls | App frame | Methods |
|---|---|---:|---|---|
| `activity_task` | ability_runtime (AMS) | 19 | yes | IActivityClientController.activityDestroyed, IActivityClientController.activityIdle, IActivityClientController.activityPaused, IActivityClientController.activityResumed, IActivityClientController.activityTopResumedStateLost, IActivityClientController.finishActivity, IActivityClientController.getDisplayId, IActivityClientController.getTaskForActivity, IActivityClientController.reportSizeConfigurations, IActivityClientController.setTaskDescription, IActivityTaskManager.getActivityClientController, IActivityTaskManager.startActivity |
| `package` | bundle_framework (BMS) | 19 | yes | IPackageManager.getActivityInfo, IPackageManager.getApplicationInfo, IPackageManager.getComponentEnabledSetting, IPackageManager.getPackageInfo, IPackageManager.getPackagesForUid, IPackageManager.getProviderInfo, IPackageManager.getSdkSandboxPackageName, IPackageManager.getServiceInfo, IPackageManager.notifyDexLoad, IPackageManager.queryIntentActivities, IPackageManager.queryIntentContentProviders, IPackageManager.setComponentEnabledSetting |
| `activity` | ability_runtime (AMS) | 14 | yes | IActivityManager.checkPermissionForDevice, IActivityManager.finishAttachApplication, IActivityManager.getContentProvider, IActivityManager.getHistoricalProcessExitReasons, IActivityManager.getIntentSenderWithFeature, IActivityManager.publishContentProviders, IActivityManager.reportOptimizationInfo, IActivityManager.reportStartInfoViewTimestamps, IActivityManager.setRenderThread, IActivityManager.waitForNetworkStateUpdate |
| `servicemanager` |  | 8 | yes | IServiceManager.checkService2 |
| `settings-provider` |  | 8 | yes | IContentProvider.call |
| `window` | window_manager | 7 | framework only | IWindowManager.getCurrentAnimatorScale, IWindowManager.hasNavigationBar, IWindowManager.openSession, IWindowSession.addToDisplayAsUser, IWindowSession.finishDrawing, IWindowSession.relayout, IWindowSession.setOnBackInvokedCallbackInfo |
| `uimode` | display / theme | 5 | framework only | IUiModeManager.addCallback, IUiModeManager.getContrast, IUiModeManager.getForceInvertState |
| `accessibility` |  | 4 | framework only | IAccessibilityManager.addClient, IAccessibilityManager.getFocusColor, IAccessibilityManager.getFocusStrokeWidth, IAccessibilityManager.getRecommendedTimeoutMillis |
| `display` | display_manager | 3 | framework only | IDisplayManager.getDisplayIds, IDisplayManager.registerCallbackWithEventMask |
| `jobscheduler` | resourceschedule/work_scheduler | 2 | yes | IJobScheduler.getAllPendingJobsInNamespace, IJobScheduler.schedule |
| `mount` |  | 2 | yes | IStorageManager.getVolumeList, IStorageManager.mkdirs |
| `notification` | notification (ANS) | 2 | yes | INotificationManager.createNotificationChannels, INotificationManager.getNotificationChannels |
| `voiceinteraction` |  | 2 | yes | IVoiceInteractionManagerService.notifyActivityEventChanged |
| `connectivity` | netmanager (NetConnManager) | 1 | framework only | IConnectivityManager.getProxyForNetwork |
| `graphicsstats` |  | 1 | framework only | IGraphicsStats.requestBufferForProcess |
| `input_method` | inputmethod_framework | 1 | yes | IInputMethodManager.addClient |
| `protolog_configuration` |  | 1 | framework only | IProtoLogConfigurationService.registerClient |
| `user` | account/os_account | 1 | yes | IUserManager.isUserUnlockingOrUnlocked |

## Against the static gap map

13 of 33 rows reached on this run (27 `svc:` + 6 `pm:call:`); 6 services used that no row names.

Reached: `pm:call:getComponentEnabledSetting`, `pm:call:queryIntentContentProviders`, `pm:call:setComponentEnabledSetting`, `svc:accessibility`, `svc:activity`, `svc:connectivity`, `svc:display`, `svc:input_method`, `svc:jobscheduler`, `svc:notification`, `svc:uimode`, `svc:user`, `svc:window`

Not reached on this run: `pm:call:queryBroadcastReceivers`, `pm:call:queryIntentActivityOptions`, `pm:call:queryIntentServices`, `svc:alarm`, `svc:appops`, `svc:audio`, `svc:clipboard`, `svc:download`, `svc:locale`, `svc:location`, `svc:media_metrics`, `svc:phone`, `svc:power`, `svc:search`, `svc:vibrator`, `svc:wifi`

Not observable by a Java IPC trace (binderless or native client): `svc:captioning`, `svc:layout_inflater`, `svc:sensor`, `svc:textclassification`

Used but not in the map (framework-implied): `activity_task`, `graphicsstats`, `mount`, `protolog_configuration`, `settings-provider`, `voiceinteraction`
