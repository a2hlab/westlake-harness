/*
 * ServiceConnectionRegistry.java
 *
 * Singleton registry managing the mapping between Android IServiceConnection
 * and OH AbilityConnection for the Service adaptation layer.
 *
 * When an Android app calls bindService(), the adapter registers the
 * IServiceConnection here and obtains a local connectionId. This id is
 * passed to the native side which creates an OH AbilityConnection and
 * returns an OH-assigned connectionId. When OH fires onAbilityConnectDone /
 * onAbilityDisconnectDone, the native callback looks up the Android
 * IServiceConnection through this registry and dispatches the event.
 *
 * Reference:
 *   Android: core/java/android/app/LoadedApk.java (ServiceDispatcher)
 *   OH: ability_rt/interfaces/inner_api/ability_manager/include/ability_connection_stub.h
 */
package adapter.activity;

import android.app.IServiceConnection;
import android.content.ComponentName;
import android.os.IBinder;
import android.os.RemoteException;
import android.util.Log;

import java.util.HashMap;
import java.util.Map;

public class ServiceConnectionRegistry {

    private static final String TAG = "OH_SvcConnRegistry";

    // Singleton
    private static final ServiceConnectionRegistry sInstance = new ServiceConnectionRegistry();

    public static ServiceConnectionRegistry getInstance() {
        return sInstance;
    }

    private ServiceConnectionRegistry() {}

    // ========================================================================
    // Registration result (2026-07-28, Fn07.A01)
    // ========================================================================

    /**
     * Result of registerConnection: the assigned connectionId plus whether
     * the record was newly created.  Callers that roll back after a failed
     * nativeConnectAbility must unregister ONLY when created == true;
     * unregistering on the dedup path would destroy the first, still-live
     * binding's record (Fn07.A01 failure oracle F2).
     */
    public static final class RegistrationResult {
        public final int connectionId;
        public final boolean created;

        RegistrationResult(int connectionId, boolean created) {
            this.connectionId = connectionId;
            this.created = created;
        }
    }

    // ========================================================================
    // Inner class: ConnectionRecord
    // ========================================================================

    private static class ConnectionRecord {
        final IServiceConnection connection;
        final ComponentName targetComponent;
        int connectionId;      // assigned locally, shared with native side
        boolean bound;

        ConnectionRecord(IServiceConnection conn, ComponentName target) {
            this.connection = conn;
            this.targetComponent = target;
            this.connectionId = -1;
            this.bound = false;
        }
    }

    // ========================================================================
    // Fields
    // ========================================================================

    // Key = IServiceConnection.asBinder(), maps to ConnectionRecord
    private final Map<IBinder, ConnectionRecord> mConnections = new HashMap<>();

    // Key = connectionId (shared between Java and native), maps to ConnectionRecord
    private final Map<Integer, ConnectionRecord> mConnectionsById = new HashMap<>();

    private int mNextConnectionId = 1;

    // ========================================================================
    // Connection registration (called by ActivityManagerAdapter.bindService)
    // ========================================================================

    /**
     * Register an Android IServiceConnection and assign a local connectionId.
     * If the same connection (by Binder identity) is already registered,
     * returns the existing local connectionId with created == false and does
     * not create a duplicate record.
     *
     * @param connection The Android IServiceConnection from the app
     * @param target     The target service ComponentName
     * @return RegistrationResult with the connectionId and created flag
     */
    public synchronized RegistrationResult registerConnection(
            IServiceConnection connection, ComponentName target) {
        IBinder key = connection.asBinder();
        ConnectionRecord existing = mConnections.get(key);
        if (existing != null) {
            Log.d(TAG, "Connection already registered, connId=" + existing.connectionId
                    + " target=" + target);
            return new RegistrationResult(existing.connectionId, false);
        }

        ConnectionRecord record = new ConnectionRecord(connection, target);
        int connId = mNextConnectionId++;
        record.connectionId = connId;

        mConnections.put(key, record);
        mConnectionsById.put(connId, record);

        Log.i(TAG, "Registered connection: connId=" + connId + " target=" + target);
        return new RegistrationResult(connId, true);
    }

    /**
     * Unregister an Android IServiceConnection.
     * Removes the record from all maps.
     *
     * @param connection The Android IServiceConnection to remove
     * @return the OH connectionId (for native disconnect), or -1 if not found
     */
    public synchronized int unregisterConnection(IServiceConnection connection) {
        IBinder key = connection.asBinder();
        ConnectionRecord record = mConnections.remove(key);
        if (record == null) {
            Log.d(TAG, "unregisterConnection: not found");
            return -1;
        }

        mConnectionsById.remove(record.connectionId);

        Log.i(TAG, "Unregistered connection: connId=" + record.connectionId
                + " target=" + record.targetComponent);
        return record.connectionId;
    }

    /**
     * 仅当 binder 与预期 connId 仍指向同一记录时移除。
     *
     * 该 compare-and-remove 关闭 native 调用期间发生 unbind/rebind 后，
     * 迟到失败回滚误删新记录的 ABA 窗口。
     */
    public synchronized boolean unregisterConnection(
            IServiceConnection connection, int expectedConnectionId) {
        IBinder key = connection.asBinder();
        ConnectionRecord record = mConnections.get(key);
        if (record == null || record.connectionId != expectedConnectionId) {
            Log.w(TAG, "Conditional unregister skipped: expected connId="
                    + expectedConnectionId);
            return false;
        }
        mConnections.remove(key);
        mConnectionsById.remove(expectedConnectionId);
        Log.i(TAG, "Conditionally unregistered connection: connId="
                + expectedConnectionId + " target=" + record.targetComponent);
        return true;
    }

    /**
     * OH 已异步报告连接失败；按 connId 清理对应 Java 记录。
     */
    public synchronized void onServiceConnectionFailed(
            int connectionId, String bundleName, String abilityName, int resultCode) {
        ConnectionRecord record = mConnectionsById.remove(connectionId);
        if (record == null) {
            Log.w(TAG, "onServiceConnectionFailed: no record for connId="
                    + connectionId + " rc=" + resultCode);
            return;
        }
        IBinder key = record.connection.asBinder();
        if (mConnections.get(key) == record) {
            mConnections.remove(key);
        }
        Log.e(TAG, "Service connection failed: connId=" + connectionId
                + " bundle=" + bundleName + " ability=" + abilityName
                + " rc=" + resultCode);
    }

    // ========================================================================
    // OH -> Android callbacks (called from native via JNI)
    // ========================================================================

    /**
     * Called when OH reports that a service ability has connected.
     * Dispatches the event to the Android IServiceConnection.
     *
     * @param connectionId  The connection id (shared between Java and native)
     * @param bundleName    The OH bundle name of the connected ability
     * @param abilityName   The OH ability name of the connected ability
     * @param serviceBinder The IBinder representing the service
     */
    public void onServiceConnected(int connectionId, String bundleName,
                                   String abilityName, IBinder serviceBinder) {
        final ConnectionRecord record;
        synchronized (this) {
            record = mConnectionsById.get(connectionId);
            if (record == null) {
                Log.e(TAG, "onServiceConnected: no record for connectionId="
                        + connectionId);
                return;
            }
        }

        ComponentName componentName = record.targetComponent;
        Log.i(TAG, "onServiceConnected: connId=" + connectionId
                + " bundle=" + bundleName + " ability=" + abilityName);

        try {
            record.connection.connected(componentName, serviceBinder, false);
        } catch (Exception error) {
            Log.e(TAG, "onServiceConnected: callback dispatch failed", error);
            return;
        }

        synchronized (this) {
            if (mConnectionsById.get(connectionId) == record) {
                record.bound = true;
            }
        }
    }

    /**
     * Called when OH reports that a service ability has disconnected.
     * Dispatches the event to the Android IServiceConnection with a null binder.
     *
     * @param connectionId The connection id (shared between Java and native)
     * @param bundleName   The OH bundle name of the disconnected ability
     * @param abilityName  The OH ability name of the disconnected ability
     */
    public void onServiceDisconnected(int connectionId, String bundleName,
                                      String abilityName) {
        final ConnectionRecord record;
        synchronized (this) {
            record = mConnectionsById.get(connectionId);
            if (record == null) {
                Log.e(TAG, "onServiceDisconnected: no record for connectionId="
                        + connectionId);
                return;
            }
        }

        ComponentName componentName = record.targetComponent;
        Log.i(TAG, "onServiceDisconnected: connId=" + connectionId
                + " bundle=" + bundleName + " ability=" + abilityName);

        try {
            record.connection.connected(componentName, null, true);
        } catch (Exception error) {
            Log.e(TAG, "onServiceDisconnected: callback dispatch failed", error);
            return;
        }

        synchronized (this) {
            if (mConnectionsById.get(connectionId) == record) {
                record.bound = false;
            }
        }
    }

    // ========================================================================
    // Shutdown
    // ========================================================================

    /**
     * Disconnect and clear all registered connections.
     * Called during adapter shutdown via OHEnvironment.shutdown().
     */
    public synchronized void disconnectAll() {
        int count = mConnections.size();
        mConnections.clear();
        mConnectionsById.clear();
        Log.i(TAG, "Disconnected all connections, count=" + count);
    }
}
