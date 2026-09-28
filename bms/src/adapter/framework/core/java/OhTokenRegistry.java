/*
 * OhTokenRegistry.java
 *
 * BCP-resident registry that bridges Android adapter-side IBinder tokens to
 * OH AbilityRecord token raw pointers (uint64 / long).
 *
 * Spec: doc/window_manager_ipc_adapter_design.html §3.1.4.6 / §3.1.5.6.1 / §3.1.5.6.3 / §3.1.5.6.4
 *
 * Lives in adapter.core (BCP / oh-adapter-framework.jar) so both:
 *   - adapter.activity.AppSchedulerBridge   (oh-adapter-runtime.jar, populates)
 *   - adapter.window.WindowSessionAdapter   (BCP, reads on addToDisplay)
 * can reference it without circular jar dependencies.
 *
 * Three concurrent maps:
 *   ohToAndroid       OH token raw addr   -> Android IBinder (canonical reverse map)
 *   androidToOh       Android IBinder     -> OH token raw addr (forward lookup, used by addToDisplay)
 *   recordToAndroid   OH AbilityRecord id -> Android IBinder (legacy LifecycleAdapter path)
 *   androidToMainSession  Android IBinder -> OH SCB main SceneSession persistentId (§3.1.5.6.3)
 */
package adapter.core;

import android.os.Binder;
import android.os.IBinder;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;

public final class OhTokenRegistry {

    private static final ConcurrentHashMap<Long, IBinder> sOhToAndroid = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<IBinder, Long> sAndroidToOh = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<Integer, IBinder> sRecordToAndroid = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<IBinder, Integer> sAndroidToMainSession = new ConcurrentHashMap<>();

    // 2026-05-26 Layer 2 (mission_group_design.html §15): tokens whose AOSP
    // Activity destroy is already in flight.  Shared dedup between the forward
    // finishActivity path (ActivityClientControllerAdapter) and the reverse
    // ScheduleCleanAbility path (AppSchedulerBridge) so a single teardown never
    // dispatches two DestroyActivityItems for the same Activity (hazard B).
    private static final java.util.Set<IBinder> sDestroying =
            java.util.Collections.newSetFromMap(new ConcurrentHashMap<IBinder, Boolean>());

    // 2026-05-25 Bug 2 Fix 1: defer-and-flush for the FOREGROUND lifecycle race.
    // onScheduleAbilityTransaction (IAbilityScheduler thread) can arrive before
    // nativeOnScheduleLaunchAbility (IAppScheduler thread) has registered the token +
    // scheduled onCreate.  Instead of dropping the transaction (which lost the
    // FOREGROUND ack → OH AMS LIFECYCLE_TIMEOUT → kill → relaunch loop), defer it here
    // and flush once the launch completes, preserving onCreate→onResume order.
    private static final ConcurrentHashMap<Long, ConcurrentLinkedQueue<Runnable>> sPendingByOhToken = new ConcurrentHashMap<>();
    private static final java.util.Set<Long> sLaunchComplete = ConcurrentHashMap.newKeySet();

    private OhTokenRegistry() {}

    /**
     * Get-or-create an Android-side IBinder for the given OH AbilityRecord token.
     * Caches both directions so subsequent lookups are stable. Called from
     * AppSchedulerBridge.nativeOnScheduleLaunchAbility (B.47 path).
     */
    public static IBinder acquireAndroidToken(int abilityRecordId, long ohTokenAddr) {
        if (ohTokenAddr != 0L) {
            IBinder existing = sOhToAndroid.get(ohTokenAddr);
            if (existing != null) return existing;
        }
        IBinder b = new Binder();
        if (ohTokenAddr != 0L) {
            sOhToAndroid.put(ohTokenAddr, b);
            sAndroidToOh.put(b, ohTokenAddr);
        }
        sRecordToAndroid.put(abilityRecordId, b);
        return b;
    }

    public static IBinder findByOhToken(long ohTokenAddr) {
        return sOhToAndroid.get(ohTokenAddr);
    }

    /** Layer 2 dedup: mark an Activity token whose destroy is already in flight. */
    public static void markDestroying(IBinder androidBinder) {
        if (androidBinder != null) {
            sDestroying.add(androidBinder);
        }
    }

    /** Layer 2 dedup: true if this Activity token is already being destroyed. */
    public static boolean isDestroying(IBinder androidBinder) {
        return androidBinder != null && sDestroying.contains(androidBinder);
    }

    /** §3.1.5.6.1 — used by WindowSessionAdapter.addToDisplay to thread OH token to SCB. */
    public static Long findOhToken(IBinder androidBinder) {
        return sAndroidToOh.get(androidBinder);
    }

    public static IBinder findByRecordId(int abilityRecordId) {
        return sRecordToAndroid.get(abilityRecordId);
    }

    /**
     * §3.1.5.6.3 — record OH SCB-auto-created main SceneSession persistentId
     * (when SCB binds an existing main session to our SessionStageAdapter).
     * Triggers the addToDisplay reuse path instead of CreateAndConnect.
     */
    public static void setMainSessionId(long ohTokenAddr, int persistentId) {
        IBinder b = sOhToAndroid.get(ohTokenAddr);
        if (b != null && persistentId > 0) {
            sAndroidToMainSession.put(b, persistentId);
        }
    }

    public static int getMainSessionId(IBinder androidBinder) {
        if (androidBinder == null) return -1;
        Integer id = sAndroidToMainSession.get(androidBinder);
        return id == null ? -1 : id.intValue();
    }

    /**
     * §3.1.5.6.4 — DeathRecipient cleanup hook called from
     * app_scheduler_adapter.cpp::TokenDeathRecipient::OnRemoteDied via JNI.
     * Drops all maps keyed by the dead OH token.
     */
    public static void removeByOhToken(long ohTokenAddr) {
        IBinder b = sOhToAndroid.remove(ohTokenAddr);
        if (b != null) {
            sAndroidToOh.remove(b);
            sAndroidToMainSession.remove(b);
            sDestroying.remove(b);
            // 2026-05-26 Layer 2 (hazard F): also drop the abilityRecordId->IBinder
            // entry so sRecordToAndroid doesn't leak across launch/kill cycles.
            sRecordToAndroid.values().remove(b);
        }
        // Bug 2 Fix 1: drop deferred lifecycle work + launch flag for the dead token.
        sLaunchComplete.remove(ohTokenAddr);
        sPendingByOhToken.remove(ohTokenAddr);
    }

    /**
     * 2026-05-25 Bug 2 Fix 1: run {@code action} once the launch for {@code ohTokenAddr}
     * has completed (token registered + onCreate scheduled).  Runs immediately if the
     * launch already completed; otherwise defers until {@link #markLaunchComplete}.
     * Replaces the old "drop FOREGROUND transaction when token not yet registered"
     * behavior, which lost the FOREGROUND ack and tripped OH AMS LIFECYCLE_TIMEOUT.
     */
    public static void runAfterLaunchComplete(long ohTokenAddr, Runnable action) {
        if (action == null) {
            return;
        }
        if (ohTokenAddr == 0L || sLaunchComplete.contains(ohTokenAddr)) {
            action.run();
            return;
        }
        sPendingByOhToken.computeIfAbsent(ohTokenAddr, k -> new ConcurrentLinkedQueue<>()).add(action);
    }

    /**
     * 2026-05-25 Bug 2 Fix 1: called from AppSchedulerBridge.nativeOnScheduleLaunchAbility
     * right after the LaunchActivityItem (onCreate) transaction is scheduled.  Marks the
     * launch complete and flushes any deferred lifecycle work for this token, so a
     * FOREGROUND transaction that raced ahead is dispatched now — AFTER onCreate.
     */
    public static void markLaunchComplete(long ohTokenAddr) {
        if (ohTokenAddr == 0L) {
            return;
        }
        sLaunchComplete.add(ohTokenAddr);
        ConcurrentLinkedQueue<Runnable> q = sPendingByOhToken.remove(ohTokenAddr);
        if (q != null) {
            Runnable r;
            while ((r = q.poll()) != null) {
                r.run();
            }
        }
    }
}
