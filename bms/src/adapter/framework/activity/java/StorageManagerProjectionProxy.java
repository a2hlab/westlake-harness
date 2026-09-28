package adapter.activity;

import android.os.Binder;
import android.os.Environment;
import android.os.IBinder;
import android.os.Parcel;
import android.os.Parcelable;
import android.os.RemoteException;
import android.os.Trace;
import android.os.UserHandle;

import java.io.File;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Map;
import java.util.UUID;

/**
 * Child-local projection for the single storage-manager operation used by
 * AOSP Environment when an app asks ContextImpl for an external app directory.
 *
 * <p>The OpenHarmony app sandbox has no global /storage/emulated/0 mount.  The
 * adapter already projects ApplicationInfo.dataDir onto the real writable
 * per-user OH directory; this binder exposes that same authority through the
 * AOSP IStorageManager.getVolumeList transaction.  It intentionally does not
 * attach a local interface and does not implement any other mount operation.</p>
 */
public final class StorageManagerProjectionProxy {
    private static final String SERVICE_NAME = "mount";
    private static final String DESCRIPTOR = "android.os.storage.IStorageManager";
    private static final int TRANSACTION_GET_VOLUME_LIST = 0x1e;
    private static final String PACKAGE_PATTERN = "[A-Za-z0-9._]+";
    private static final String TRACE_GET_VOLUME_LIST = "ZZ.StorageVolume.getVolumeList";

    private StorageManagerProjectionProxy() {}

    /** Install before ActivityThread binds the application. */
    @SuppressWarnings("unchecked")
    public static void install() {
        try {
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
                    System.err.println("[ZZ-STORAGE] mount cache already populated; preserving "
                            + existing.getClass().getName());
                    return;
                }
                // Do not attachInterface(): the device-generated IStorageManager.Stub
                // must choose its Proxy and exercise the real 0x1e Parcel contract.
                cache.put(SERVICE_NAME, new MountBinder());
            }
            System.err.println("[ZZ-STORAGE] installed child-local mount binder transaction=0x1e");
        } catch (Throwable t) {
            throw new IllegalStateException("Unable to install child-local mount binder", t);
        }
    }

    static final class MountBinder extends Binder {
        MountBinder() {}

        @Override
        protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (code == IBinder.INTERFACE_TRANSACTION) {
                if (reply != null) {
                    reply.writeString(DESCRIPTOR);
                }
                return true;
            }
            if (code != TRANSACTION_GET_VOLUME_LIST) {
                return super.onTransact(code, data, reply, flags);
            }

            data.enforceInterface(DESCRIPTOR);
            int userId = data.readInt();
            String callingPackage = data.readString();
            int queryFlags = data.readInt();
            data.enforceNoDataAvail();

            Trace.beginSection(TRACE_GET_VOLUME_LIST);
            try {
                Parcelable volume = createStorageVolume(userId, callingPackage);
                Parcelable[] result = volume == null
                        ? new Parcelable[0] : new Parcelable[] { volume };
                reply.writeNoException();
                reply.writeTypedArray(result, Parcelable.PARCELABLE_WRITE_RETURN_VALUE);
                System.err.println("[ZZ-STORAGE] getVolumeList user=" + userId
                        + " package=" + callingPackage + " flags=" + queryFlags
                        + " count=" + result.length);
                return true;
            } finally {
                Trace.endSection();
            }
        }
    }

    private static Parcelable createStorageVolume(int userId, String callingPackage) {
        try {
            if (callingPackage == null || !callingPackage.matches(PACKAGE_PATTERN)) {
                System.err.println("[ZZ-STORAGE] rejecting invalid package=" + callingPackage);
                return null;
            }
            File root = findWritableExternalRoot(userId, callingPackage);
            if (root == null) {
                System.err.println("[ZZ-STORAGE] no writable OH app root for " + callingPackage);
                return null;
            }

            Class<?> storageVolume = Class.forName("android.os.storage.StorageVolume");
            Constructor<?> constructor = storageVolume.getDeclaredConstructor(
                    String.class,
                    File.class,
                    File.class,
                    String.class,
                    boolean.class,
                    boolean.class,
                    boolean.class,
                    boolean.class,
                    boolean.class,
                    long.class,
                    UserHandle.class,
                    UUID.class,
                    String.class,
                    String.class);
            constructor.setAccessible(true);

            int safeUserId = userId >= 0 && userId <= 20000 ? userId : 0;
            UserHandle owner = UserHandle.getUserHandleForUid(safeUserId * 100000);
            Object value = constructor.newInstance(
                    "oh-primary-" + safeUserId,
                    root,
                    root,
                    "OpenHarmony app storage",
                    true,
                    false,
                    true,
                    false,
                    false,
                    0L,
                    owner,
                    null,
                    null,
                    Environment.MEDIA_MOUNTED);
            return (Parcelable) value;
        } catch (Throwable t) {
            System.err.println("[ZZ-STORAGE] StorageVolume construction failed: " + t);
            return null;
        }
    }

    private static File findWritableExternalRoot(int userId, String callingPackage) {
        String[] candidates = {
            "/data/app/el2/" + userId + "/base/" + callingPackage,
            "/data/app/el1/" + userId + "/base/" + callingPackage,
            "/data/app/el2/100/base/" + callingPackage,
            "/data/app/el1/100/base/" + callingPackage,
            "/data/local/tmp/oh_app_home/" + callingPackage,
        };
        for (String candidate : candidates) {
            File base = new File(candidate);
            if (!base.isDirectory() || !base.canWrite()) {
                continue;
            }
            File external = new File(base, "external");
            if ((external.isDirectory() || external.mkdirs()) && external.canWrite()) {
                try {
                    return external.getCanonicalFile();
                } catch (Throwable ignored) {
                    return external.getAbsoluteFile();
                }
            }
        }
        return null;
    }
}
