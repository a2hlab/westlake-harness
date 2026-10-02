package org.chromium.support_lib_glue;

import android.webkit.WebSettings;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Minimal androidx.webkit support-library glue for the route-A WebView provider (2026-10-03-u13-java-walls-2).
 *
 * androidx.webkit asks the WebView provider's class loader for
 * {@code org.chromium.support_lib_glue.SupportLibReflectionUtil.createWebViewProviderFactory()} and talks to the
 * returned InvocationHandler through its own boundary interfaces (method names only, no shared classes). Without
 * this class every support-library feature list is empty. That is harmless for most features, but not for
 * ALGORITHMIC_DARKENING: WebViewFeature.isFeatureSupported() also accepts the framework (SDK_INT >= 33 -> true),
 * while WebSettingsCompat.setAlgorithmicDarkeningAllowed() checks only the WebView feature list and throws
 * UnsupportedOperationException("This method is not supported by the current version of the framework and the
 * current WebView APK"). That is privacybrowser's first fatal.
 *
 * Supported features: exactly ALGORITHMIC_DARKENING. Its setter/getter forward to the framework WebSettings
 * methods of API 33 when the provider's WebSettings implements them, and are remembered per WebSettings otherwise.
 * Every other boundary call returns the type's default; androidx never makes them, because no other feature is
 * claimed.
 */
public final class SupportLibReflectionUtil {
    static final String[] FEATURES = {"ALGORITHMIC_DARKENING"};
    private static final Map<WebSettings, Boolean> DARKENING = Collections.synchronizedMap(new WeakHashMap<>());

    private SupportLibReflectionUtil() {}

    /** Entry point androidx.webkit's WebViewGlueCommunicator looks up by reflection. */
    public static InvocationHandler createWebViewProviderFactory() {
        System.err.println("[WEBKIT-GLUE] support-library factory created, features=ALGORITHMIC_DARKENING");
        return new FactoryHandler();
    }

    static Object defaultValue(Class<?> t) {
        if (t == boolean.class) return Boolean.FALSE;
        if (t == int.class) return 0;
        if (t == long.class) return 0L;
        if (t == float.class) return 0f;
        if (t == double.class) return 0d;
        if (t == short.class) return (short) 0;
        if (t == byte.class) return (byte) 0;
        if (t == char.class) return (char) 0;
        return null;
    }

    /** WebViewProviderFactoryBoundaryInterface. */
    static final class FactoryHandler implements InvocationHandler {
        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            switch (method.getName()) {
                case "getSupportedFeatures":
                    return FEATURES.clone();
                case "getWebkitToCompatConverter":
                    return new ConverterHandler();
                case "toString":
                    return "WlSupportLibFactory";
                case "hashCode":
                    return System.identityHashCode(this);
                case "equals":
                    return args != null && args.length == 1 && args[0] == proxy;
                default:
                    System.err.println("[WEBKIT-GLUE] unsupported factory call " + method.getName());
                    return defaultValue(method.getReturnType());
            }
        }
    }

    /** WebkitToCompatConverterBoundaryInterface: only convertSettings is reachable for the claimed feature. */
    static final class ConverterHandler implements InvocationHandler {
        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            if ("convertSettings".equals(method.getName()) && args != null && args.length == 1
                    && args[0] instanceof WebSettings) {
                return new SettingsHandler((WebSettings) args[0]);
            }
            return defaultValue(method.getReturnType());
        }
    }

    /** WebSettingsBoundaryInterface: setAlgorithmicDarkeningAllowed / isAlgorithmicDarkeningAllowed. */
    static final class SettingsHandler implements InvocationHandler {
        private final WebSettings settings;

        SettingsHandler(WebSettings settings) {
            this.settings = settings;
        }

        @Override
        public Object invoke(Object proxy, Method method, Object[] args) {
            String n = method.getName();
            if ("setAlgorithmicDarkeningAllowed".equals(n) && args != null && args.length == 1) {
                boolean allow = Boolean.TRUE.equals(args[0]);
                DARKENING.put(settings, allow);
                try {
                    WebSettings.class.getMethod("setAlgorithmicDarkeningAllowed", boolean.class)
                            .invoke(settings, allow);
                } catch (Throwable ignored) {
                    // the provider's WebSettings may not implement the API 33 method; the value is remembered
                }
                return null;
            }
            if ("isAlgorithmicDarkeningAllowed".equals(n)) {
                try {
                    return WebSettings.class.getMethod("isAlgorithmicDarkeningAllowed").invoke(settings);
                } catch (Throwable ignored) {
                    Boolean v = DARKENING.get(settings);
                    return v != null && v;
                }
            }
            return defaultValue(method.getReturnType());
        }
    }
}
