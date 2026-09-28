/*
 * ContentServiceAdapter.java
 *
 * Real-routed (no-op) adapter implementation of android.content.IContentService.
 *
 * Why this exists
 * ---------------
 * ServiceManager.getService("content") previously hit
 * OHServiceManager.lookupAdapter("content") -> null. AOSP's
 * ContentResolver.getContentService() caches that binder and, during an
 * Activity's onResume, calls IContentService.registerContentObserver(...) on it.
 * A null binder -> NullPointerException -> "Unable to resume activity ...
 * UnityPlayerActivity". This is the FIRST BCP wall for the unmodified Unity APK
 * (betweentwoworlds) after the IL2CPP engine + worker threads come up.
 *
 * OpenHarmony has no IContentService analog (content-observer / sync-adapter is
 * an Android-framework concept). So, exactly like the Unity peripheral-service
 * stubs (adapter.core.unitysvc.*: power/audio/thermal/vibrator/clipboard), this
 * is a minimal *real* IContentService.Stub binder that returns safe defaults for
 * every method and NEVER throws. The three observer methods Unity actually
 * exercises (register/unregister/notifyChange) are explicit no-ops; the ~40 sync
 * methods return null / 0 / false / empty so any later ContentResolver call also
 * degrades gracefully instead of NPE/abort.
 *
 * Design boundary (HanBing iron rules)
 * ------------------------------------
 *   - Adapts at the IPC interface (IContentService) only; ServiceManager,
 *     ContentResolver and the rest of the AOSP framework are untouched
 *     (rule 2/3).
 *   - No ART / class_linker / vtable involvement (rule 1).
 *   - This class lives in adapter.contentprovider (the BCP oh-adapter-framework
 *     jar) next to ContentProviderBridge; wiring is one arm in
 *     OHServiceManager.lookupAdapter (mirrors the "user" -> UserManagerAdapter
 *     arm). Changing the BCP jar requires a coherent ART boot-image re-bake
 *     (rule 4) -- see the deploy recipe.
 *
 * Future: if an app needs live cross-process content-observer notifications,
 * notifyChange/registerContentObserver can be bridged to OH DataShare observer
 * callbacks (cf. ContentProviderBridge's DataShareHelper route). Not needed for
 * Unity first-frame.
 */
package adapter.contentprovider;

import android.accounts.Account;
import android.content.ComponentName;
import android.content.IContentService;
import android.content.ISyncStatusObserver;
import android.content.PeriodicSync;
import android.content.SyncAdapterType;
import android.content.SyncInfo;
import android.content.SyncRequest;
import android.content.SyncStatusInfo;
import android.database.IContentObserver;
import android.net.Uri;
import android.os.Bundle;
import android.os.RemoteException;

import java.util.Collections;
import java.util.List;

public final class ContentServiceAdapter extends IContentService.Stub {

    private static final String TAG = "OH_ContentSvcAdapter";

    private static volatile ContentServiceAdapter sInstance;

    public static ContentServiceAdapter getInstance() {
        if (sInstance == null) {
            synchronized (ContentServiceAdapter.class) {
                if (sInstance == null) {
                    sInstance = new ContentServiceAdapter();
                }
            }
        }
        return sInstance;
    }

    public ContentServiceAdapter() {
        System.err.println("[" + TAG + "] instantiated (no-op IContentService; OH has no analog)");
    }

    // ------------------------------------------------------------------------
    // Content observers -- the methods Unity's onResume actually exercises.
    // No-op: we don't deliver content-change callbacks (no OH observer bridge
    // yet), but registering/unregistering/notifying must never NPE or throw.
    // ------------------------------------------------------------------------

    @Override
    public void registerContentObserver(Uri uri, boolean notifyForDescendants,
            IContentObserver observer, int userHandle, int targetSdkVersion)
            throws RemoteException {
        // no-op
    }

    @Override
    public void unregisterContentObserver(IContentObserver observer) throws RemoteException {
        // no-op
    }

    @Override
    public void notifyChange(Uri[] uris, IContentObserver observer,
            boolean observerWantsSelfNotifications, int flags,
            int userHandle, int targetSdkVersion, String callingPackage)
            throws RemoteException {
        // no-op
    }

    // ------------------------------------------------------------------------
    // Sync framework -- safe defaults so any later ContentResolver sync call
    // degrades gracefully (null / 0 / false / empty), never aborts.
    // ------------------------------------------------------------------------

    @Override
    public void requestSync(Account account, String authority, Bundle extras,
            String callingPackage) throws RemoteException {
        // no-op
    }

    @Override
    public void sync(SyncRequest request, String callingPackage) throws RemoteException {
        // no-op
    }

    @Override
    public void syncAsUser(SyncRequest request, int userId, String callingPackage)
            throws RemoteException {
        // no-op
    }

    @Override
    public void cancelSync(Account account, String authority, ComponentName cname)
            throws RemoteException {
        // no-op
    }

    @Override
    public void cancelSyncAsUser(Account account, String authority, ComponentName cname,
            int userId) throws RemoteException {
        // no-op
    }

    @Override
    public void cancelRequest(SyncRequest request) throws RemoteException {
        // no-op
    }

    @Override
    public boolean getSyncAutomatically(Account account, String providerName)
            throws RemoteException {
        return false;
    }

    @Override
    public boolean getSyncAutomaticallyAsUser(Account account, String providerName, int userId)
            throws RemoteException {
        return false;
    }

    @Override
    public void setSyncAutomatically(Account account, String providerName, boolean sync)
            throws RemoteException {
        // no-op
    }

    @Override
    public void setSyncAutomaticallyAsUser(Account account, String providerName, boolean sync,
            int userId) throws RemoteException {
        // no-op
    }

    @Override
    public List<PeriodicSync> getPeriodicSyncs(Account account, String providerName,
            ComponentName cname) throws RemoteException {
        return Collections.emptyList();
    }

    @Override
    public void addPeriodicSync(Account account, String providerName, Bundle extras,
            long pollFrequency) throws RemoteException {
        // no-op
    }

    @Override
    public void removePeriodicSync(Account account, String providerName, Bundle extras)
            throws RemoteException {
        // no-op
    }

    @Override
    public int getIsSyncable(Account account, String providerName) throws RemoteException {
        return 0;
    }

    @Override
    public int getIsSyncableAsUser(Account account, String providerName, int userId)
            throws RemoteException {
        return 0;
    }

    @Override
    public void setIsSyncable(Account account, String providerName, int syncable)
            throws RemoteException {
        // no-op
    }

    @Override
    public void setIsSyncableAsUser(Account account, String providerName, int syncable,
            int userId) throws RemoteException {
        // no-op
    }

    @Override
    public void setMasterSyncAutomatically(boolean flag) throws RemoteException {
        // no-op
    }

    @Override
    public void setMasterSyncAutomaticallyAsUser(boolean flag, int userId)
            throws RemoteException {
        // no-op
    }

    @Override
    public boolean getMasterSyncAutomatically() throws RemoteException {
        return false;
    }

    @Override
    public boolean getMasterSyncAutomaticallyAsUser(int userId) throws RemoteException {
        return false;
    }

    @Override
    public List<SyncInfo> getCurrentSyncs() throws RemoteException {
        return Collections.emptyList();
    }

    @Override
    public List<SyncInfo> getCurrentSyncsAsUser(int userId) throws RemoteException {
        return Collections.emptyList();
    }

    @Override
    public SyncAdapterType[] getSyncAdapterTypes() throws RemoteException {
        return new SyncAdapterType[0];
    }

    @Override
    public SyncAdapterType[] getSyncAdapterTypesAsUser(int userId) throws RemoteException {
        return new SyncAdapterType[0];
    }

    @Override
    public String[] getSyncAdapterPackagesForAuthorityAsUser(String authority, int userId)
            throws RemoteException {
        return new String[0];
    }

    @Override
    public String getSyncAdapterPackageAsUser(String accountType, String authority, int userId)
            throws RemoteException {
        return null;
    }

    @Override
    public boolean isSyncActive(Account account, String authority, ComponentName cname)
            throws RemoteException {
        return false;
    }

    @Override
    public SyncStatusInfo getSyncStatus(Account account, String authority, ComponentName cname)
            throws RemoteException {
        return null;
    }

    @Override
    public SyncStatusInfo getSyncStatusAsUser(Account account, String authority,
            ComponentName cname, int userId) throws RemoteException {
        return null;
    }

    @Override
    public boolean isSyncPending(Account account, String authority, ComponentName cname)
            throws RemoteException {
        return false;
    }

    @Override
    public boolean isSyncPendingAsUser(Account account, String authority, ComponentName cname,
            int userId) throws RemoteException {
        return false;
    }

    @Override
    public void addStatusChangeListener(int mask, ISyncStatusObserver callback)
            throws RemoteException {
        // no-op
    }

    @Override
    public void removeStatusChangeListener(ISyncStatusObserver callback) throws RemoteException {
        // no-op
    }

    @Override
    public void putCache(String packageName, Uri key, Bundle value, int userId)
            throws RemoteException {
        // no-op
    }

    @Override
    public Bundle getCache(String packageName, Uri key, int userId) throws RemoteException {
        return null;
    }

    @Override
    public void resetTodayStats() throws RemoteException {
        // no-op
    }

    @Override
    public void onDbCorruption(String tag, String message, String stacktrace)
            throws RemoteException {
        // no-op
    }
}
