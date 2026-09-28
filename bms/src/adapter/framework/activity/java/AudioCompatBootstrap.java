package adapter.audio;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/** Loads the opt-in Android audio JNI bridge from a compatible APK sandbox. */
public final class AudioCompatBootstrap implements Thread.UncaughtExceptionHandler {
    private static final String BOAT_PROCESS = "com.Unity3d.BoatAttackDay";
    private static boolean loaded;
    private static boolean exceptionReceiptInstalled;
    private final Thread.UncaughtExceptionHandler previousHandler;

    private AudioCompatBootstrap(Thread.UncaughtExceptionHandler previousHandler) {
        this.previousHandler = previousHandler;
    }

    private static void installExceptionReceipt() {
        if (exceptionReceiptInstalled) return;
        Thread.UncaughtExceptionHandler previous =
                Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler(
                new AudioCompatBootstrap(previous));
        exceptionReceiptInstalled = true;
    }

    @Override
    public void uncaughtException(Thread thread, Throwable error) {
        if (thread != null && thread.getName().contains("FMOD")) {
            try (PrintWriter writer = new PrintWriter(new FileWriter(
                    "/data/storage/el2/base/files/westlake_audio_exception.log",
                    false))) {
                writer.println("thread=" + thread.getName());
                error.printStackTrace(writer);
            } catch (Throwable ignored) {
            }
        }
        if (previousHandler != null) {
            previousHandler.uncaughtException(thread, error);
        }
    }

    public static synchronized void load(String processName, ClassLoader appClassLoader) {
        if (loaded || !BOAT_PROCESS.equals(processName)) {
            return;
        }
        String path = "/data/app/el1/bundle/public/" + processName
                + "/android/lib/arm64-v8a/libwestlake_audio_compat.so";
        if (!new File(path).isFile()) {
            System.err.println("[OH_AudioCompat] optional bridge absent");
            return;
        }
        try {
            Class<?> appCaller = Class.forName(
                    "org.fmod.FMODAudioDevice", false, appClassLoader);
            Method load0 = Runtime.class.getDeclaredMethod(
                    "load0", Class.class, String.class);
            load0.setAccessible(true);
            load0.invoke(Runtime.getRuntime(), appCaller, path);
            loaded = true;
            installExceptionReceipt();
            System.err.println("[OH_AudioCompat] bridge loaded");
        } catch (Throwable error) {
            if (error instanceof InvocationTargetException
                    && ((InvocationTargetException) error).getCause() != null) {
                error = ((InvocationTargetException) error).getCause();
            }
            System.err.println("[OH_AudioCompat] bridge load failed: " + error);
        }
    }
}
