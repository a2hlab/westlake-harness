package adapter.activity;

import android.os.Binder;
import android.os.IBinder;
import android.os.Parcel;
import android.os.RemoteException;
import android.os.Trace;

import java.lang.reflect.Field;
import java.util.Map;

/** Child-local IUserManager projection for the credential-unlocked query. */
public final class UserManagerProjectionProxy {
    private static final String SERVICE_NAME = "user";
    private static final String DESCRIPTOR = "android.os.IUserManager";
    private static final String TRANSACTION_FIELD =
            "TRANSACTION_isUserUnlockingOrUnlocked";
    private static final String TRACE_QUERY =
            "ZZ.UserManager.isUserUnlockingOrUnlocked";

    private UserManagerProjectionProxy() {}

    /** Install before ActivityThread binds the application. */
    @SuppressWarnings("unchecked")
    public static void install() {
        try {
            Class<?> stub = Class.forName("android.os.IUserManager$Stub");
            Field transactionField = stub.getDeclaredField(TRANSACTION_FIELD);
            transactionField.setAccessible(true);
            int transaction = transactionField.getInt(null);
            if (transaction <= 0) {
                throw new IllegalStateException("invalid IUserManager transaction=" + transaction);
            }

            Class<?> serviceManager = Class.forName("android.os.ServiceManager");
            Field cacheField = serviceManager.getDeclaredField("sCache");
            cacheField.setAccessible(true);
            Object value = cacheField.get(null);
            if (!(value instanceof Map)) {
                throw new IllegalStateException("ServiceManager.sCache is not a Map");
            }
            Map<String, IBinder> cache = (Map<String, IBinder>) value;
            synchronized (cache) {
                IBinder existing = cache.get(SERVICE_NAME);
                if (existing != null) {
                    System.err.println("[ZZ-USER] user cache already populated; preserving "
                            + existing.getClass().getName());
                    return;
                }
                // No local interface: force the device-generated IUserManager
                // Proxy to exercise the generation-specific Parcel contract.
                cache.put(SERVICE_NAME, new UserBinder(transaction));
            }
            System.err.println("[ZZ-USER] installed child-local user binder transaction="
                    + transaction);
        } catch (Throwable t) {
            throw new IllegalStateException("Unable to install child-local user binder", t);
        }
    }

    static final class UserBinder extends Binder {
        private final int transaction;

        UserBinder(int transaction) {
            this.transaction = transaction;
        }

        @Override
        protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (code == IBinder.INTERFACE_TRANSACTION) {
                if (reply != null) {
                    reply.writeString(DESCRIPTOR);
                }
                return true;
            }
            if (code != transaction) {
                return super.onTransact(code, data, reply, flags);
            }

            data.enforceInterface(DESCRIPTOR);
            int userId = data.readInt();
            data.enforceNoDataAvail();
            Trace.beginSection(TRACE_QUERY);
            try {
                reply.writeNoException();
                reply.writeBoolean(true);
                System.err.println("[ZZ-USER] isUserUnlockingOrUnlocked user="
                        + userId + " result=true");
                return true;
            } finally {
                Trace.endSection();
            }
        }
    }
}
