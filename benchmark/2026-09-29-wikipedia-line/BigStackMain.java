package adapter.activity;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/**
 * Run ActivityThread.main on a Java thread with a large stack (B11 experiment, cc-wiki).
 *
 * appspawn-x children get a 128 KiB main-thread stack: after fork a PROT_NONE page sits directly
 * under the currently mapped [stack] (the parent's same page is rw-p), so RLIMIT_STACK never
 * applies. Deep main-thread work -- Wikipedia's Compose recomposition decoding a PNG through skia
 * inflate -- walks into that page and dies with SIGSEGV(SEGV_ACCERR).
 *
 * AppSpawnXInit.invokeStaticMain calls this instead of Method.invoke. The main looper, Choreographer
 * and every main-thread callback then run on the big-stack thread; the original native main thread
 * only waits. Whatever ActivityThread.main throws is rethrown here as Method.invoke would, so
 * initChild's existing handling (logging, exit) is unchanged.
 */
public final class BigStackMain {
    private static final long STACK_BYTES = 32L << 20;

    private BigStackMain() {}

    public static Object invoke(final Method method, final Object receiver, final Object[] args)
            throws IllegalAccessException, InvocationTargetException {
        final Object[] result = new Object[1];
        final Throwable[] failure = new Throwable[1];
        Thread thread = new Thread(null, new Runnable() {
            public void run() {
                try {
                    result[0] = method.invoke(receiver, args);
                } catch (Throwable t) {
                    failure[0] = t;
                }
            }
        }, "main", STACK_BYTES);
        System.err.println("[BIGSTACK] " + method.getDeclaringClass().getName() + "." + method.getName()
                + " on a " + (STACK_BYTES >> 20) + " MiB thread");
        System.err.flush();
        thread.start();
        boolean interrupted = false;
        while (true) {
            try {
                thread.join();
                break;
            } catch (InterruptedException e) {
                interrupted = true;
            }
        }
        if (interrupted) Thread.currentThread().interrupt();
        Throwable f = failure[0];
        if (f instanceof InvocationTargetException) throw (InvocationTargetException) f;
        if (f instanceof IllegalAccessException) throw (IllegalAccessException) f;
        if (f instanceof RuntimeException) throw (RuntimeException) f;
        if (f instanceof Error) throw (Error) f;
        if (f != null) throw new InvocationTargetException(f);
        return result[0];
    }
}
