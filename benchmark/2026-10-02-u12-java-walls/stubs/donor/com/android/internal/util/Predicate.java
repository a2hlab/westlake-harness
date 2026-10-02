package com.android.internal.util;

/**
 * AOSP (android-7.1 and earlier) com.android.internal.util.Predicate, removed from later frameworks but still
 * referenced by old libraries (ACRA's org.acra.util.IOUtils: packlist dies with ClassNotFoundException). Same
 * interface U11i carries in oh-adapter-runtime.jar; that copy is invisible to app class loaders (runtime
 * PathClassLoader), so the boot class path needs this one.
 *
 * @deprecated Use {@code java.util.function.Predicate} instead.
 */
@Deprecated
public interface Predicate<T> {
    boolean apply(T t);
}
