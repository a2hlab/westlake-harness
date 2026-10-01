/* J10e (#webview-viewdelegate): single-purpose freeze unit -- the WebView ViewDelegate forwarding.
 * Split out of J10eWebView.java (was J10eWebView$DelegateForward) so each fix is one file, behaviour
 * unchanged. For each ViewDelegate method m(args), if WebView.PrivateAccess has a public same-named
 * super_<m> with identical params, forward to it (so WebView.mLayoutParams/mFrame get set); else zero. */
package adapter.activity;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;

public final class J10eViewDelegate implements InvocationHandler {
    private static volatile boolean sLoggedDelegate = false;
    private final Object privateAccess;
    J10eViewDelegate(Object pa) { this.privateAccess = pa; }
    @Override public Object invoke(Object proxy, Method method, Object[] args) {
        String n = method.getName();
        if ("toString".equals(n)) return "WlViewDelegate";
        if ("hashCode".equals(n)) return Integer.valueOf(System.identityHashCode(proxy));
        if ("equals".equals(n)) return Boolean.valueOf(args != null && args.length == 1 && args[0] == proxy);
        if (privateAccess != null) {
            try {
                Method sup = privateAccess.getClass().getMethod("super_" + n, method.getParameterTypes());
                Object r = sup.invoke(privateAccess, args);
                if ("setLayoutParams".equals(n) && !sLoggedDelegate) {
                    sLoggedDelegate = true;
                    System.err.println("[J10e-WEBVIEW] delegate forwards setLayoutParams");
                }
                return r;
            } catch (NoSuchMethodException noSuper) {
                // no super_<n> counterpart -> fall through to zero
            } catch (Throwable t) {
                // defensive: never let the delegate throw into the parent layout path
            }
        }
        return J10eWebView.zero(method.getReturnType());
    }
}
