/*
 * ActivityClientControllerAdapter.java
 *
 * Adapter for Android IActivityClientController interface using class inheritance.
 * Extends IActivityClientController.Stub directly — every AIDL method is overridden
 * with a typed signature checked at compile time.
 *
 * Replaces the prior Proxy.newProxyInstance + InvocationHandler approach
 * (B.20.r11), which was flagged in feedback.txt P0 as a recurrence of the
 * pattern user explicitly rejected in AA.23 (2026-04-27).  Per project iron
 * rule (CLAUDE.md "Forward Bridge Pattern (Class Inheritance)"), all AIDL
 * stub-side adapters must use class inheritance, not InvocationHandler.
 *
 * Routing strategy:
 *   - lifecycle reporters (activityIdle / activityResumed / activityPaused / ...) are
 *     informational signals from the client.  Native OH AbilityScheduler already
 *     has equivalent callbacks; the Android-side ones can be no-op for HelloWorld
 *     as the OH schedule path drives lifecycle directly.  Future stages may
 *     forward them to OH AbilityManagerService.
 *   - getters (getDisplayId / getCallingPackage / ...) return safe defaults.
 *   - controls (setRequestedOrientation / setImmersive / ...) are no-op.
 *
 * Method tags:
 *   [STUB]    - Returns safe default; no OH route yet.  HelloWorld doesn't need.
 *   [BRIDGED] - Routes to OH equivalent (none yet at B.30; placeholder for
 *               future Activity lifecycle bridge).
 *
 * Singleton accessor pattern matches DisplayManagerAdapter / ActivityManagerAdapter
 * etc., used by AppSpawnXInit.installActivityClientControllerStub() for
 * ActivityClient.INTERFACE_SINGLETON injection.
 */
package adapter.activity;

import android.app.ActivityManager;
import android.app.IActivityClientController;
import android.app.ICompatCameraControlCallback;
import android.app.IRequestFinishCallback;
import android.app.PictureInPictureParams;
import android.content.ComponentName;
import android.content.Intent;
import android.content.res.Configuration;
import android.os.Bundle;
import android.os.IBinder;
import android.os.IRemoteCallback;
import android.os.PersistableBundle;
import android.os.RemoteException;
import android.util.Log;
import android.view.RemoteAnimationDefinition;
import android.window.SizeConfigurationBuckets;

import com.android.internal.policy.IKeyguardDismissCallback;

public final class ActivityClientControllerAdapter extends IActivityClientController.Stub {

    private static final String TAG = "OH_ACCAdapter";

    private static volatile ActivityClientControllerAdapter sInstance;

    public static ActivityClientControllerAdapter getInstance() {
        if (sInstance == null) {
            synchronized (ActivityClientControllerAdapter.class) {
                if (sInstance == null) {
                    sInstance = new ActivityClientControllerAdapter();
                }
            }
        }
        return sInstance;
    }

    public ActivityClientControllerAdapter() {
        Log.i(TAG, "ActivityClientControllerAdapter created (extends Stub)");
    }

    // ====================================================================
    // Lifecycle reporters (oneway) — informational; OH AbilityScheduler
    // drives lifecycle directly so Android-side reports are no-op.  [STUB]
    // ====================================================================

    // ----- G2.1 (2026-04-30): OH AbilityTransitionDone reverse callback -----
    // OH AMS expects the App to call AbilityTransitionDone(token, ohState,...)
    // after each lifecycle transition.  Without it, AMS triggers
    // LIFECYCLE_HALF_TIMEOUT (~1s) and kills the process.  We hook the
    // Android-side lifecycle reporters and forward the equivalent OH state.
    //
    // OH AbilityState enum (foundation/ability/.../ability_state.h):
    //   INITIAL=0  INACTIVE=1  ACTIVE=2  INACTIVATING=5  ACTIVATING=6
    //   TERMINATING=8  FOREGROUND=9  BACKGROUND=10
    //   FOREGROUNDING=11  BACKGROUNDING=12
    //
    // NOTE: these are the INTERNAL AMS state values. AbilityTransitionDone IPC
    // expects AbilityLifeCycleState (different enum). The translation is done
    // in nativeAbilityTransitionDone (JNI side) — see oh_ability_manager_client.cpp.
    private static final int OH_STATE_FOREGROUND   = 9;
    private static final int OH_STATE_BACKGROUND   = 10;
    private static final int OH_STATE_INACTIVE     = 1;

    private static native int nativeAbilityTransitionDone(long ohTokenAddr, int ohState);

    // G2.14ah reportOnCreateDone(...) REMOVED 2026-05-09 (R-fix root cause).
    // See AppSchedulerBridge.nativeOnScheduleLaunchAbility for full rationale.
    // Short version: it crashed main thread (SIGSEGV at 0x86c in sptr ctor),
    // and the reverse-notify it tried to provide was unnecessary — OH AMS drives
    // INACTIVE itself, and FOREGROUND is reverse-notified via activityResumed →
    // reportOhLifecycle below.

    // W9 (2026-05-18): INACTIVE heartbeat hook from Application.ActivityLifecycleCallbacks.onActivityStarted.
    // AOSP fires NO IPC between onCreate/onStart and onResume — investigation confirmed (see
    // doc §1.5 + §4.1.4 W9). Adapter therefore registers onActivityStarted via
    // Application.registerActivityLifecycleCallbacks (called once from
    // AppSchedulerBridge.ensureBindApplication after handleBindApplication returns) and forwards
    // AbilityTransitionDone(token, INACTIVE=1) to OH AMS at that point — semantic match for
    // OH "INACTIVE = onCreate completed, before onForeground" per §2.1.
    // Package-visible static wrapper so LifecycleAdapter (same package) can invoke it.
    static void reportInactiveHeartbeatForToken(IBinder token) {
        if (token == null) {
            Log.w(TAG, "W9 reportInactiveHeartbeatForToken: null token");
            return;
        }
        try {
            Long ohAddr = adapter.core.OhTokenRegistry.findOhToken(token);
            if (ohAddr != null && ohAddr != 0L) {
                int rc = nativeAbilityTransitionDone(ohAddr, OH_STATE_INACTIVE);
                Log.i(TAG, "W9 onActivityStarted: OH AbilityTransitionDone(token=0x"
                        + Long.toHexString(ohAddr) + ", state=INACTIVE=1) rc=" + rc);
            } else {
                Log.w(TAG, "W9 onActivityStarted: no OH token mapping for " + token);
            }
        } catch (Throwable t) {
            Log.e(TAG, "W9 onActivityStarted INACTIVE heartbeat failed", t);
        }
    }

    private void reportOhLifecycle(IBinder token, int ohState, String tag) {
        // G2.14f — direct BCP call. OhTokenRegistry was moved to BCP-resident
        // adapter.core.OhTokenRegistry (G2.14b token bridge work). The old
        // reflection path tried adapter.activity.AppSchedulerBridge$OhTokenRegistry
        // which is in oh-adapter-runtime.jar (PathClassLoader, non-BCP) — BCP
        // code can't see it via Class.forName even with ContextClassLoader,
        // because system_server-style threads here have BCP-only context CL.
        // The shim AppSchedulerBridge.OhTokenRegistry now delegates to
        // adapter.core.OhTokenRegistry, so we cut out the indirection entirely.
        try {
            Long ohAddr = adapter.core.OhTokenRegistry.findOhToken(token);
            if (ohAddr != null && ohAddr != 0L) {
                int rc = nativeAbilityTransitionDone(ohAddr, ohState);
                Log.i(TAG, tag + ": OH AbilityTransitionDone(token=0x"
                        + Long.toHexString(ohAddr) + ", state=" + ohState + ") rc=" + rc);
            } else {
                Log.w(TAG, tag + ": no OH token mapping for " + token);
            }
        } catch (Throwable t) {
            Log.e(TAG, tag + " reverse callback failed", t);
        }
    }

    @Override
    public void activityIdle(IBinder token, Configuration config, boolean stopProfiling) { /* no-op */ }

    // Fn03.A10 consumes the typed Fn04.A02 producer receipt emitted only after
    // the app-content ANativeWindow successfully queues a buffer to OH RS.
    // OnDraw and timer expiry are deliberately not accepted as presentation.
    private static final java.util.WeakHashMap<IBinder, Long> sForegroundGeneration =
            new java.util.WeakHashMap<>();
    private static native int nativeOpenForegroundTransition(long ohTokenAddr,
            String owner, int androidTokenIdentity, long windowGeneration,
            String transitionId);

    @Override
    public void activityResumed(IBinder token, boolean handleSplashScreenExit) {
        if (token == null) {
            Log.w(TAG, "activityResumed: null token");
            return;
        }
        try {
            Long ohAddr = adapter.core.OhTokenRegistry.findOhToken(token);
            if (ohAddr == null || ohAddr == 0L) {
                Log.w(TAG, "activityResumed: no OH token mapping for " + token);
                return;
            }
            long windowGeneration;
            synchronized (sForegroundGeneration) {
                Long prior = sForegroundGeneration.get(token);
                windowGeneration = prior == null ? 1L : prior.longValue() + 1L;
                sForegroundGeneration.put(token, windowGeneration);
            }
            String owner = android.app.ActivityThread.currentPackageName();
            if (owner == null || owner.isEmpty()) {
                owner = "unknown.android.owner";
            }
            String transitionId = "foreground:"
                    + Integer.toHexString(System.identityHashCode(token))
                    + ":" + windowGeneration;
            int rc = nativeOpenForegroundTransition(ohAddr.longValue(), owner,
                    System.identityHashCode(token), windowGeneration, transitionId);
            if (rc == 0) {
                Log.i(TAG, "Fn03.A10 foreground join open; waiting for typed "
                        + "Fn04.A02 APP_CONTENT receipt transition=" + transitionId);
            } else {
                Log.e(TAG, "Fn03.A10 foreground join rejected rc=" + rc
                        + " transition=" + transitionId);
            }
        } catch (Throwable t) {
            Log.e(TAG, "Fn03.A10 foreground join failed closed", t);
        }
    }

    @Override
    public void activityRefreshed(IBinder token) { /* no-op */ }

    @Override
    public void activityTopResumedStateLost() { /* no-op */ }

    @Override
    public void activityPaused(IBinder token) {
        // Android Activity.onPause done → OH AbilityState.INACTIVE (active→inactive transition).
        reportOhLifecycle(token, OH_STATE_INACTIVE, "activityPaused");
    }

    @Override
    public void activityStopped(IBinder token, Bundle state, PersistableBundle persistentState,
            CharSequence description) {
        // Android Activity.onStop done → OH AbilityState.BACKGROUND.
        reportOhLifecycle(token, OH_STATE_BACKGROUND, "activityStopped");
    }

    @Override
    public void activityDestroyed(IBinder token) { /* no-op — finishActivity already drove OH TerminateAbility */ }

    @Override
    public void activityLocalRelaunch(IBinder token) { /* no-op */ }

    @Override
    public void activityRelaunched(IBinder token) { /* no-op */ }

    @Override
    public void reportSizeConfigurations(IBinder token, SizeConfigurationBuckets sizeConfigurations) { /* no-op */ }

    // ====================================================================
    // Task / activity control — return safe defaults.  [STUB]
    // ====================================================================

    @Override
    public boolean moveActivityTaskToBack(IBinder token, boolean nonRoot) { return false; }

    @Override
    public boolean shouldUpRecreateTask(IBinder token, String destAffinity) { return false; }

    @Override
    public boolean navigateUpTo(IBinder token, Intent target, String resolvedType,
            int resultCode, Intent resultData) { return false; }

    @Override
    public boolean releaseActivityInstance(IBinder token) { return false; }

    /**
     * B.48 (2026-04-30 §1.2.4.3 P2 reverse): App finish() reverse callback.
     * Look up OH IRemoteObject token addr from OhTokenRegistry (set at SLA time),
     * then call OH AbilityMS::TerminateAbility via JNI bridge.
     * Returns true (App side expects success) regardless of OH result — OH-side
     * failure should not unwind App's onDestroy chain.
     */
    private static native int nativeTerminateAbilityByTokenAddr(long ohTokenAddr, int resultCode);

    // 2026-06-01 (back-key blocker fix, option B): drive OH AbilityMS::MinimizeAbility
    // for a task-root back press (back to home, keep process alive). See onBackPressed.
    // Retained for reference; onBackPressed now uses nativeBackPressedByTokenAddr.
    private static native int nativeMinimizeAbilityByTokenAddr(long ohTokenAddr);

    // 2026-06-01 (back-key fix, native-semantic): route Android back to OH
    // TerminateAbility (androidBack marker); OH decides root=minimize / non-root=pop.
    private static native int nativeBackPressedByTokenAddr(long ohTokenAddr);

    @Override
    public boolean finishActivity(IBinder token, int code, Intent data, int finishTask) {
        try {
            // 2026-05-26 Layer 2 dedup (mission_group_design.html §15): the App is
            // finishing this Activity locally, so the reverse ScheduleCleanAbility OH
            // sends back must NOT redispatch a second DestroyActivityItem (hazard B).
            adapter.core.OhTokenRegistry.markDestroying(token);
            // G2.14f — direct BCP call (see reportOhLifecycle for rationale).
            Long ohAddr = adapter.core.OhTokenRegistry.findOhToken(token);
            if (ohAddr != null && ohAddr != 0L) {
                int rc = nativeTerminateAbilityByTokenAddr(ohAddr, code);
                Log.i(TAG, "finishActivity: OH TerminateAbility(token=0x"
                        + Long.toHexString(ohAddr) + ", code=" + code + ") rc=" + rc);
            } else {
                Log.w(TAG, "finishActivity: no OH token mapping for "
                        + token + " — finish-only Android-side");
            }
        } catch (Throwable t) {
            Log.e(TAG, "finishActivity reverse callback failed", t);
        }
        return true;
    }

    @Override
    public boolean finishActivityAffinity(IBinder token) { return true; }

    @Override
    public void finishSubActivity(IBinder token, String resultWho, int requestCode) { /* no-op */ }

    @Override
    public void setForceSendResultForMediaProjection(IBinder token) { /* no-op */ }

    // ====================================================================
    // Activity state queries.  [STUB]
    // ====================================================================

    @Override
    public boolean isTopOfTask(IBinder token) { return true; }

    @Override
    public boolean willActivityBeVisible(IBinder token) { return true; }

    @Override
    public int getDisplayId(IBinder activityToken) { return 0; }   // OH default display

    @Override
    public int getTaskForActivity(IBinder token, boolean onlyRoot) { return -1; }

    @Override
    public Configuration getTaskConfiguration(IBinder activityToken) { return null; }

    @Override
    public IBinder getActivityTokenBelow(IBinder token) { return null; }

    @Override
    public ComponentName getCallingActivity(IBinder token) { return null; }

    @Override
    public String getCallingPackage(IBinder token) { return null; }

    @Override
    public int getLaunchedFromUid(IBinder token) { return 0; }

    @Override
    public String getLaunchedFromPackage(IBinder token) { return null; }

    // ====================================================================
    // Orientation.  [STUB]
    // ====================================================================

    @Override
    public void setRequestedOrientation(IBinder token, int requestedOrientation) { /* no-op */ }

    @Override
    public int getRequestedOrientation(IBinder token) { return -1; /* SCREEN_ORIENTATION_UNSPECIFIED */ }

    // ====================================================================
    // Translucency / immersive.  [STUB]
    // ====================================================================

    @Override
    public boolean convertFromTranslucent(IBinder token) { return false; }

    @Override
    public boolean convertToTranslucent(IBinder token, Bundle options) { return false; }

    @Override
    public boolean isImmersive(IBinder token) { return false; }

    @Override
    public void setImmersive(IBinder token, boolean immersive) { /* no-op */ }

    // ====================================================================
    // Picture-in-picture / multiwindow.  [STUB]
    // ====================================================================

    @Override
    public boolean enterPictureInPictureMode(IBinder token, PictureInPictureParams params) { return false; }

    @Override
    public void setPictureInPictureParams(IBinder token, PictureInPictureParams params) { /* no-op */ }

    @Override
    public void setShouldDockBigOverlays(IBinder token, boolean shouldDockBigOverlays) { /* no-op */ }

    @Override
    public void toggleFreeformWindowingMode(IBinder token) { /* no-op */ }

    @Override
    public void requestMultiwindowFullscreen(IBinder token, int request, IRemoteCallback callback) { /* no-op */ }

    // ====================================================================
    // Lock task / assist / voice interaction.  [STUB]
    // ====================================================================

    @Override
    public void startLockTaskModeByToken(IBinder token) { /* no-op */ }

    @Override
    public void stopLockTaskModeByToken(IBinder token) { /* no-op */ }

    @Override
    public void showLockTaskEscapeMessage(IBinder token) { /* no-op */ }

    @Override
    public void setTaskDescription(IBinder token, ActivityManager.TaskDescription values) { /* no-op */ }

    @Override
    public boolean showAssistFromActivity(IBinder token, Bundle args) { return false; }

    @Override
    public boolean isRootVoiceInteraction(IBinder token) { return false; }

    @Override
    public void startLocalVoiceInteraction(IBinder token, Bundle options) { /* no-op */ }

    @Override
    public void stopLocalVoiceInteraction(IBinder token) { /* no-op */ }

    // ====================================================================
    // Show-when-locked / turn-screen-on / draw flags.  [STUB]
    // ====================================================================

    @Override
    public void setShowWhenLocked(IBinder token, boolean showWhenLocked) { /* no-op */ }

    @Override
    public void setInheritShowWhenLocked(IBinder token, boolean setInheritShownWhenLocked) { /* no-op */ }

    @Override
    public void setTurnScreenOn(IBinder token, boolean turnScreenOn) { /* no-op */ }

    @Override
    public void setAllowCrossUidActivitySwitchFromBelow(IBinder token, boolean allowed) { /* no-op */ }

    @Override
    public void reportActivityFullyDrawn(IBinder token, boolean restoredFromBundle) { /* no-op */ }

    // ====================================================================
    // Activity transitions.  [STUB]
    // ====================================================================

    @Override
    public void overrideActivityTransition(IBinder token, boolean open, int enterAnim,
            int exitAnim, int backgroundColor) { /* no-op */ }

    @Override
    public void clearOverrideActivityTransition(IBinder token, boolean open) { /* no-op */ }

    @Override
    public void overridePendingTransition(IBinder token, String packageName,
            int enterAnim, int exitAnim, int backgroundColor) { /* no-op */ }

    @Override
    public int setVrMode(IBinder token, boolean enabled, ComponentName packageName) { return 0; }

    @Override
    public void setRecentsScreenshotEnabled(IBinder token, boolean enabled) { /* no-op */ }

    @Override
    public void invalidateHomeTaskSnapshot(IBinder homeToken) { /* no-op */ }

    // ====================================================================
    // Keyguard / remote animations.  [STUB]
    // ====================================================================

    @Override
    public void dismissKeyguard(IBinder token, IKeyguardDismissCallback callback,
            CharSequence message) { /* no-op */ }

    @Override
    public void registerRemoteAnimations(IBinder token, RemoteAnimationDefinition definition) { /* no-op */ }

    @Override
    public void unregisterRemoteAnimations(IBinder token) { /* no-op */ }

    // ====================================================================
    // Misc.  [STUB]
    // ====================================================================

    @Override
    public void onBackPressed(IBinder activityToken, IRequestFinishCallback callback) {
        // 2026-06-01 (back-key fix, native-semantic redesign).
        //
        // AOSP Activity.onBackPressed() does NOT finish locally — it calls
        // ActivityClient.onBackPressed(token, RequestFinishCallback), an IPC to
        // ATMS.  The adapter replaces ATMS, so this entry — previously a no-op —
        // silently swallowed every back press ("back does nothing").
        //
        // OH-native truth (verified): back == TerminateAbility (Ability::
        // OnBackPressed -> TerminateAbility), while recents/multitask minimize ==
        // MinimizeAbility (WMS MinimizeApp -> AMS MinimizeAbility).  They are two
        // independent OH methods, so routing back to TerminateAbility keeps it
        // naturally separate from recents (no pid/caller guessing).
        //
        // We make ONE call (nativeBackPressedByTokenAddr -> OH TerminateAbility
        // with an "androidBack" marker Want).  OH MissionListManager decides the
        // root/non-root behavior — it owns the mission stack:
        //   - non-root (multi-Activity stack)  -> pop the top Activity (reveal below)
        //   - root      (single Activity)      -> minimize keep-alive (moveTaskToBack)
        // The 'callback' (IRequestFinishCallback) is unused: OH performs the
        // navigation directly; we do not ask the App to finish itself.
        try {
            Long ohAddr = adapter.core.OhTokenRegistry.findOhToken(activityToken);
            if (ohAddr == null || ohAddr == 0L) {
                Log.w(TAG, "onBackPressed: no OH token mapping for " + activityToken
                        + " — cannot drive OH back navigation");
                return;
            }
            int rc = nativeBackPressedByTokenAddr(ohAddr);
            Log.i(TAG, "onBackPressed: → OH TerminateAbility(androidBack, token=0x"
                    + Long.toHexString(ohAddr) + ") rc=" + rc
                    + " [OH decides root=minimize / non-root=pop]");
        } catch (Throwable t) {
            Log.e(TAG, "onBackPressed reverse callback failed", t);
        }
    }

    @Override
    public void splashScreenAttached(IBinder token) { /* no-op */ }

    @Override
    public void requestCompatCameraControl(IBinder token, boolean showControl,
            boolean transformationApplied, ICompatCameraControlCallback callback) { /* no-op */ }

    @Override
    public void enableTaskLocaleOverride(IBinder token) { /* no-op */ }

    @Override
    public boolean isRequestedToLaunchInTaskFragment(IBinder activityToken,
            IBinder taskFragmentToken) { return false; }
}
